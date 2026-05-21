from decimal import Decimal
from django.conf import settings
from .models import ProductVariant

class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get('cart')
        if not cart:
            cart = self.session['cart'] = {}
        self.cart = cart

    def add(self, variant, quantity=1, override_quantity=False):
        variant_id = str(variant.id)
        
        # Verificar stock disponible
        available_stock = variant.stock
        
        if variant_id not in self.cart:
            self.cart[variant_id] = {
                'quantity': 0,
                'price': str(variant.price)
            }
        
        if override_quantity:
            new_qty = quantity
        else:
            new_qty = self.cart[variant_id]['quantity'] + quantity
            
        # Limitar por el stock disponible
        if new_qty > available_stock:
            new_qty = available_stock
            
        self.cart[variant_id]['quantity'] = new_qty
        self.save()
        return new_qty

    def remove(self, variant):
        variant_id = str(variant.id)
        if variant_id in self.cart:
            del self.cart[variant_id]
            self.save()

    def save(self):
        self.session.modified = True

    def __iter__(self):
        variant_ids = self.cart.keys()
        variants = ProductVariant.objects.filter(id__in=variant_ids).select_related('product', 'color', 'size')
        
        cart_copy = self.cart.copy()
        for variant in variants:
            cart_copy[str(variant.id)]['variant'] = variant
            cart_copy[str(variant.id)]['product'] = variant.product

        for item in cart_copy.values():
            item['price'] = Decimal(item['price'])
            item['subtotal'] = item['price'] * item['quantity']
            yield item

    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self):
        return sum(Decimal(item['price']) * item['quantity'] for item in self.cart.values())

    def clear(self):
        del self.session['cart']
        self.save()
