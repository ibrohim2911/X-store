from .models import Sale, SaleItem, Cash, PaymentMenthod, Client, AuditLog, SystemSetting
from rest_framework import serializers

class SystemSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemSetting
        fields = '__all__'


class SaleItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='variant.product.name', read_only=True)
    size_name = serializers.CharField(source='variant.size.name', read_only=True)
    sku = serializers.CharField(source='variant.sku', read_only=True)
    class Meta:
        model = SaleItem
        fields = '__all__'
class CashSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cash
        fields = '__all__'
class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True, read_only=True)
    payments = CashSerializer(many=True, read_only=True)
    seller_name = serializers.CharField(source='seller.name', read_only=True)
    class Meta:
        model = Sale
        fields = '__all__'
class PaymentMenthodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMenthod
        fields = '__all__'
class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = '__all__'

class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.name', read_only=True)
    class Meta:
        model = AuditLog
        fields = '__all__'