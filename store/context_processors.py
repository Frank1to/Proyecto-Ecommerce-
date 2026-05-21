from .cart import Cart

def cart_context(request):
    return {
        'cart_length': len(Cart(request))
    }
