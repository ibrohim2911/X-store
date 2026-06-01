from django.db import models
from common.models import BaseModel

class Products(BaseModel):
    name = models.CharField(max_length=255)
    img = models.ImageField(upload_to='product_images/', null=True, blank=True)
    barcode = models.CharField(max_length=100, blank=True, null=True)
    def __str__(self):
        return self.name
class SizeScale(BaseModel):
    name = models.CharField(max_length=50)
    def __str__(self):
        return self.name
class Size(BaseModel):
    name = models.CharField(max_length=50)
    size_scale = models.ForeignKey(SizeScale, on_delete=models.CASCADE, related_name='sizes')
    def __str__(self):        return self.name
class Variant(BaseModel):
    product = models.ForeignKey(Products, on_delete=models.CASCADE, related_name='variants')
    sku = models.CharField(max_length=100, unique=True)
    size_scale = models.ForeignKey(SizeScale, on_delete=models.CASCADE, related_name='variants', null=True, blank=True)
    size = models.ManyToManyField(Size, null=True, blank=True, related_name='variants')
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    sticker_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField()
    def __str__(self):
        return self.sku
