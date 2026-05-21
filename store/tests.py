from django.test import TestCase, RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .models import Category, Product, Color, Size, ProductVariant, Coupon
from .cart import Cart

class ECommerceModelsTestCase(TestCase):
    def setUp(self):
        # Configurar datos de prueba
        self.category = Category.objects.create(name="Ropa Deportiva")
        self.product = Product.objects.create(
            category=self.category,
            name="Remera Premium",
            price=120000.00
        )
        self.color = Color.objects.create(name="Rojo", hex_code="#FF0000")
        self.size = Size.objects.create(name="M")
        
        # Variante con precio base heredado
        self.variant_base = ProductVariant.objects.create(
            product=self.product,
            color=self.color,
            size=self.size,
            stock=10
        )
        
        # Variante con precio modificado
        self.variant_override = ProductVariant.objects.create(
            product=self.product,
            color=self.color,
            size=Size.objects.create(name="XL"),
            stock=5,
            price_override=140000.00
        )

    def test_product_slug_generation(self):
        """Verifica que el slug del producto se genere automáticamente al guardar."""
        self.assertEqual(self.product.slug, "remera-premium")

    def test_variant_price(self):
        """Verifica que el precio de la variante se herede o se anule correctamente."""
        # Hereda del precio base del producto
        self.assertEqual(self.variant_base.price, 120000.00)
        # Usa el precio alternativo modificado
        self.assertEqual(self.variant_override.price, 140000.00)


class CouponTestCase(TestCase):
    def setUp(self):
        now = timezone.now()
        self.valid_coupon = Coupon.objects.create(
            code="VAL10",
            discount_type="percentage",
            discount_value=10.00,
            active=True,
            valid_from=now - timedelta(days=1),
            valid_to=now + timedelta(days=1)
        )
        
        self.expired_coupon = Coupon.objects.create(
            code="EXP20",
            discount_type="percentage",
            discount_value=20.00,
            active=True,
            valid_from=now - timedelta(days=5),
            valid_to=now - timedelta(days=1)
        )
        
        self.inactive_coupon = Coupon.objects.create(
            code="INA30",
            discount_type="fixed",
            discount_value=30000.00,
            active=False,
            valid_from=now - timedelta(days=1),
            valid_to=now + timedelta(days=1)
        )

    def test_coupon_validity(self):
        """Verifica que las validaciones de los cupones activos, expirados o inactivos sean correctas."""
        self.assertTrue(self.valid_coupon.is_valid())
        self.assertFalse(self.expired_coupon.is_valid())
        self.assertFalse(self.inactive_coupon.is_valid())


class CartTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        
        # Crear datos de prueba
        self.category = Category.objects.create(name="Calzado")
        self.product = Product.objects.create(
            category=self.category,
            name="Tenis",
            price=250000.00
        )
        self.color = Color.objects.create(name="Azul", hex_code="#0000FF")
        self.size = Size.objects.create(name="42")
        self.variant = ProductVariant.objects.create(
            product=self.product,
            color=self.color,
            size=self.size,
            stock=3
        )

    def test_cart_operations(self):
        """Verifica añadir elementos, límites de stock y sumas de precios en el carrito de sesión."""
        # 1. Crear una petición mock con middleware de sesión
        request = self.factory.get('/')
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        request.session.save()
        
        cart = Cart(request)
        
        # 2. Añadir elemento
        cart.add(variant=self.variant, quantity=1)
        self.assertEqual(len(cart), 1)
        self.assertEqual(cart.get_total_price(), Decimal('250000.00'))
        
        # 3. Añadir más de lo disponible en stock
        # Debería limitar la cantidad a 3 (que es el stock actual)
        cart.add(variant=self.variant, quantity=5)
        self.assertEqual(len(cart), 3)
        self.assertEqual(cart.get_total_price(), Decimal('750000.00'))
        
        # 4. Eliminar del carrito
        cart.remove(self.variant)
        self.assertEqual(len(cart), 0)
        self.assertEqual(cart.get_total_price(), Decimal('0.00'))
