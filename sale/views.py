import decimal

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from django.db import transaction
from django.db.models import Sum, F, Q
from django_filters import rest_framework as filters
from .models import Sale, SaleItem, Cash, CashCategory, PaymentMenthod, Client, AuditLog, SystemSetting, Debt
from .serializers import SaleSerializer, SaleItemSerializer, CashSerializer, CashCategorySerializer, PaymentMenthodSerializer, ClientSerializer, AuditLogSerializer, SystemSettingSerializer, DebtSerializer
from product.models import Variant
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from rest_framework.permissions import IsAuthenticated
from common.permissions import IsRoleAuthorized
import urllib.request
import json

class SystemSettingViewSet(viewsets.ModelViewSet):
    queryset = SystemSetting.objects.all()
    serializer_class = SystemSettingSerializer

class NgrokUrlView(APIView):
    permission_classes = []
    
    def get(self, request):
        try:
            req = urllib.request.Request('http://127.0.0.1:4040/api/tunnels')
            with urllib.request.urlopen(req, timeout=2) as response:
                data = json.loads(response.read().decode())
                for tunnel in data.get('tunnels', []):
                    if tunnel.get('proto') == 'https':
                        return Response({'url': tunnel.get('public_url')})
        except Exception:
            pass
        return Response({'url': None})

def broadcast_update(event_type):
    channel_layer = get_channel_layer()
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            'updates',
            {'type': 'broadcast_update', 'message_type': event_type}
        )

def log_audit(user, action_text, description=""):
    AuditLog.objects.create(user=user if (user and not user.is_anonymous) else None, action=action_text, description=description)

class SaleFilter(filters.FilterSet):
    start_date = filters.DateTimeFilter(field_name="created_at", lookup_expr='gte')
    end_date = filters.DateTimeFilter(field_name="created_at", lookup_expr='lte')

    class Meta:
        model = Sale
        fields = ['start_date', 'end_date']

class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.all().order_by('-created_at')
    serializer_class = AuditLogSerializer

class SaleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsRoleAuthorized]
    queryset = Sale.objects.all().order_by('-created_at')
    serializer_class = SaleSerializer
    filterset_class = SaleFilter
    
    def perform_create(self, serializer):
        serializer.save(seller=self.request.user)
        broadcast_update('sales_updated')
        log_audit(self.request.user, "Sale Created", f"Sale ID: {serializer.instance.id}")

    def perform_update(self, serializer):
        super().perform_update(serializer)
        broadcast_update('sales_updated')
        log_audit(self.request.user, "Sale Updated", f"Sale ID: {serializer.instance.id} status changed to {serializer.instance.status}")

    @transaction.atomic
    def perform_destroy(self, instance):
        # Restore stock for each item
        for item in instance.items.all():
            variant = item.variant
            variant.quantity += item.quantity
            variant.save()
            
        # Cash records related to this sale are deleted automatically by CASCADE
        # if the ForeignKey is on_delete=CASCADE.
        
        log_audit(self.request.user, "Sale Deleted", f"Sale ID: {instance.id}")
        super().perform_destroy(instance)
        broadcast_update('sales_updated')

    def get_queryset(self):
        queryset = super().get_queryset()
        user_id = self.request.query_params.get('user_id')
        search = self.request.query_params.get('search')
        
        if user_id is not None:
            queryset = queryset.filter(seller_id=user_id)
            
        if search:
            queryset = queryset.filter(
                Q(items__variant__sku__icontains=search) |
                Q(items__variant__product__barcode__icontains=search) |
                Q(client__name__icontains=search) |
                Q(client__phone__icontains=search)
            ).distinct()
            
        return queryset

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def update_items(self, request, pk=None):
        sale = self.get_object()
        new_items_data = request.data.get('items', [])
        
        old_items = sale.items.all()
        old_quantities = {item.variant_id: item.quantity for item in old_items}
        old_items_dict = {item.variant_id: item for item in old_items}
        
        new_quantities = {}
        for item_data in new_items_data:
            vid = str(item_data.get('variant'))
            qty = int(item_data.get('quantity', 0))
            new_quantities[vid] = new_quantities.get(vid, 0) + qty
            
        # Validate stock
        for vid, new_qty in new_quantities.items():
            old_qty = old_quantities.get(vid, 0)
            diff = new_qty - old_qty
            if diff > 0:
                variant = Variant.objects.get(id=vid)
                if variant.quantity < diff:
                    return Response({'error': f'Not enough stock for variant {variant.sku}. Available: {variant.quantity}'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Handle returns and tax refunds
        # Handle returns of items (product price refund only, tax is handled below via net difference)
        for vid, old_qty in old_quantities.items():
            # Items are returned to stock
            variant = Variant.objects.get(id=vid)
            variant.quantity += old_qty
            variant.save()
            
            new_qty = new_quantities.get(vid, 0)
            diff = old_qty - new_qty
            if diff > 0:
                old_item = old_items_dict[vid]
                price = old_item.price
                refund_amount = decimal.Decimal(str(price)) * decimal.Decimal(str(diff))
                
                savdo_cat, _ = CashCategory.objects.get_or_create(name='Savdo', defaults={'is_system': True})
                # Create Cash Chiqim for refunded product price
                if refund_amount > 0:
                    Cash.objects.create(
                        user=sale.seller,
                        is_cash_in=False,
                        amount=refund_amount,
                        reason="returned sale item",
                        category=savdo_cat,
                        sale=sale
                    )
                
        old_items.delete()
        
        # First, get default_tax
        tax_setting = SystemSetting.objects.filter(key='tax_amount').first()
        default_tax = decimal.Decimal(str(tax_setting.value)) if tax_setting else decimal.Decimal('20000.00')

        # Calculate old tax totals per variant
        old_tax_totals = {vid: item.quantity * item.applied_tax_amount for vid, item in old_items_dict.items()}

        # Calculate new tax totals per variant and prepare new items
        new_tax_totals = {}
        new_applied_taxes = {}
        for item_data in new_items_data:
            vid = str(item_data.get('variant'))
            qty = int(item_data.get('quantity', 0))
            apply_tax = item_data.get('apply_tax')
            
            if apply_tax is None:
                if vid in old_items_dict:
                    applied_tax = old_items_dict[vid].applied_tax_amount
                else:
                    applied_tax = default_tax
            elif apply_tax:
                if vid in old_items_dict and old_items_dict[vid].applied_tax_amount > 0:
                    applied_tax = old_items_dict[vid].applied_tax_amount
                else:
                    applied_tax = default_tax
            else:
                applied_tax = decimal.Decimal('0.00')
                
            new_applied_taxes[vid] = applied_tax
            new_tax_totals[vid] = qty * applied_tax

        # Handle tax differences
        all_vids = set(old_tax_totals.keys()).union(set(new_tax_totals.keys()))
        for vid in all_vids:
            old_tax = old_tax_totals.get(vid, decimal.Decimal('0.00'))
            new_tax = new_tax_totals.get(vid, decimal.Decimal('0.00'))
            diff_tax = new_tax - old_tax
            
            if diff_tax > 0:
                # We need to charge more tax
                Cash.objects.create(
                    user=sale.seller,
                    is_cash_in=False,
                    amount=diff_tax,
                    reason="20 tax (updated)",
                    sale=sale
                )
            elif diff_tax < 0:
                # We need to refund some tax
                Cash.objects.create(
                    user=sale.seller,
                    is_cash_in=True,
                    amount=abs(diff_tax),
                    reason="returned 20 tax (updated)",
                    sale=sale
                )

        # Re-create items with new quantities
        total_new_qty = 0
        for item_data in new_items_data:
            vid = str(item_data.get('variant'))
            qty = int(item_data.get('quantity', 0))
            if qty > 0:
                total_new_qty += qty
                variant = Variant.objects.get(id=vid)
                
                applied_tax = new_applied_taxes.get(vid, decimal.Decimal('0.00'))
                
                SaleItem.objects.create(
                    sale=sale,
                    variant=variant,
                    quantity=qty,
                    price=item_data.get('price'),
                    applied_tax_amount=applied_tax
                )
            
        sale.total_price = decimal.Decimal(str(request.data.get('total_price', sale.total_price)))
        sale.debt = decimal.Decimal(str(request.data.get('debt', sale.debt)))
        
        # Auto-return if empty
        if total_new_qty == 0:
            sale.status = 'returned'
            setattr(sale, 'skip_signal', True)
        else:
            sale.status = 'completed'
            setattr(sale, 'skip_signal', True)
            
        sale.save()
        
        log_audit(request.user, "Sale Swapped/Refunded", f"Sale ID: {sale.id} updated items")
        broadcast_update('sales_updated')
        return Response(SaleSerializer(sale).data)
    
    @action(detail=False, methods=['post'])
    @transaction.atomic
    def create_with_items(self, request, pk=None):
        seller = request.user
        data = request.data.copy()
        
        if seller and not seller.is_anonymous:
            data['seller'] = seller.id
        else:
            data['seller'] = 1
            
        data['status'] = 'completed'
        data['total_price'] = decimal.Decimal(str(data.get('total_price', '0.00')))
        data['debt'] = decimal.Decimal(str(data.get('debt', '0.00')))
        
        serializer = SaleSerializer(data=data)
        
        if serializer.is_valid():
            items_data = data.get('items', [])
            
            # Pre-validate stock before saving anything
            for item_data in items_data:
                variant = Variant.objects.get(id=item_data.get('variant'))
                qty = int(item_data.get('quantity', 0))
                if variant.quantity < qty:
                    return Response(
                        {'error': f'Not enough stock for variant {variant.sku}. Available: {variant.quantity}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            sale = serializer.save()
            
            # Get default tax from Settings
            tax_setting = SystemSetting.objects.filter(key='tax_amount').first()
            default_tax = decimal.Decimal(str(tax_setting.value)) if tax_setting else decimal.Decimal('20000.00')

            savdo_cat, _ = CashCategory.objects.get_or_create(name='Savdo', defaults={'is_system': True})
            soliq_cat, _ = CashCategory.objects.get_or_create(name='Soliq', defaults={'is_system': True})
            
            total_tax_deducted = decimal.Decimal('0.00')

            for item_data in items_data:
                variant = Variant.objects.get(id=item_data.get('variant'))
                qty = int(item_data.get('quantity', 0))
                apply_tax = item_data.get('apply_tax', True)
                
                applied_tax = default_tax if apply_tax else decimal.Decimal('0.00')
                
                SaleItem.objects.create(
                    sale=sale,
                    variant=variant,
                    quantity=qty,
                    price=item_data.get('price'),
                    applied_tax_amount=applied_tax
                )
                
                if applied_tax > 0 and qty > 0:
                    total_tax_deducted += (applied_tax * qty)

            # Deduct tax from cash
            if total_tax_deducted > 0:
                Cash.objects.create(
                    user=seller,
                    is_cash_in=False,
                    amount=total_tax_deducted,
                    reason="20 tax",
                    category=soliq_cat,
                    sale=sale
                )
                
            # Add Sale Income to Cash
            net_income = sale.total_price - sale.debt
            if net_income > 0:
                Cash.objects.create(
                    user=seller,
                    is_cash_in=True,
                    amount=net_income,
                    reason="sale income",
                    category=savdo_cat,
                    sale=sale
                )
                
            # Create Debt record if there is debt
            if sale.debt > 0:
                Debt.objects.create(
                    user=seller,
                    is_income=False, # Debt given to client
                    amount=sale.debt,
                    description=f"Savdodan qarz (Chek: {sale.id})",
                    person=sale.client.name if sale.client else "Mijoz",
                    status='active'
                )
            
            log_audit(request.user, "Sale Created", f"Sale ID: {sale.id}, Total: {sale.total_price}")
            broadcast_update('sales_updated')
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SaleItemViewSet(viewsets.ModelViewSet):
    queryset = SaleItem.objects.all()
    serializer_class = SaleItemSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        sale_id = self.request.query_params.get('sale_id')
        if sale_id is not None:
            queryset = queryset.filter(sale_id=sale_id)
        return queryset

    @transaction.atomic
    def perform_destroy(self, instance):
        variant = instance.variant
        variant.quantity += instance.quantity
        variant.save()
        super().perform_destroy(instance)
        broadcast_update('sales_updated')

class ClientViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsRoleAuthorized]
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class PaymentMenthodViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsRoleAuthorized]
    queryset = PaymentMenthod.objects.all()
    serializer_class = PaymentMenthodSerializer
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class CashCategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsRoleAuthorized]
    queryset = CashCategory.objects.all()
    serializer_class = CashCategorySerializer

class CashViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsRoleAuthorized]
    queryset = Cash.objects.all().order_by('-created_at')
    serializer_class = CashSerializer
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        broadcast_update('cash_updated')
        log_audit(self.request.user, "Cash Added", f"Amount: {serializer.instance.amount}, In: {serializer.instance.is_cash_in}")

    def perform_update(self, serializer):
        super().perform_update(serializer)
        broadcast_update('cash_updated')

    def perform_destroy(self, instance):
        log_audit(self.request.user, "Cash Deleted", f"Amount: {instance.amount}")
        super().perform_destroy(instance)
        broadcast_update('cash_updated')

class DebtViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsRoleAuthorized]
    queryset = Debt.objects.all().order_by('-created_at')
    serializer_class = DebtSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        broadcast_update('cash_updated')
        log_audit(self.request.user, "Debt Added", f"Amount: {serializer.instance.amount}, In: {serializer.instance.is_income}")

    def perform_update(self, serializer):
        super().perform_update(serializer)
        broadcast_update('cash_updated')

    def perform_destroy(self, instance):
        log_audit(self.request.user, "Debt Deleted", f"Amount: {instance.amount}")
        super().perform_destroy(instance)
        broadcast_update('cash_updated')

class PaymentMenthodViewSet(viewsets.ModelViewSet):
    queryset = PaymentMenthod.objects.all()
    serializer_class = PaymentMenthodSerializer

class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer

class DashboardStatsView(APIView):
    def get(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        sales = Sale.objects.all()
        cashes = Cash.objects.all()
        debts = Debt.objects.all()
        if start_date:
            sales = sales.filter(created_at__gte=start_date)
            cashes = cashes.filter(created_at__gte=start_date)
            debts = debts.filter(created_at__gte=start_date)
        if end_date:
            sales = sales.filter(created_at__lte=end_date)
            cashes = cashes.filter(created_at__lte=end_date)
            debts = debts.filter(created_at__lte=end_date)
            
        completed_sales = sales.filter(status='completed')
        sale_items = SaleItem.objects.filter(sale__in=completed_sales)
        
        net_sales = completed_sales.aggregate(total=Sum(F('total_price') - F('debt')))['total'] or decimal.Decimal('0.00')
        tax_amount = sale_items.aggregate(total=Sum(F('applied_tax_amount') * F('quantity')))['total'] or decimal.Decimal('0.00')
        
        savdodan_kirim = net_sales - tax_amount
        
        qarz_from_sale = completed_sales.aggregate(total=Sum('debt'))['total'] or decimal.Decimal('0.00')
        qarz_without_sale = debts.filter(is_income=False, status='active').aggregate(total=Sum('amount'))['total'] or decimal.Decimal('0.00')
        qarz_all = qarz_from_sale + qarz_without_sale
        
        sale_price_total = completed_sales.aggregate(total=Sum('total_price'))['total'] or decimal.Decimal('0.00')
        cost_price_total = sale_items.aggregate(total=Sum(F('variant__cost_price') * F('quantity')))['total'] or decimal.Decimal('0.00')
        
        yalpi_foyda = sale_price_total - cost_price_total - tax_amount
        
        xarajatlar_cashes = cashes.filter(is_cash_in=False).exclude(reason__icontains='tax').exclude(category__name='Soliq').exclude(reason='returned sale item')
        x_categories = xarajatlar_cashes.values('category__name', 'reason').annotate(total=Sum('amount'))
        
        xarajatlar_dict = {}
        for xc in x_categories:
            cat_name = xc['category__name']
            if not cat_name:
                # Fallback to older logic or 'Boshqa'
                reason_lower = str(xc['reason']).lower()
                if 'oylik' in reason_lower: cat_name = 'Oylik'
                elif 'ijara' in reason_lower: cat_name = 'Ijara'
                elif 'qarz' in reason_lower: continue # Skip old qarz from xarajat
                else: cat_name = 'Boshqa'
            
            xarajatlar_dict[cat_name] = xarajatlar_dict.get(cat_name, decimal.Decimal('0.00')) + (xc['total'] or decimal.Decimal('0.00'))
            
        xarajatlar_list = [{'category': k, 'amount': v} for k, v in xarajatlar_dict.items()]
        
        from product.models import Variant
        total_inventory_qty = Variant.objects.aggregate(total=Sum('quantity'))['total'] or 0
        total_inventory_value = Variant.objects.aggregate(total=Sum(F('sticker_price') * F('quantity')))['total'] or decimal.Decimal('0.00')
        total_inventory_cost = Variant.objects.aggregate(total=Sum(F('cost_price') * F('quantity')))['total'] or decimal.Decimal('0.00')
        
        return Response({
            'savdodan_kirim': savdodan_kirim,
            'tax_amount': tax_amount,
            'qarz_all': qarz_all,
            'qarz_from_sale': qarz_from_sale,
            'qarz_without_sale': qarz_without_sale,
            'yalpi_foyda': yalpi_foyda,
            'sotilgan_tovar_tan_narx': cost_price_total,
            'xarajatlar': xarajatlar_list,
            'total_inventory': {
                'qty': total_inventory_qty,
                'sticker_value': total_inventory_value,
                'cost_value': total_inventory_cost
            }
        })