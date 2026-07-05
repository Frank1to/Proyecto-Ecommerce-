import stripe
import mercadopago
from django.conf import settings
from django.urls import reverse


def get_site_url(request):
    return getattr(settings, 'SITE_URL', '') or request.build_absolute_uri('/').rstrip('/')


def create_stripe_checkout_session(request, order):
    """Crea una Stripe Checkout Session (pago hospedado) para la orden y devuelve la URL de pago.

    Si no hay una clave de Stripe configurada (proyecto de práctica, sin cuenta real),
    se redirige a una pasarela simulada propia con el mismo look & feel del flujo real.
    """
    if not settings.STRIPE_SECRET_KEY:
        return reverse('simulated_payment_page', args=[order.id, 'stripe'])

    stripe.api_key = settings.STRIPE_SECRET_KEY
    site_url = get_site_url(request)

    line_items = []
    for item in order.items.select_related('product', 'variant__color', 'variant__size').all():
        variant_desc = f" ({item.variant.color.name} / Talla {item.variant.size.name})" if item.variant else ""
        line_items.append({
            'price_data': {
                # PYG es moneda "zero-decimal" en Stripe: el monto va en guaraníes enteros, no en centavos.
                'currency': 'pyg',
                'product_data': {'name': f"{item.product.name}{variant_desc}"},
                'unit_amount': int(round(item.price)),
            },
            'quantity': item.quantity,
        })

    session = stripe.checkout.Session.create(
        mode='payment',
        payment_method_types=['card'],
        line_items=line_items,
        customer_email=order.email,
        metadata={'order_id': str(order.id)},
        success_url=f"{site_url}/checkout/success/?id={order.id}&session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{site_url}/checkout/pago-cancelado/?id={order.id}",
    )
    return session.url


def create_mercadopago_preference(request, order):
    """Crea una preferencia de MercadoPago Checkout Pro (pago hospedado) y devuelve la URL de pago.

    Si no hay un access token de MercadoPago configurado (proyecto de práctica, sin cuenta real),
    se redirige a una pasarela simulada propia con el mismo look & feel del flujo real.
    """
    if not settings.MERCADOPAGO_ACCESS_TOKEN:
        return reverse('simulated_payment_page', args=[order.id, 'mercadopago'])

    sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
    site_url = get_site_url(request)

    items = []
    for item in order.items.select_related('product', 'variant__color', 'variant__size').all():
        variant_desc = f" ({item.variant.color.name} / Talla {item.variant.size.name})" if item.variant else ""
        items.append({
            'title': f"{item.product.name}{variant_desc}",
            'quantity': item.quantity,
            'unit_price': float(item.price),
            'currency_id': 'PYG',
        })

    preference_data = {
        'items': items,
        'payer': {
            'name': order.first_name,
            'surname': order.last_name,
            'email': order.email,
        },
        'external_reference': str(order.id),
        'back_urls': {
            'success': f"{site_url}/checkout/success/?id={order.id}",
            'failure': f"{site_url}/checkout/pago-cancelado/?id={order.id}",
            'pending': f"{site_url}/checkout/pago-cancelado/?id={order.id}",
        },
        'auto_return': 'approved',
        'notification_url': f"{site_url}{reverse('mercadopago_webhook')}",
    }
    preference_response = sdk.preference().create(preference_data)
    preference = preference_response['response']
    checkout_url = preference.get('init_point') or preference.get('sandbox_init_point')

    if not checkout_url:
        # El SDK de MercadoPago no lanza excepción ante errores HTTP: hay que revisar la respuesta a mano.
        error_detail = preference.get('message') or preference.get('error') or preference_response
        raise RuntimeError(f"MercadoPago rechazó la preferencia de pago: {error_detail}")

    return checkout_url


def get_stripe_session_payment_status(session_id):
    """Consulta directamente a Stripe si una sesión ya fue pagada (fallback si el webhook todavía no llegó)."""
    stripe.api_key = settings.STRIPE_SECRET_KEY
    session = stripe.checkout.Session.retrieve(session_id)
    return session.payment_status == 'paid', session.payment_intent


def get_mercadopago_payment_status(payment_id):
    """Consulta directamente a MercadoPago el estado de un pago (fallback si el webhook todavía no llegó)."""
    sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
    payment = sdk.payment().get(payment_id)['response']
    return payment.get('status') == 'approved', payment.get('external_reference'), str(payment.get('id'))
