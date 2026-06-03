from django.db import models
from common.models import BaseModel
from product.models import Products

class SystemSetting(models.Model):
    key = models.CharField(max_length=50, unique=True)
    value = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.key}: {self.value}"

class Client(BaseModel):
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=100)
class PaymentMenthod(models.Model):
    name = models.CharField(max_length=50)
class Sale(BaseModel):
    seller = models.ForeignKey('user.User', on_delete=models.CASCADE)
    client = models.ManyToManyField(Client, null=True, blank=True)
    payment_method = models.ForeignKey(PaymentMenthod, on_delete=models.CASCADE, null=True, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=50, choices=[('completed', 'Completed'), ('returned', 'Returned')])
    debt = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    def __str__(self):
        return f"Sale #{self.id}"
class SaleItem(BaseModel):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey('product.Variant', on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    applied_tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def __str__(self):
        return f"{self.variant.product.name} - {self.quantity} - {self.price}"

class Cash(BaseModel):
    user = models.ForeignKey('user.User', on_delete=models.CASCADE)
    is_cash_in = models.BooleanField(default=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=255 )
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, null=True, blank=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"Cash Payment for Sale #{self.sale.id} - Amount: {self.amount}"

class AuditLog(BaseModel):
    user = models.ForeignKey('user.User', on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.name if self.user else 'System'} - {self.action} at {self.created_at}"