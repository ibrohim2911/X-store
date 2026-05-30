from django.db import models
from common.models import BaseModel

class Products(BaseModel):
    name = models.CharField(max_length=255)
    img = models.ImageField(upload_to='product_images/', null=True, blank=True)
    def __str__(self):
        return self.name
class Variant(BaseModel):
    product = models.ForeignKey(Products, on_delete=models.CASCADE, related_name='variants')
    sku = models.CharField(max_length=100, unique=True)
    barcode = models.CharField(max_length=100)
    size_scale = models.CharField(max_length=50)
    size = models.CharField(max_length=50)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    sticker_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField()
    def __str__(self):
        return self.sku
