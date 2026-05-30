from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from .models import Sale, SaleItem, Cash, PaymentMenthod, Client
from .serializers import SaleSerializer, SaleItemSerializer, CashSerializer, PaymentMenthodSerializer, ClientSerializer
class SaleViewSet(viewsets.ModelViewSet):
    queryset = Sale.objects.all()
    serializer_class = SaleSerializer
    def get_queryset(self):
        queryset = super().get_queryset()
        user_id = self.request.query_params.get('user_id')
        if user_id is not None:
            queryset = queryset.filter(user_id=user_id)
        return queryset
    @action(detail=True, methods=['post'])
    def create_with_items(self, request, pk=None):
        seller = request.user
        serializer = SaleSerializer(data=request.data)
        if serializer.is_valid():
            sale = serializer.save(seller=seller)
            items_data = request.data.get('items', [])
            for item_data in items_data:
                SaleItem.objects.create(
                    sale=sale,
                    variant_id=item_data.get('variant_id'),
                    quantity=item_data.get('quantity'),
                    price=item_data.get('price')
                ).save()
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
    
    
class PaymentMenthodViewSet(viewsets.ModelViewSet):
    queryset = PaymentMenthod.objects.all()
    serializer_class = PaymentMenthodSerializer
class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer