from .models import Sale, SaleItem, Cash, PaymentMenthod, Client
from rest_framework import serializers

class SaleItemSerializer(serializers.ModelSerializer):
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