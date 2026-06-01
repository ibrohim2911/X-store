import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from sale.serializers import SaleSerializer
from django.contrib.auth import get_user_model
User = get_user_model()
user = User.objects.first()

data = {
    'items': [{'variant': 1, 'quantity': 1, 'price': '10.00'}],
    'client': [],
    'payment_method': None,
    'total_price': '10.00',
    'seller': user.id,
    'status': 'completed'
}
s = SaleSerializer(data=data)
s.is_valid(raise_exception=True)
print("VALIDATED DATA:", s.validated_data)

try:
    s.save(seller=user)
    print("SUCCESS")
except Exception as e:
    import traceback
    traceback.print_exc()
