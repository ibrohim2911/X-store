from django.db import models
from common.models import BaseModel

class Products(BaseModel):
    store = models.ForeignKey('common.Store', on_delete=models.CASCADE, null=True, blank=True, related_name='products')
    created_by = models.ForeignKey('user.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_products')
    name = models.CharField(max_length=255)
    img = models.ImageField(upload_to='product_images/', null=True, blank=True)
    barcode = models.CharField(max_length=100, blank=True, null=True)
    def save(self, *args, **kwargs):
        if not self.barcode:
            qs = Products.objects.filter(store=self.store)
            barcodes = qs.values_list('barcode', flat=True)
            max_b = 999
            for b in barcodes:
                if b and str(b).isdigit():
                    val = int(b)
                    if val > max_b:
                        max_b = val
            self.barcode = str(max_b + 1)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
class SizeScale(BaseModel):
    store = models.ForeignKey('common.Store', on_delete=models.CASCADE, null=True, blank=True, related_name='size_scales')
    created_by = models.ForeignKey('user.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_size_scales')
    name = models.CharField(max_length=50)
    def __str__(self):
        return self.name
class Size(BaseModel):
    store = models.ForeignKey('common.Store', on_delete=models.CASCADE, null=True, blank=True, related_name='sizes')
    created_by = models.ForeignKey('user.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_sizes')
    name = models.CharField(max_length=50)
    size_scale = models.ForeignKey(SizeScale, on_delete=models.CASCADE, related_name='sizes')
    def __str__(self):        return self.name
class Variant(BaseModel):
    product = models.ForeignKey(Products, on_delete=models.CASCADE, related_name='variants')
    created_by = models.ForeignKey('user.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_variants')
    sku = models.CharField(max_length=100)
    size_scale = models.ForeignKey(SizeScale, on_delete=models.CASCADE, related_name='variants', null=True, blank=True)
    size = models.ManyToManyField(Size, null=True, blank=True, related_name='variants')
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    sticker_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField()

    def save(self, *args, **kwargs):
        if not self.sku:
            qs = Variant.objects.filter(product__store=self.product.store)
            skus = qs.values_list('sku', flat=True)
            max_s = 999
            for s in skus:
                if s and str(s).isdigit():
                    val = int(s)
                    if val > max_s:
                        max_s = val
            self.sku = str(max_s + 1)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.sku
