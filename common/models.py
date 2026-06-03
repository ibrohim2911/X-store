from django.db import models

# Create your models here.
class BaseModel(models.Model):
    id = models.AutoField(primary_key=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class PrinterSetting(BaseModel):
    printer_name = models.CharField(max_length=255, default='Xprinter XP-365B')
    paper_width_mm = models.IntegerField(default=40)
    paper_height_mm = models.IntegerField(default=30)
    dpi = models.IntegerField(default=203)
    layout_config = models.JSONField(default=dict, blank=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        super(PrinterSetting, self).save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        if created and not obj.layout_config:
            obj.layout_config = {
                "product_name": { "x": 10, "y": 10, "fontSize": 24, "visible": True },
                "barcode": { "x": 10, "y": 40, "width": 200, "height": 60, "visible": True },
                "price": { "x": 10, "y": 110, "fontSize": 28, "visible": True }
            }
            obj.save()
        return obj