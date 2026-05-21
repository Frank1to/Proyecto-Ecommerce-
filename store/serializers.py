from rest_framework import serializers
from .models import Category, Product, Color, Size, ProductVariant, Coupon, Order, OrderItem, Review

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description']


class ColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Color
        fields = ['id', 'name', 'hex_code']


class SizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Size
        fields = ['id', 'name']


class ProductVariantSerializer(serializers.ModelSerializer):
    color = ColorSerializer(read_only=True)
    size = SizeSerializer(read_only=True)
    price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = ProductVariant
        fields = ['id', 'color', 'size', 'stock', 'price']


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['id', 'product', 'user_name', 'rating', 'comment', 'created_at']
        read_only_fields = ['created_at']


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    average_rating = serializers.FloatField(read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'category', 'name', 'slug', 'description', 
            'price', 'image', 'is_active', 'variants', 
            'average_rating', 'reviews', 'created_at'
        ]


class CouponSerializer(serializers.ModelSerializer):
    is_valid = serializers.BooleanField(read_only=True, source='is_valid')

    class Meta:
        model = Coupon
        fields = ['id', 'code', 'discount_type', 'discount_value', 'active', 'valid_from', 'valid_to', 'is_valid']


class OrderItemSerializer(serializers.ModelSerializer):
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    color_name = serializers.CharField(source='variant.color.name', read_only=True, default=None)
    size_name = serializers.CharField(source='variant.size.name', read_only=True, default=None)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'variant', 'color_name', 'size_name', 'price', 'quantity', 'subtotal']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    coupon_code = serializers.CharField(source='coupon.code', read_only=True, default=None)

    class Meta:
        model = Order
        fields = [
            'id', 'first_name', 'last_name', 'email', 'address', 'city', 
            'country', 'total_amount', 'coupon', 'coupon_code', 
            'discount_amount', 'paid', 'payment_id', 'status', 
            'created_at', 'items'
        ]
        read_only_fields = ['total_amount', 'discount_amount', 'paid', 'payment_id', 'status', 'created_at']
