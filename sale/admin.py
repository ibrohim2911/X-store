from django.contrib import admin
from .models import Sale, SaleItem, Cash, PaymentMenthod, Client
admin.site.register(Sale)
admin.site.register(SaleItem)
admin.site.register(Cash)
admin.site.register(PaymentMenthod)
admin.site.register(Client)
# Register your models here.
