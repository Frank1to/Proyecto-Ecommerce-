import json
import uuid
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db import transaction

from .models import Category, Product, Color, Size, ProductVariant, Coupon, Order, OrderItem, Review
from .cart import Cart
from .utils import generate_invoice_pdf

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
        'final_total': final_total
    }
    return render(request, 'store/checkout.html', context)


# 10. PROCESAR ORDEN / PAGO (AJAX POST)
@require_POST
def process_order(request):
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
    
    if not (first_name and last_name and email and address and city):
        return JsonResponse({'success': False, 'message': 'Por favor completá todos los campos de facturación.'}, status=400)
        
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

    # Simular transacciones de pago con éxito
    payment_success = request.POST.get('payment_success', 'true') == 'true'
    
    if not payment_success:
        return JsonResponse({'success': False, 'message': 'El pago fue rechazado por el banco emisor de la tarjeta.'}, status=400)
        
    # Generar ID de transacción ficticia (MercadoPago o Stripe)
    payment_id = f"PAY-{uuid.uuid4().hex[:12].upper()}"

    try:
        # Usar transacción atómica para asegurar la integridad de la base de datos y descontar stock de forma segura
        with transaction.atomic():
            # 1. Crear la Orden
            order = Order.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=email,
                address=address,
                city=city,
                country=country,
                total_amount=final_total,
                coupon=coupon,
                discount_amount=discount,
                paid=True, # Pago procesado exitosamente
                payment_id=payment_id,
                status='paid'
            )
            
            # 2. Crear los Ítems de la orden y descontar stock
            for item in cart:
                variant = item['variant']
                quantity = item['quantity']
                
                # Bloquear y verificar stock de nuevo de forma segura
                db_variant = ProductVariant.objects.select_for_update().get(id=variant.id)
                if db_variant.stock < quantity:
                    raise ValueError(f"Lo sentimos, ya no queda stock suficiente para {db_variant.product.name} ({db_variant.color.name} - {db_variant.size.name}). Stock disponible: {db_variant.stock}.")
                
                # Descontar stock
                db_variant.stock -= quantity
                db_variant.save()
                
                # Registrar el ítem
                OrderItem.objects.create(
                    order=order,
                    product=db_variant.product,
                    variant=db_variant,
                    price=item['price'],
                    quantity=quantity
                )

        # Si todo salió bien, vaciar carrito y cupones de la sesión
        cart.clear()
        if 'coupon_id' in request.session:
            del request.session['coupon_id']
            
        # Almacenar la orden en la sesión del usuario para su historial sin login obligatorio
        placed_orders = request.session.get('placed_orders', [])
        placed_orders.append(order.id)
        request.session['placed_orders'] = placed_orders
        request.session['last_order_id'] = order.id
        
        return JsonResponse({
            'success': True,
            'message': 'Orden creada y pagada con éxito.',
            'order_id': order.id,
            'redirect_url': f'/checkout/success/?id={order.id}'
        })
        
    except ValueError as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Ocurrió un error al procesar tu orden: {str(e)}'}, status=500)


# 11. PÁGINA DE ÉXITO DE ORDEN
def order_success(request):
    order_id = request.GET.get('id')
    if not order_id:
        raise Http404("Orden no encontrada.")
        
    order = get_object_or_404(Order, id=order_id)
    
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
    # Obtener las órdenes de la sesión
    placed_order_ids = request.session.get('placed_orders', [])
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
