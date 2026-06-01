from rest_framework import serializers
from .models import Products, Variant, Size, SizeScale
class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Products
        fields = '__all__'
class VariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Variant
        fields = '__all__'
class SizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Size
        fields = '__all__'
class SizeScaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = SizeScale
        fields = '__all__'