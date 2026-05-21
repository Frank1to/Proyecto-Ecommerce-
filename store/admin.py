from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Category, Product, Color, Size, ProductVariant, Coupon, Order, OrderItem, Review

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    verbose_name = "Variante de Producto"
    verbose_name_plural = "Variantes de Producto"

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'is_active', 'average_rating_display', 'created_at')
    list_filter = ('category', 'is_active', 'created_at')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'description')
    inlines = [ProductVariantInline]

    def average_rating_display(self, obj):
        rating = obj.average_rating
        return format_html('<span style="color: #f59e0b;">' + '★' * int(round(rating)) + '</span> ({:.1f})', rating) if rating > 0 else "Sin calificaciones"
    average_rating_display.short_description = "Calificación Promedio"


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ('name', 'hex_code', 'color_preview')
    
    def color_preview(self, obj):
        return format_html('<div style="width: 24px; height: 24px; background-color: {}; border: 1px solid #ccc; border-radius: 50%;"></div>', obj.hex_code)
    color_preview.short_description = "Vista Previa"


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('product', 'color', 'size', 'stock', 'price_display')
    list_filter = ('product__category', 'color', 'size')
    search_fields = ('product__name',)

    def price_display(self, obj):
        return f"Gs. {obj.price:,.0f}" if obj.price >= 1000 else f"${obj.price}"
    price_display.short_description = "Precio"


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'discount_value', 'active', 'valid_from', 'valid_to', 'is_valid_now')
    list_filter = ('active', 'discount_type')
    search_fields = ('code',)

    def is_valid_now(self, obj):
        valid = obj.is_valid()
        color = "green" if valid else "red"
        text = "Sí" if valid else "No"
        return format_html('<b style="color: {};">{}</b>', color, text)
    is_valid_now.short_description = "¿Válido actualmente?"


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'variant', 'price', 'quantity', 'subtotal_display')
    
    def subtotal_display(self, obj):
        if obj.id:
            return f"Gs. {obj.subtotal:,.0f}" if obj.subtotal >= 1000 else f"${obj.subtotal}"
        return ""
    subtotal_display.short_description = "Subtotal"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'first_name', 'last_name', 'email', 'total_amount_display', 'paid_status', 'status', 'created_at', 'invoice_link')
    list_filter = ('paid', 'status', 'created_at')
    search_fields = ('first_name', 'last_name', 'email', 'address')
    inlines = [OrderItemInline]
    readonly_fields = ('payment_id', 'total_amount', 'discount_amount')

    def total_amount_display(self, obj):
        return f"Gs. {obj.total_amount:,.0f}" if obj.total_amount >= 1000 else f"${obj.total_amount}"
    total_amount_display.short_description = "Total"

    def paid_status(self, obj):
        color = "green" if obj.paid else "red"
        text = "Pagado" if obj.paid else "Pendiente"
        return format_html('<b style="color: {};">{}</b>', color, text)
    paid_status.short_description = "Estado de Pago"

    def invoice_link(self, obj):
        if obj.paid or obj.status == 'paid':
            url = reverse('download_invoice', args=[obj.id])
            return format_html('<a href="{}" target="_blank" class="button" style="background-color: #8b5cf6; color: white; padding: 4px 8px; border-radius: 4px; text-decoration: none;">📄 PDF</a>', url)
        return "No pagado"
    invoice_link.short_description = "Factura"


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user_name', 'rating_stars', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('product__name', 'user_name', 'comment')
    readonly_fields = ('product', 'user_name', 'rating', 'comment', 'created_at')

    def rating_stars(self, obj):
        return format_html('<span style="color: #f59e0b;">' + '★' * obj.rating + '</span>')
    rating_stars.short_description = "Calificación"
