from django.db import models
from common.models import BaseModel
from product.models import Products

class SystemSetting(models.Model):
    key = models.CharField(max_length=50, unique=True)
    value = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.key}: {self.value}"

class Client(BaseModel):
    store = models.ForeignKey('common.Store', on_delete=models.CASCADE, null=True, blank=True, related_name='clients')
    created_by = models.ForeignKey('user.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_clients')
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=100)
class PaymentMenthod(models.Model):
    store = models.ForeignKey('common.Store', on_delete=models.CASCADE, null=True, blank=True, related_name='payment_methods')
    created_by = models.ForeignKey('user.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_payment_methods')
    name = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
class Sale(BaseModel):
    store = models.ForeignKey('common.Store', on_delete=models.CASCADE, null=True, blank=True, related_name='sales')
    seller = models.ForeignKey('user.User', on_delete=models.CASCADE, null=True, blank=True)
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

class CashCategory(BaseModel):
    store = models.ForeignKey('common.Store', on_delete=models.CASCADE, null=True, blank=True, related_name='cash_categories')
    name = models.CharField(max_length=100)
    is_system = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class Cash(BaseModel):
    store = models.ForeignKey('common.Store', on_delete=models.CASCADE, null=True, blank=True, related_name='cashes')
    user = models.ForeignKey('user.User', on_delete=models.CASCADE, null=True, blank=True)
    is_cash_in = models.BooleanField(default=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(CashCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='cashes')
    reason = models.CharField(max_length=255 )
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, null=True, blank=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"Cash Payment for Sale #{self.sale.id} - Amount: {self.amount}"

class AuditLog(BaseModel):
    store = models.ForeignKey('common.Store', on_delete=models.CASCADE, null=True, blank=True, related_name='audit_logs')
    user = models.ForeignKey('user.User', on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.name if self.user else 'System'} - {self.action} at {self.created_at}"

class Debt(BaseModel):
    store = models.ForeignKey('common.Store', on_delete=models.CASCADE, null=True, blank=True, related_name='debts')
    user = models.ForeignKey('user.User', on_delete=models.CASCADE, null=True, blank=True)
    is_income = models.BooleanField(default=True) # True = Qarz oldik, False = Qarz berdik
    person = models.CharField(max_length=255) # Kimdan / Kimga
    status = models.CharField(max_length=50, choices=[('active', 'Active'), ('returned', 'Returned')], default='active')
    expiration_date = models.DateField(null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255)

    def __str__(self):
        return f"Debt: {self.amount} - {self.person}"