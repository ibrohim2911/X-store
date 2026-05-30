from django.shortcuts import render
from rest_framework import viewsets
from .models import Products, Variant
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from .serializers import ProductSerializer, VariantSerializer
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Products.objects.all()
    serializer_class = ProductSerializer
    @action(detail=True, methods=['post'])
    def createwithvariants(self, request, pk=None):
        name = request.data.get('name')
        img = request.data.get('img')
        variants_data = request.data.get('variants', [])
        product = Products.objects.create(name=name, img=img)
        product.save()
        for variant_data in variants_data:

            Variant.objects.create(
                product=product,
                sku=variant_data.get('sku'),
                barcode=variant_data.get('barcode'),
                size_scale=variant_data.get('size_scale'),
                size=variant_data.get('size'),
                cost_price=variant_data.get('cost_price'),
                sticker_price=variant_data.get('sticker_price'),
                quantity=variant_data.get('quantity')
            ).save()
            
        serializer = self.get_serializer(product)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
class VariantViewSet(viewsets.ModelViewSet):
    queryset = Variant.objects.all()
    serializer_class = VariantSerializer