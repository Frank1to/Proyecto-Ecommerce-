from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import api_views

router = DefaultRouter()
router.register(r'api/products', api_views.ProductViewSet, basename='api_products')

urlpatterns = [
    # Catálogo
    path('', views.product_list, name='product_list'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('product/<int:product_id>/review/', views.add_review, name='add_review'),
    
    # Autenticación
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # Panel de Administración
    path('panel/', views.admin_dashboard, name='admin_dashboard'),
    path('panel/orders/', views.admin_orders, name='admin_orders'),
    path('panel/orders/<int:order_id>/status/', views.admin_order_status, name='admin_order_status'),
    path('panel/products/', views.admin_products, name='admin_products'),
    path('panel/products/<int:product_id>/toggle/', views.admin_product_toggle, name='admin_product_toggle'),
    path('panel/users/', views.admin_users, name='admin_users'),
    path('panel/coupons/', views.admin_coupons, name='admin_coupons'),
    path('panel/coupons/<int:coupon_id>/toggle/', views.admin_coupon_toggle, name='admin_coupon_toggle'),
    path('panel/reports/', views.admin_reports, name='admin_reports'),

    # Carrito
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/', views.cart_add, name='cart_add'),
    path('cart/update/', views.cart_update, name='cart_update'),
    path('cart/remove/', views.cart_remove, name='cart_remove'),
    path('cart/coupon/', views.apply_coupon, name='apply_coupon'),
    
    # Checkout y Órdenes
    path('checkout/', views.checkout, name='checkout'),
    path('checkout/process/', views.process_order, name='process_order'),
    path('checkout/success/', views.order_success, name='order_success'),
    path('orders/', views.order_history, name='order_history'),
    path('order/<int:order_id>/invoice/', views.download_invoice, name='download_invoice'),

    # API REST
    path('', include(router.urls)),
    path('api/review/add/', api_views.ReviewCreateAPIView.as_view(), name='api_add_review'),
    path('api/coupon/validate/', api_views.CouponValidateAPIView.as_view(), name='api_validate_coupon'),
    path('api/checkout/', api_views.APICheckoutView.as_view(), name='api_checkout'),
]