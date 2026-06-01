from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db import transaction
from .models import Sale, SaleItem, Cash

@receiver(post_save, sender=SaleItem)
def update_stock_on_sale(sender, instance, created, **kwargs):
    if created and instance.sale.status == 'completed':
        with transaction.atomic():
            variant = instance.variant
            variant.quantity -= instance.quantity
            variant.save()

@receiver(pre_save, sender=Sale)
def handle_sale_updates(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_sale = Sale.objects.get(pk=instance.pk)
        except Sale.DoesNotExist:
            return
        
        # If the sale status is changing to returned
        if old_sale.status == 'completed' and instance.status == 'returned':
            with transaction.atomic():
                # Restock variants
                for item in instance.items.all():
                    variant = item.variant
                    variant.quantity += item.quantity
                    variant.save()
                
                # Create a cash out record for the refund if any amount was paid
                paid_amount = old_sale.total_price - old_sale.debt
                if paid_amount > 0:
                    Cash.objects.create(
                        user=instance.seller,
                        is_cash_in=False,
                        amount=paid_amount,
                        reason=f"Refund for returned Sale #{instance.id}",
                        sale=instance
                    )
        
        # If the sale status remains completed but debt changes
        elif old_sale.status == 'completed' and instance.status == 'completed':
            debt_difference = old_sale.debt - instance.debt
            if debt_difference > 0:
                # Debt decreased -> Customer paid us cash
                Cash.objects.create(
                    user=instance.seller,
                    is_cash_in=True,
                    amount=debt_difference,
                    reason=f"Debt payment for Sale #{instance.id}",
                    sale=instance
                )
            elif debt_difference < 0:
                # Debt increased -> Customer was refunded partial amount or extended credit
                Cash.objects.create(
                    user=instance.seller,
                    is_cash_in=False,
                    amount=abs(debt_difference),
                    reason=f"Debt increased for Sale #{instance.id}",
                    sale=instance
                )

@receiver(post_save, sender=Sale)
def create_cash_on_sale(sender, instance, created, **kwargs):
    # Create Cash In when a Sale is made
    if created and instance.status == 'completed':
        paid_amount = instance.total_price - instance.debt
        if paid_amount > 0:
            Cash.objects.create(
                user=instance.seller,
                is_cash_in=True,
                amount=paid_amount,
                reason=f"Payment for Sale #{instance.id}",
                sale=instance
            )