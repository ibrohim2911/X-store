from django.shortcuts import render
from rest_framework import viewsets
from .models import Products, Variant, Size, SizeScale
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status, filters
from .serializers import ProductSerializer, VariantSerializer, SizeSerializer, SizeScaleSerializer
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Products.objects.all()
    serializer_class = ProductSerializer
    @action(detail=False, methods=['post'])
    def createwithvariants(self, request, pk=None):
        name = request.data.get('name')
        img = request.data.get('img')
        barcode = request.data.get('barcode')
        variants_data = request.data.get('variants', [])
        
        if isinstance(variants_data, str):
            import json
            try:
                variants_data = json.loads(variants_data)
            except ValueError:
                variants_data = []
                
        product = Products.objects.create(name=name, img=img, barcode=barcode)
        product.save()
        for variant_data in variants_data:
            size_id = variant_data.get('size')
            size_obj = Size.objects.get(id=size_id)
            sticker_price = variant_data.get('sticker_price')
            
            # Generate custom SKU: {ProductName}-{SizeName}-{Price}
            sku = f"{product.name}-{size_obj.name}-{sticker_price}"

            variant = Variant.objects.create(
                product=product,
                sku=sku,
                size_scale_id=variant_data.get('size_scale'),
                cost_price=variant_data.get('cost_price'),
                sticker_price=sticker_price,
                quantity=variant_data.get('quantity')
            )
            if size_id:
                variant.size.set([size_id])
            
        serializer = self.get_serializer(product)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
class VariantViewSet(viewsets.ModelViewSet):
    queryset = Variant.objects.all()
    serializer_class = VariantSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['product__name', 'sku', 'product__barcode', 'size__name']
class SizeViewSet(viewsets.ModelViewSet):
    queryset = Size.objects.all()
    serializer_class = SizeSerializer
class SizeScaleViewSet(viewsets.ModelViewSet):
    queryset = SizeScale.objects.all()
    serializer_class = SizeScaleSerializer