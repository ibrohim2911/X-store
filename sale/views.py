import decimal

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from django.db import transaction
from django.db.models import Sum, F
from django_filters import rest_framework as filters
from .models import Sale, SaleItem, Cash, PaymentMenthod, Client
from .serializers import SaleSerializer, SaleItemSerializer, CashSerializer, PaymentMenthodSerializer, ClientSerializer
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

class SaleFilter(filters.FilterSet):
    start_date = filters.DateTimeFilter(field_name="created_at", lookup_expr='gte')
    end_date = filters.DateTimeFilter(field_name="created_at", lookup_expr='lte')

    class Meta:
        model = Sale
        fields = ['start_date', 'end_date']

class SaleViewSet(viewsets.ModelViewSet):
    queryset = Sale.objects.all().order_by('-created_at')
    serializer_class = SaleSerializer
    filterset_class = SaleFilter
    
    def perform_create(self, serializer):
        super().perform_create(serializer)
        broadcast_update('sales_updated')

    def perform_update(self, serializer):
        super().perform_update(serializer)
        broadcast_update('sales_updated')

    def perform_destroy(self, instance):
        super().perform_destroy(instance)
        broadcast_update('sales_updated')

    def get_queryset(self):
        queryset = super().get_queryset()
        user_id = self.request.query_params.get('user_id')
        if user_id is not None:
            queryset = queryset.filter(user_id=user_id)
        return queryset
    
    @action(detail=False, methods=['post'])
    @transaction.atomic
    def create_with_items(self, request, pk=None):
        seller = request.user
        request.data['seller'] = seller.id
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

            sale = serializer.save(seller=seller)
            
            for item_data in items_data:
                variant = Variant.objects.get(id=item_data.get('variant'))
                SaleItem.objects.create(
                    sale=sale,
                    variant=variant,
                    quantity=item_data.get('quantity'),
                    price=item_data.get('price')
                )
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
    queryset = Cash.objects.all()
    serializer_class = CashSerializer
    
    def perform_create(self, serializer):
        super().perform_create(serializer)
        broadcast_update('cash_updated')

    def perform_update(self, serializer):
        super().perform_update(serializer)
        broadcast_update('cash_updated')

    def perform_destroy(self, instance):
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
        if start_date:
            sales = sales.filter(created_at__gte=start_date)
        if end_date:
            sales = sales.filter(created_at__lte=end_date)
            
        total_revenue = sales.aggregate(Sum('total_price'))['total_price__sum'] or 0
        
        sale_items = SaleItem.objects.filter(sale__in=sales)
        total_items = sale_items.aggregate(Sum('quantity'))['quantity__sum'] or 0
        
        profit = sale_items.annotate(
            profit_per_item=F('price') - F('variant__cost_price')
        ).aggregate(
            total_profit=Sum(F('profit_per_item') * F('quantity'))
        )['total_profit'] or 0
        
        top_products = sale_items.values('variant__product__name').annotate(
            total_qty=Sum('quantity')
        ).order_by('-total_qty')[:5]
        
        top_selling = [
            {'name': item['variant__product__name'], 'quantity': item['total_qty']}
            for item in top_products
        ]
        
        return Response({
            'total_revenue': total_revenue,
            'total_items_sold': total_items,
            'gross_profit': profit,
            'top_selling_products': top_selling
        })