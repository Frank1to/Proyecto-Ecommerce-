from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import api_views

# Configurar el Router de Django REST Framework
router = DefaultRouter()
router.register(r'api/products', api_views.ProductViewSet, basename='api_products')

urlpatterns = [
    # Rutas de la API REST (Django REST Framework)
    path('', include(router.urls)),
    path('api/review/add/', api_views.ReviewCreateAPIView.as_view(), name='api_add_review'),
    path('api/coupon/validate/', api_views.CouponValidateAPIView.as_view(), name='api_validate_coupon'),
    path('api/checkout/', api_views.APICheckoutView.as_view(), name='api_checkout'),

    # Catálogo
    path('', views.product_list, name='product_list'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('product/<int:product_id>/review/', views.add_review, name='add_review'),
    
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
]

