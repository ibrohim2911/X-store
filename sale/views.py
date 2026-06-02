import decimal

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from django.db import transaction
from django.db.models import Sum, F, Q
from django_filters import rest_framework as filters
from .models import Sale, SaleItem, Cash, PaymentMenthod, Client, AuditLog
from .serializers import SaleSerializer, SaleItemSerializer, CashSerializer, PaymentMenthodSerializer, ClientSerializer, AuditLogSerializer
from product.models import Variant
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import urllib.request
import json

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
    queryset = Sale.objects.all().order_by('-created_at')
    serializer_class = SaleSerializer
    filterset_class = SaleFilter
    
    def perform_create(self, serializer):
        super().perform_create(serializer)
        broadcast_update('sales_updated')
        log_audit(self.request.user, "Sale Created", f"Sale ID: {serializer.instance.id}")

    def perform_update(self, serializer):
        super().perform_update(serializer)
        broadcast_update('sales_updated')
        log_audit(self.request.user, "Sale Updated", f"Sale ID: {serializer.instance.id} status changed to {serializer.instance.status}")

    def perform_destroy(self, instance):
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
                Q(items__variant__barcode__icontains=search) |
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
        
        new_quantities = {}
        for item_data in new_items_data:
            vid = int(item_data.get('variant'))
            qty = int(item_data.get('quantity', 0))
            new_quantities[vid] = new_quantities.get(vid, 0) + qty
            
        for vid, new_qty in new_quantities.items():
            old_qty = old_quantities.get(vid, 0)
            diff = new_qty - old_qty
            if diff > 0:
                variant = Variant.objects.get(id=vid)
                if variant.quantity < diff:
                    return Response({'error': f'Not enough stock for variant {variant.sku}. Available: {variant.quantity}'}, status=status.HTTP_400_BAD_REQUEST)
        
        for item in old_items:
            variant = Variant.objects.get(id=item.variant_id)
            variant.quantity += item.quantity
            variant.save()
        old_items.delete()
        
        for item_data in new_items_data:
            vid = int(item_data.get('variant'))
            qty = int(item_data.get('quantity', 0))
            variant = Variant.objects.get(id=vid)
            variant.quantity -= qty
            variant.save()
            SaleItem.objects.create(
                sale=sale,
                variant=variant,
                quantity=qty,
                price=item_data.get('price')
            )
            
        sale.total_price = decimal.Decimal(str(request.data.get('total_price', sale.total_price)))
        sale.debt = decimal.Decimal(str(request.data.get('debt', sale.debt)))
        sale.save()
        
        log_audit(request.user, "Sale Swapped/Refunded", f"Sale ID: {sale.id} updated items")
        broadcast_update('sales_updated')
        return Response(SaleSerializer(sale).data)
    
    @action(detail=False, methods=['post'])
    @transaction.atomic
    def create_with_items(self, request, pk=None):
        seller = request.user
        request.data['seller'] = seller.id if seller and not seller.is_anonymous else 1
        request.data['status'] = 'completed'
        request.data['total_price'] = decimal.Decimal(str(request.data.get('total_price', '0.00')))
        request.data['debt'] = decimal.Decimal(str(request.data.get('debt', '0.00')))
        serializer = SaleSerializer(data=request.data)
        
        if serializer.is_valid():
            items_data = request.data.get('items', [])
            
            # Pre-validate stock before saving anything
            for item_data in items_data:
                variant = Variant.objects.get(id=item_data.get('variant'))
                qty = int(item_data.get('quantity', 0))
                if variant.quantity < qty:
                    return Response(
                        {'error': f'Not enough stock for variant {variant.sku}. Available: {variant.quantity}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            sale = serializer.save(seller=seller if seller and not seller.is_anonymous else None)
            
            for item_data in items_data:
                variant = Variant.objects.get(id=item_data.get('variant'))
                qty = int(item_data.get('quantity', 0))
                variant.quantity -= qty
                variant.save()
                SaleItem.objects.create(
                    sale=sale,
                    variant=variant,
                    quantity=qty,
                    price=item_data.get('price')
                )
            
            apply_tax = request.data.get('apply_tax', False)
            if apply_tax:
                total_qty = sum(int(item.get('quantity', 0)) for item in items_data)
                tax_amount = total_qty * 20000
                if tax_amount > 0:
                    Cash.objects.create(
                        user=seller if seller and not seller.is_anonymous else None,
                        is_cash_in=False,
                        amount=tax_amount,
                        reason="20 tax",
                        sale=sale
                    )
            
            log_audit(request.user, "Sale Created", f"Sale ID: {sale.id}, Total: {sale.total_price}, Tax Applied: {apply_tax}")
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

class CashViewSet(viewsets.ModelViewSet):
    queryset = Cash.objects.all().order_by('-created_at')
    serializer_class = CashSerializer
    
    def perform_create(self, serializer):
        super().perform_create(serializer)
        broadcast_update('cash_updated')
        log_audit(self.request.user, "Cash Added", f"Amount: {serializer.instance.amount}, In: {serializer.instance.is_cash_in}")

    def perform_update(self, serializer):
        super().perform_update(serializer)
        broadcast_update('cash_updated')

    def perform_destroy(self, instance):
        log_audit(self.request.user, "Cash Deleted", f"Amount: {instance.amount}")
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
        if start_date:
            sales = sales.filter(created_at__gte=start_date)
            cashes = cashes.filter(created_at__gte=start_date)
        if end_date:
            sales = sales.filter(created_at__lte=end_date)
            cashes = cashes.filter(created_at__lte=end_date)
            
        completed_sales = sales.filter(status='completed')
        returned_sales = sales.filter(status='returned')
        
        incomes_from_sale = completed_sales.aggregate(total=Sum(F('total_price') - F('debt')))['total'] or 0
        incomes_from_sale_qty = completed_sales.count()
        
        incomes_pending = completed_sales.aggregate(total=Sum('debt'))['total'] or 0
        incomes_pending_qty = completed_sales.filter(debt__gt=0).count()
        
        total_sales_revenue = completed_sales.aggregate(total=Sum('total_price'))['total'] or 0
        
        cash_incomes = cashes.filter(is_cash_in=True).aggregate(total=Sum('amount'))['total'] or 0
        cash_incomes_qty = cashes.filter(is_cash_in=True).count()
        
        cash_outcomes_all = cashes.filter(is_cash_in=False)
        cash_outcomes = cash_outcomes_all.exclude(reason='20 tax').aggregate(total=Sum('amount'))['total'] or 0
        cash_outcomes_qty = cash_outcomes_all.exclude(reason='20 tax').count()
        
        qarz_outcomes = cash_outcomes_all.filter(reason__icontains='qarz').aggregate(total=Sum('amount'))['total'] or 0
        qarz_outcomes_qty = cash_outcomes_all.filter(reason__icontains='qarz').count()
        
        returned_debts_qs = cashes.filter(is_cash_in=True).filter(Q(reason__icontains='qarz') | Q(reason__icontains='debt'))
        returned_debts = returned_debts_qs.aggregate(total=Sum('amount'))['total'] or 0
        returned_debts_qty = returned_debts_qs.count()
        
        tax_outcomes = cash_outcomes_all.filter(reason='20 tax').aggregate(total=Sum('amount'))['total'] or 0
        
        outcomes_from_refunds = returned_sales.aggregate(total=Sum('total_price'))['total'] or 0
        outcomes_from_refunds_qty = returned_sales.count()
        
        all_incomes = incomes_from_sale + cash_incomes
        all_outcomes = cash_outcomes + tax_outcomes + outcomes_from_refunds
        
        sale_items = SaleItem.objects.filter(sale__in=completed_sales)
        all_sold_product_bought_price = sale_items.aggregate(total=Sum(F('variant__cost_price') * F('quantity')))['total'] or 0
        all_sold_product_sticker_price = sale_items.aggregate(total=Sum(F('variant__sticker_price') * F('quantity')))['total'] or 0
        total_items_sold = sale_items.aggregate(total=Sum('quantity'))['total'] or 0
        
        gross_profit = total_sales_revenue - all_sold_product_bought_price
        discount_markup_diff = total_sales_revenue - all_sold_product_sticker_price
        net_profit = all_incomes - all_outcomes
        
        top_products = sale_items.values('variant__product__name').annotate(
            total_qty=Sum('quantity')
        ).order_by('-total_qty')[:5]
        
        top_selling = [
            {'name': item['variant__product__name'], 'quantity': item['total_qty']}
            for item in top_products
        ]
        
        return Response({
            'all_incomes': all_incomes,
            'all_outcomes': all_outcomes,
            'incomes_from_sale': {'val': incomes_from_sale, 'qty': incomes_from_sale_qty},
            'incomes_pending': {'val': incomes_pending, 'qty': incomes_pending_qty},
            'incomes_from_other_source': {'val': cash_incomes, 'qty': cash_incomes_qty},
            'outcomes_from_refunds': {'val': outcomes_from_refunds, 'qty': outcomes_from_refunds_qty},
            'outcomes_from_cash_flow': {'val': cash_outcomes, 'qty': cash_outcomes_qty},
            'qarz_outcomes': {'val': qarz_outcomes, 'qty': qarz_outcomes_qty},
            'returned_debts': {'val': returned_debts, 'qty': returned_debts_qty},
            'net_profit': net_profit,
            'gross_profit': gross_profit,
            'discount_markup_difference': discount_markup_diff,
            'all_sold_product_bought_price': {'val': all_sold_product_bought_price, 'qty': total_items_sold},
            'all_sold_product_sticker_price': {'val': all_sold_product_sticker_price, 'qty': total_items_sold},
            'total_sales_revenue': total_sales_revenue,
            'top_selling_products': top_selling
        })