import json
import uuid
import stripe
from decimal import Decimal
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User

from .models import Category, Product, Color, Size, ProductVariant, Coupon, Order, OrderItem, Review
from .cart import Cart
from .utils import generate_invoice_pdf
from .payments import (
    create_stripe_checkout_session,
    create_mercadopago_preference,
    get_stripe_session_payment_status,
    get_mercadopago_payment_status,
)


# 0. AUTENTICACIÓN DE CLIENTES (registro / login / logout - el login es opcional para comprar)
def register_view(request):
    if request.user.is_authenticated:
        return redirect('product_list')

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        if not (first_name and last_name and username and email and password1 and password2):
            messages.error(request, 'Completá todos los campos para registrarte.')
        elif password1 != password2:
            messages.error(request, 'Las contraseñas no coinciden.')
        elif len(password1) < 8:
            messages.error(request, 'La contraseña debe tener al menos 8 caracteres.')
        elif User.objects.filter(username__iexact=username).exists():
            messages.error(request, 'Ese nombre de usuario ya está en uso.')
        elif User.objects.filter(email__iexact=email).exists():
            messages.error(request, 'Ya existe una cuenta registrada con ese correo.')
        else:
            user = User.objects.create_user(
                username=username, email=email, password=password1,
                first_name=first_name, last_name=last_name,
            )
            login(request, user)
            messages.success(request, f'¡Bienvenido, {first_name}! Tu cuenta fue creada con éxito.')
            return redirect('product_list')

    return render(request, 'store/register.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('product_list')

    next_url = request.POST.get('next') or request.GET.get('next') or 'product_list'

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect(next_url)
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')

    return render(request, 'store/login.html', {'next': next_url})


@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, 'Cerraste sesión correctamente.')
    return redirect('product_list')


# 1. CATÁLOGO / INICIO
def product_list(request):
    categories = Category.objects.all()
    products = Product.objects.filter(is_active=True).prefetch_related('reviews')
    
    # Filtrar por categoría
    category_slug = request.GET.get('category')
    active_category = None
    if category_slug:
        active_category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=active_category)
        
    # Buscar por palabra clave
    query = request.GET.get('q')
    if query:
        products = products.filter(name__icontains=query) | products.filter(description__icontains=query)

    # Añadir rating promedio calculado a cada producto para mostrar estrellas en listado
    for p in products:
        p.avg_stars = round(p.average_rating)
        p.review_count = p.reviews.count()

    context = {
        'categories': categories,
        'products': products,
        'active_category': active_category,
        'search_query': query,
    }
    return render(request, 'store/product_list.html', context)


# 2. DETALLE DE PRODUCTO
def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    reviews = product.reviews.all()
    
    # Obtener variantes disponibles
    variants = product.variants.all().select_related('color', 'size')
    
    # Organizar colores y tallas únicos disponibles para este producto
    colors = Color.objects.filter(id__in=variants.values_list('color_id', flat=True).distinct())
    sizes = Size.objects.filter(id__in=variants.values_list('size_id', flat=True).distinct())
    
    # Formatear variantes en JSON para interacción rápida en el frontend
    variants_json = []
    for var in variants:
        variants_json.append({
            'id': var.id,
            'color_id': var.color.id,
            'color_name': var.color.name,
            'size_id': var.size.id,
            'size_name': var.size.name,
            'stock': var.stock,
            'price': float(var.price),
            'price_formatted': f"Gs. {var.price:,.0f}" if var.price >= 1000 else f"${var.price:.2f}"
        })

    avg_stars = round(product.average_rating)
    stars_range = range(1, 6)

    context = {
        'product': product,
        'variants': variants,
        'colors': colors,
        'sizes': sizes,
        'variants_json': json.dumps(variants_json),
        'reviews': reviews,
        'avg_stars': avg_stars,
        'stars_range': stars_range,
    }
    return render(request, 'store/product_detail.html', context)


# 3. CREAR RESEÑA (POST)
@require_POST
def add_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    user_name = request.POST.get('user_name', 'Anónimo').strip()
    rating = int(request.POST.get('rating', 5))
    comment = request.POST.get('comment', '').strip()
    
    if not user_name:
        user_name = 'Anónimo'
        
    Review.objects.create(
        product=product,
        user_name=user_name,
        rating=rating,
        comment=comment
    )
    return redirect('product_detail', slug=product.slug)


# 4. CARRITO DE COMPRAS - DETALLE
def cart_detail(request):
    cart = Cart(request)
    coupon_id = request.session.get('coupon_id')
    coupon = None
    discount = Decimal('0.00')
    
    if coupon_id:
        try:
            coupon = Coupon.objects.get(id=coupon_id)
            if coupon.is_valid():
                total_price = cart.get_total_price()
                if coupon.discount_type == 'percentage':
                    discount = total_price * (coupon.discount_value / Decimal('100'))
                else:
                    discount = coupon.discount_value
                    if discount > total_price:
                        discount = total_price
            else:
                del request.session['coupon_id']
        except Coupon.DoesNotExist:
            del request.session['coupon_id']
            
    final_total = cart.get_total_price() - discount
    if final_total < 0:
        final_total = Decimal('0.00')

    context = {
        'cart': cart,
        'coupon': coupon,
        'discount': discount,
        'final_total': final_total
    }
    return render(request, 'store/cart.html', context)


# 5. AÑADIR AL CARRITO (AJAX POST)
@require_POST
def cart_add(request):
    cart = Cart(request)
    variant_id = request.POST.get('variant_id')
    quantity = int(request.POST.get('quantity', 1))
    
    variant = get_object_or_404(ProductVariant, id=variant_id)
    
    if variant.stock == 0:
        return JsonResponse({'success': False, 'message': 'Este artículo no tiene stock disponible.'}, status=400)
        
    new_qty = cart.add(variant=variant, quantity=quantity)
    
    return JsonResponse({
        'success': True,
        'message': f'Se agregaron {quantity} unidades al carrito.',
        'cart_length': len(cart),
        'added_qty': new_qty
    })


# 6. ACTUALIZAR CANTIDAD EN EL CARRITO (AJAX POST)
@require_POST
def cart_update(request):
    cart = Cart(request)
    variant_id = request.POST.get('variant_id')
    quantity = int(request.POST.get('quantity', 1))
    
    variant = get_object_or_404(ProductVariant, id=variant_id)
    
    # Validar stock
    if quantity > variant.stock:
        quantity = variant.stock
        message = f'Cantidad limitada al stock disponible ({variant.stock} unidades).'
        limited = True
    else:
        message = 'Cantidad actualizada.'
        limited = False
        
    actual_qty = cart.add(variant=variant, quantity=quantity, override_quantity=True)
    
    subtotal = variant.price * actual_qty
    cart_total = cart.get_total_price()
    
    # Recalcular cupones si aplica
    coupon_id = request.session.get('coupon_id')
    discount = Decimal('0.00')
    if coupon_id:
        coupon = Coupon.objects.filter(id=coupon_id).first()
        if coupon and coupon.is_valid():
            if coupon.discount_type == 'percentage':
                discount = cart_total * (coupon.discount_value / Decimal('100'))
            else:
                discount = coupon.discount_value
                if discount > cart_total:
                    discount = cart_total
                    
    final_total = cart_total - discount
    if final_total < 0:
        final_total = Decimal('0.00')
        
    return JsonResponse({
        'success': True,
        'message': message,
        'quantity': actual_qty,
        'limited': limited,
        'subtotal_formatted': f"Gs. {subtotal:,.0f}" if subtotal >= 1000 else f"${subtotal:.2f}",
        'cart_total_formatted': f"Gs. {cart_total:,.0f}" if cart_total >= 1000 else f"${cart_total:.2f}",
        'discount_formatted': f"Gs. {discount:,.0f}" if discount >= 1000 else f"${discount:.2f}",
        'final_total_formatted': f"Gs. {final_total:,.0f}" if final_total >= 1000 else f"${final_total:.2f}",
        'cart_length': len(cart)
    })


# 7. ELIMINAR DEL CARRITO (AJAX POST)
@require_POST
def cart_remove(request):
    cart = Cart(request)
    variant_id = request.POST.get('variant_id')
    variant = get_object_or_404(ProductVariant, id=variant_id)
    
    cart.remove(variant)
    
    cart_total = cart.get_total_price()
    
    # Recalcular descuentos
    coupon_id = request.session.get('coupon_id')
    discount = Decimal('0.00')
    if coupon_id:
        coupon = Coupon.objects.filter(id=coupon_id).first()
        if coupon and coupon.is_valid():
            if coupon.discount_type == 'percentage':
                discount = cart_total * (coupon.discount_value / Decimal('100'))
            else:
                discount = coupon.discount_value
                if discount > cart_total:
                    discount = cart_total
                    
    final_total = cart_total - discount
    if final_total < 0:
        final_total = Decimal('0.00')

    return JsonResponse({
        'success': True,
        'message': 'Artículo eliminado del carrito.',
        'cart_total_formatted': f"Gs. {cart_total:,.0f}" if cart_total >= 1000 else f"${cart_total:.2f}",
        'discount_formatted': f"Gs. {discount:,.0f}" if discount >= 1000 else f"${discount:.2f}",
        'final_total_formatted': f"Gs. {final_total:,.0f}" if final_total >= 1000 else f"${final_total:.2f}",
        'cart_length': len(cart)
    })


# 8. APLICAR CUPÓN DE DESCUENTO (AJAX POST)
@require_POST
def apply_coupon(request):
    cart = Cart(request)
    code = request.POST.get('coupon_code', '').strip().upper()
    
    if len(cart) == 0:
        return JsonResponse({'success': False, 'message': 'El carrito está vacío.'}, status=400)
        
    try:
        coupon = Coupon.objects.get(code=code)
        if not coupon.is_valid():
            return JsonResponse({'success': False, 'message': 'El cupón ha vencido o no está activo.'}, status=400)
            
        request.session['coupon_id'] = coupon.id
        
        # Calcular montos
        cart_total = cart.get_total_price()
        if coupon.discount_type == 'percentage':
            discount = cart_total * (coupon.discount_value / Decimal('100'))
        else:
            discount = coupon.discount_value
            if discount > cart_total:
                discount = cart_total
                
        final_total = cart_total - discount
        if final_total < 0:
            final_total = Decimal('0.00')

        return JsonResponse({
            'success': True,
            'message': f'Cupón {coupon.code} aplicado con éxito.',
            'discount_formatted': f"Gs. {discount:,.0f}" if discount >= 1000 else f"${discount:.2f}",
            'final_total_formatted': f"Gs. {final_total:,.0f}" if final_total >= 1000 else f"${final_total:.2f}",
            'coupon_code': coupon.code,
            'discount_type': coupon.discount_type,
            'discount_value': float(coupon.discount_value)
        })
    except Coupon.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'El cupón no es válido o no existe.'}, status=404)


# 9. PÁGINA DE CHECKOUT
def checkout(request):
    cart = Cart(request)
    if len(cart) == 0:
        return redirect('product_list')
        
    # Obtener cupón si está aplicado en la sesión
    coupon_id = request.session.get('coupon_id')
    coupon = None
    discount = Decimal('0.00')
    
    if coupon_id:
        coupon = Coupon.objects.filter(id=coupon_id).first()
        if coupon and coupon.is_valid():
            cart_total = cart.get_total_price()
            if coupon.discount_type == 'percentage':
                discount = cart_total * (coupon.discount_value / Decimal('100'))
            else:
                discount = coupon.discount_value
                if discount > cart_total:
                    discount = cart_total
        else:
            if 'coupon_id' in request.session:
                del request.session['coupon_id']
                
    final_total = cart.get_total_price() - discount
    if final_total < 0:
        final_total = Decimal('0.00')

    context = {
        'cart': cart,
        'coupon': coupon,
        'discount': discount,
        'final_total': final_total,
        'billing': _prefill_billing(request),
    }
    return render(request, 'store/checkout.html', context)


# 9b. HELPER - Datos para precargar el formulario de facturación de un usuario logueado
def _prefill_billing(request):
    if not request.user.is_authenticated:
        return {}
    return {
        'first_name': request.user.first_name,
        'last_name': request.user.last_name,
        'email': request.user.email,
    }


# 10. INICIAR PAGO REAL (AJAX POST) - Crea la orden en estado "pendiente",
# reserva el stock y redirige a Stripe Checkout o MercadoPago Checkout Pro.
@require_POST
def checkout_pay(request):
    cart = Cart(request)
    if len(cart) == 0:
        return JsonResponse({'success': False, 'message': 'El carrito está vacío.'}, status=400)

    # Obtener datos de facturación
    first_name = request.POST.get('first_name', '').strip()
    last_name = request.POST.get('last_name', '').strip()
    email = request.POST.get('email', '').strip()
    address = request.POST.get('address', '').strip()
    city = request.POST.get('city', '').strip()
    country = request.POST.get('country', 'Paraguay').strip()
    gateway = request.POST.get('gateway')

    if not (first_name and last_name and email and address and city):
        return JsonResponse({'success': False, 'message': 'Por favor completá todos los campos de facturación.'}, status=400)

    if gateway not in ('stripe', 'mercadopago'):
        return JsonResponse({'success': False, 'message': 'Elegí un método de pago válido.'}, status=400)

    # Obtener cupón si aplica
    coupon_id = request.session.get('coupon_id')
    coupon = None
    discount = Decimal('0.00')
    if coupon_id:
        coupon = Coupon.objects.filter(id=coupon_id).first()
        if coupon and coupon.is_valid():
            cart_total = cart.get_total_price()
            if coupon.discount_type == 'percentage':
                discount = cart_total * (coupon.discount_value / Decimal('100'))
            else:
                discount = coupon.discount_value
                if discount > cart_total:
                    discount = cart_total

    final_total = cart.get_total_price() - discount
    if final_total < 0:
        final_total = Decimal('0.00')

    try:
        # Usar transacción atómica para crear la orden pendiente y reservar el stock de forma segura
        with transaction.atomic():
            order = Order.objects.create(
                user=request.user if request.user.is_authenticated else None,
                first_name=first_name,
                last_name=last_name,
                email=email,
                address=address,
                city=city,
                country=country,
                total_amount=final_total,
                coupon=coupon,
                discount_amount=discount,
                paid=False,
                status='pending',
                payment_method=gateway,
            )

            for item in cart:
                variant = item['variant']
                quantity = item['quantity']

                db_variant = ProductVariant.objects.select_for_update().get(id=variant.id)
                if db_variant.stock < quantity:
                    raise ValueError(f"Lo sentimos, ya no queda stock suficiente para {db_variant.product.name} ({db_variant.color.name} - {db_variant.size.name}). Stock disponible: {db_variant.stock}.")

                db_variant.stock -= quantity
                db_variant.save()

                OrderItem.objects.create(
                    order=order,
                    product=db_variant.product,
                    variant=db_variant,
                    price=item['price'],
                    quantity=quantity
                )
    except ValueError as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

    # Crear la sesión de pago en la pasarela elegida
    try:
        if gateway == 'stripe':
            checkout_url = create_stripe_checkout_session(request, order)
        else:
            checkout_url = create_mercadopago_preference(request, order)
    except Exception as e:
        _restock_and_cancel(order)
        return JsonResponse({'success': False, 'message': f'No se pudo iniciar el pago: {e}'}, status=502)

    if not checkout_url:
        _restock_and_cancel(order)
        return JsonResponse({'success': False, 'message': 'La pasarela no devolvió una URL de pago válida.'}, status=502)

    # La orden quedó reservada del lado nuestro; limpiar carrito y cupón de la sesión
    cart.clear()
    if 'coupon_id' in request.session:
        del request.session['coupon_id']

    placed_orders = request.session.get('placed_orders', [])
    placed_orders.append(order.id)
    request.session['placed_orders'] = placed_orders

    return JsonResponse({'success': True, 'checkout_url': checkout_url})


def _restock_and_cancel(order):
    """Devuelve el stock reservado por una orden pendiente y la marca como cancelada."""
    with transaction.atomic():
        for order_item in order.items.select_related('variant'):
            if order_item.variant:
                db_variant = ProductVariant.objects.select_for_update().get(id=order_item.variant_id)
                db_variant.stock += order_item.quantity
                db_variant.save()
        order.status = 'cancelled'
        order.save()


# 10b. VOLVER DE UN PAGO CANCELADO/RECHAZADO (Stripe cancel_url / MercadoPago back_urls failure|pending)
def payment_cancel(request):
    order_id = request.GET.get('id')
    order = get_object_or_404(Order, id=order_id)

    if order.status == 'pending' and not order.paid:
        _restock_and_cancel(order)

    return render(request, 'store/payment_cancel.html', {'order': order})


# 10b-bis. PASARELA SIMULADA (se usa cuando no hay claves reales de Stripe/MercadoPago
# configuradas en .env - pensado para practicar/demostrar el flujo sin cuenta real)
def simulated_payment_page(request, order_id, gateway):
    order = get_object_or_404(Order, id=order_id, payment_method=gateway)

    if order.paid or order.status != 'pending':
        return redirect(f"/checkout/success/?id={order.id}")

    return render(request, 'store/simulated_payment.html', {'order': order, 'gateway': gateway})


@require_POST
def simulated_payment_confirm(request, order_id, gateway):
    order = get_object_or_404(Order, id=order_id, payment_method=gateway)
    approved = request.POST.get('result') == 'approved'

    if order.status == 'pending' and not order.paid:
        if approved:
            order.paid = True
            order.status = 'paid'
            order.payment_id = f"SIM-{gateway.upper()}-{uuid.uuid4().hex[:10].upper()}"
            order.save()
        else:
            _restock_and_cancel(order)

    if order.paid:
        return redirect(f"/checkout/success/?id={order.id}")
    return redirect(f"/checkout/pago-cancelado/?id={order.id}")


# 10c. WEBHOOK DE STRIPE - confirma el pago de forma asíncrona y segura (fuente de verdad)
@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        order_id = (session.get('metadata') or {}).get('order_id')
        if order_id:
            order = Order.objects.filter(id=order_id).first()
            if order and not order.paid:
                order.paid = True
                order.status = 'paid'
                order.payment_id = session.get('payment_intent') or session.get('id', '')
                order.save()

    return HttpResponse(status=200)


# 10d. WEBHOOK DE MERCADOPAGO - confirma el pago de forma asíncrona y segura (fuente de verdad)
@csrf_exempt
def mercadopago_webhook(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    payment_id = request.GET.get('data.id') or request.GET.get('id')
    topic = request.GET.get('type') or request.GET.get('topic')

    if not payment_id:
        try:
            body = json.loads(request.body or '{}')
            payment_id = (body.get('data') or {}).get('id')
            topic = topic or body.get('type')
        except json.JSONDecodeError:
            pass

    if topic == 'payment' and payment_id:
        try:
            approved, order_id, gateway_payment_id = get_mercadopago_payment_status(payment_id)
        except Exception:
            return HttpResponse(status=200)

        if approved and order_id:
            order = Order.objects.filter(id=order_id).first()
            if order and not order.paid:
                order.paid = True
                order.status = 'paid'
                order.payment_id = gateway_payment_id
                order.save()

    return HttpResponse(status=200)


# 11. PÁGINA DE ÉXITO DE ORDEN
def order_success(request):
    order_id = request.GET.get('id')
    if not order_id:
        raise Http404("Orden no encontrada.")

    order = get_object_or_404(Order, id=order_id)

    # El webhook es la fuente de verdad, pero puede tardar unos segundos en llegar.
    # Al volver de la pasarela verificamos también de forma directa para confirmar al toque.
    if not order.paid and order.status == 'pending':
        try:
            if order.payment_method == 'stripe':
                session_id = request.GET.get('session_id')
                if session_id:
                    approved, payment_intent = get_stripe_session_payment_status(session_id)
                    if approved:
                        order.paid = True
                        order.status = 'paid'
                        order.payment_id = payment_intent
                        order.save()
            elif order.payment_method == 'mercadopago':
                payment_id = request.GET.get('payment_id')
                if payment_id:
                    approved, ref_order_id, gateway_payment_id = get_mercadopago_payment_status(payment_id)
                    if approved and str(order.id) == str(ref_order_id):
                        order.paid = True
                        order.status = 'paid'
                        order.payment_id = gateway_payment_id
                        order.save()
        except Exception:
            pass

    if not order.paid:
        return render(request, 'store/order_pending.html', {'order': order})

    # Formatear montos
    total_str = f"Gs. {order.total_amount:,.0f}" if order.total_amount >= 1000 else f"${order.total_amount:.2f}"
    discount_str = f"Gs. {order.discount_amount:,.0f}" if order.discount_amount >= 1000 else f"${order.discount_amount:.2f}"

    context = {
        'order': order,
        'total_formatted': total_str,
        'discount_formatted': discount_str
    }
    return render(request, 'store/order_success.html', context)


# 12. HISTORIAL DE ÓRDENES
def order_history(request):
    # Obtener las órdenes de la sesión (compras como invitado)
    placed_order_ids = request.session.get('placed_orders', [])

    if request.user.is_authenticated:
        # Si está logueado, sumar también las órdenes asociadas a su cuenta (desde cualquier dispositivo)
        orders = Order.objects.filter(
            Q(user=request.user) | Q(id__in=placed_order_ids)
        ).distinct().prefetch_related('items__product')
    else:
        orders = Order.objects.filter(id__in=placed_order_ids).prefetch_related('items__product')
    
    # Formatear totales
    for o in orders:
        o.total_formatted = f"Gs. {o.total_amount:,.0f}" if o.total_amount >= 1000 else f"${o.total_amount:.2f}"
        o.item_count = sum(item.quantity for item in o.items.all())
        
    context = {
        'orders': orders
    }
    return render(request, 'store/order_history.html', context)


# 13. DESCARGAR FACTURA PDF
def download_invoice(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    if not (order.paid or order.status == 'paid'):
        return HttpResponse("La factura solo está disponible para órdenes pagadas.", status=400)
        
    pdf_content = generate_invoice_pdf(order)
    
    response = HttpResponse(pdf_content, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="factura_orden_{order.id}.pdf"'
    return response
