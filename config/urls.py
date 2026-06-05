"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
"""
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import TemplateView
from django.views.static import serve
from django.conf import settings
from django.conf.urls.static import static
from product import views as product_views
from user import views as user_views
from common import views as common_views
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
router.register(r'sizes', product_views.SizeViewSet)
router.register(r'size-scales', product_views.SizeScaleViewSet)
router.register(r'audit-logs', sale_views.AuditLogViewSet)
router.register(r'system-settings', sale_views.SystemSettingViewSet)
router.register(r'debts', sale_views.DebtViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/file', SpectacularAPIView.as_view(), name='schema'),
    path('api/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/login/', user_views.LoginView.as_view(), name='login'),
    path('api/logout/', user_views.LogoutView.as_view(), name='logout'),
    path('api/dashboard/stats/', sale_views.DashboardStatsView.as_view(), name='dashboard-stats'),
    path('api/ngrok-url/', sale_views.NgrokUrlView.as_view(), name='ngrok-url'),
    path('api/settings/printer/', common_views.PrinterSettingView.as_view(), name='printer-settings'),
    path('api/', include(router.urls)),
    path('api/sync/', include('sync.urls')),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
] + static('/assets/', document_root=settings.BASE_DIR / 'frontend_dist/assets')

# Catch-all route for React Router
urlpatterns += [
    re_path(r'^.*$', TemplateView.as_view(template_name='index.html')),
]
