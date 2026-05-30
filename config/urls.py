"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from product import views as product_views
from user import views as user_views
from sale import views as sale_views
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework import routers
router = routers.DefaultRouter()
router.register(r'users', user_views.UserViewSet)
router.register(r'products', product_views.ProductViewSet)
router.register(r'variants', product_views.VariantViewSet)
router.register(r'clients', sale_views.ClientViewSet)
router.register(r'payment-methods', sale_views.PaymentMenthodViewSet)
router.register(r'cash', sale_views.CashViewSet)
router.register(r'sales', sale_views.SaleViewSet)
router.register(r'sale-items', sale_views.SaleItemViewSet)
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/file', SpectacularAPIView.as_view(), name='schema'),
    path('api/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/login/', user_views.LoginView.as_view(), name='login'),
    path('api/logout/', user_views.LogoutView.as_view(), name='logout'),
    path('api/', include(router.urls)),
]
