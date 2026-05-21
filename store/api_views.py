import uuid
from decimal import Decimal
from django.db import transaction
from rest_framework import viewsets, generics, status, views
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import Product, Review, Coupon, Order, OrderItem, ProductVariant
from .serializers import ProductSerializer, ReviewSerializer, CouponSerializer, OrderSerializer

# 1. API ViewSet para catálogo de Productos (Listado y Detalle)
class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.filter(is_active=True).prefetch_related('variants__color', 'variants__size', 'reviews')
    serializer_class = ProductSerializer
    lookup_field = 'slug'

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtro de categoría por slug
        category_slug = self.request.query_params.get('category')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
            
        # Filtro de búsqueda por término
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search) | queryset.filter(description__icontains=search)
            
        return queryset


# 2. API View para Enviar una Reseña
class ReviewCreateAPIView(generics.CreateAPIView):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer

    def perform_create(self, serializer):
        product_id = self.request.data.get('product')
        product = get_object_or_404(Product, id=product_id)
        serializer.save(product=product)


# 3. API View para Validar y Aplicar un Cupón
class CouponValidateAPIView(views.APIView):
    def post(self, request, *args, **kwargs):
        code = request.data.get('code', '').strip().upper()
        if not code:
            return Response({'message': 'Código no provisto.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            coupon = Coupon.objects.get(code=code)
            if coupon.is_valid():
                serializer = CouponSerializer(coupon)
                return Response({
                    'valid': True,
                    'message': f'Cupón {coupon.code} es válido.',
                    'coupon': serializer.data
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'valid': False,
                    'message': 'El cupón ha expirado o está desactivado.'
                }, status=status.HTTP_400_BAD_REQUEST)
        except Coupon.DoesNotExist:
            return Response({
                'valid': False,
                'message': 'El cupón ingresado no existe.'
            }, status=status.HTTP_404_NOT_FOUND)


# 4. API View para Procesar checkout mediante JSON
class APICheckoutView(views.APIView):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        data = request.data
        
        # Validar datos de facturación
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        email = data.get('email', '').strip()
        address = data.get('address', '').strip()
        city = data.get('city', '').strip()
        country = data.get('country', 'Paraguay').strip()
        items = data.get('items', []) # Array de { variant_id, quantity }
        coupon_code = data.get('coupon_code', '').strip().upper()

        if not (first_name and last_name and email and address and city and items):
            return Response({
                'message': 'Faltan datos requeridos (facturación o ítems de compra).'
            }, status=status.HTTP_400_BAD_REQUEST)

        # 1. Calcular precios del carrito e ítems
        total_subtotal = Decimal('0.00')
        validated_items = []

        for item in items:
            var_id = item.get('variant_id')
            qty = int(item.get('quantity', 1))
            
            db_variant = get_object_or_404(ProductVariant.objects.select_for_update(), id=var_id)
            
            # Verificar stock
            if db_variant.stock < qty:
                return Response({
                    'message': f"Stock insuficiente para {db_variant.product.name} ({db_variant.color.name} - {db_variant.size.name}). Stock disponible: {db_variant.stock}."
                }, status=status.HTTP_400_BAD_REQUEST)
                
            item_price = db_variant.price
            item_subtotal = item_price * qty
            total_subtotal += item_subtotal
            
            validated_items.append({
                'variant': db_variant,
                'quantity': qty,
                'price': item_price
            })

        # 2. Aplicar Cupón si existe
        coupon = None
        discount_amount = Decimal('0.00')
        if coupon_code:
            coupon = Coupon.objects.filter(code=coupon_code).first()
            if coupon and coupon.is_valid():
                if coupon.discount_type == 'percentage':
                    discount_amount = total_subtotal * (coupon.discount_value / Decimal('100'))
                else:
                    discount_amount = coupon.discount_value
                    if discount_amount > total_subtotal:
                        discount_amount = total_subtotal
            else:
                return Response({'message': 'El cupón de descuento no es válido o ha vencido.'}, status=status.HTTP_400_BAD_REQUEST)

        final_total = total_subtotal - discount_amount
        if final_total < 0:
            final_total = Decimal('0.00')

        # Simular procesamiento de pago con tarjeta
        sim_success = data.get('payment_success', True)
        if not sim_success:
            return Response({'message': 'El pago fue rechazado por la pasarela bancaria.'}, status=status.HTTP_402_PAYMENT_REQUIRED)

        payment_id = f"PAY-API-{uuid.uuid4().hex[:10].upper()}"

        # 3. Registrar la Orden
        order = Order.objects.create(
            first_name=first_name,
            last_name=last_name,
            email=email,
            address=address,
            city=city,
            country=country,
            total_amount=final_total,
            coupon=coupon,
            discount_amount=discount_amount,
            paid=True,
            payment_id=payment_id,
            status='paid'
        )

        # 4. Registrar ítems y reducir stock
        for v_item in validated_items:
            db_variant = v_item['variant']
            qty = v_item['quantity']
            
            # Descontar del stock físico
            db_variant.stock -= qty
            db_variant.save()
            
            OrderItem.objects.create(
                order=order,
                product=db_variant.product,
                variant=db_variant,
                price=v_item['price'],
                quantity=qty
            )

        serializer = OrderSerializer(order)
        return Response({
            'success': True,
            'message': 'Orden procesada y pagada con éxito en la API.',
            'order': serializer.data
        }, status=status.HTTP_201_CREATED)
