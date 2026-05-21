import os
import django
from django.utils import timezone
from datetime import timedelta

# Configurar el entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from django.contrib.auth.models import User
from store.models import Category, Product, Color, Size, ProductVariant, Coupon, Review

def seed():
    print("Iniciando siembra de base de datos...")

    # 1. Crear Superusuario
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@tienda.com.py', 'admin123')
        print("Superusuario creado: admin / admin123")
    else:
        print("El superusuario 'admin' ya existe.")

    # Limpiar datos anteriores (opcional, para re-ejecuciones limpias)
    Category.objects.all().delete()
    Color.objects.all().delete()
    Size.objects.all().delete()
    Coupon.objects.all().delete()

    print("Limpieza de base de datos completada.")

    # 2. Crear Categorías
    calzado = Category.objects.create(name="Calzado Premium", description="Zapatillas y zapatos de altísima calidad para toda ocasión.")
    deportes = Category.objects.create(name="Ropa Deportiva", description="Prendas cómodas y de alto rendimiento para entrenar.")
    accesorios = Category.objects.create(name="Accesorios", description="Mochilas, gorros y complementos perfectos para tu outfit.")
    print("Categorías creadas.")

    # 3. Crear Colores
    negro = Color.objects.create(name="Negro Mate", hex_code="#1a1a1a")
    blanco = Color.objects.create(name="Blanco Puro", hex_code="#fcfcfc")
    rojo = Color.objects.create(name="Rojo Neón", hex_code="#ff2b55")
    azul = Color.objects.create(name="Azul Marino", hex_code="#1d4ed8")
    gris = Color.objects.create(name="Gris Urbano", hex_code="#6b7280")
    print("Colores creados.")

    # 4. Crear Tallas
    # Tallas de calzado
    t38 = Size.objects.create(name="38")
    t40 = Size.objects.create(name="40")
    t42 = Size.objects.create(name="42")
    # Tallas de ropa
    ts = Size.objects.create(name="S")
    tm = Size.objects.create(name="M")
    tl = Size.objects.create(name="L")
    txl = Size.objects.create(name="XL")
    print("Tallas creadas.")

    # 5. Crear Productos
    # Producto 1: Tenis Urban Run
    tenis = Product.objects.create(
        category=calzado,
        name="Tenis Urban Run Neon",
        description="Llevá tu carrera al siguiente nivel con los Tenis Urban Run Neon. Diseñados con una suela amortiguadora de alta tecnología, tejido transpirable y detalles reflectantes para mayor seguridad nocturna. Perfectos tanto para correr por Asunción como para un look casual de fin de semana.",
        price=450000.00,  # 450,000 Gs.
    )

    # Producto 2: Remera DryFit Training
    remera = Product.objects.create(
        category=deportes,
        name="Remera DryFit Training",
        description="Remera de alto rendimiento con tecnología de secado rápido. Su tela ultraliviana aleja el sudor de la piel manteniéndote fresco durante los entrenamientos más intensos. Costuras planas para evitar rozaduras.",
        price=145000.00,  # 145,000 Gs.
    )

    # Producto 3: Campera Rompevientos
    campera = Product.objects.create(
        category=deportes,
        name="Campera Rompevientos Impermeable",
        description="Protegerte de la lluvia y el viento ahora es más elegante. Esta campera liviana cuenta con capucha ajustable, bolsillos con cierres termosellados y un acabado impermeable que te mantendrá seco en cualquier tormenta.",
        price=380000.00,  # 380,000 Gs.
    )

    # Producto 4: Gorra Classic Fit
    gorra = Product.objects.create(
        category=accesorios,
        name="Gorra Classic Fit Sport",
        description="Gorra clásica con visera curva y cierre de correa ajustable en la parte trasera. Estilo atemporal hecho de algodón premium transpirable.",
        price=850000.00,  # 85,000 Gs. (En realidad, pongamos 85000.00)
    )
    gorra.price = 85000.00
    gorra.save()
    print("Productos principales creados.")

    # 6. Crear Variantes de Productos con Stock
    # Variantes de Tenis Urban Run Neon (Precios base, algunos con override)
    ProductVariant.objects.create(product=tenis, color=negro, size=t40, stock=8)
    ProductVariant.objects.create(product=tenis, color=negro, size=t42, stock=12)
    ProductVariant.objects.create(product=tenis, color=blanco, size=t38, stock=5)
    ProductVariant.objects.create(product=tenis, color=blanco, size=t40, stock=0)  # Agotado para probar UI
    ProductVariant.objects.create(product=tenis, color=rojo, size=t42, stock=4, price_override=480000.00) # Variante más cara
    
    # Variantes de Remera DryFit
    ProductVariant.objects.create(product=remera, color=azul, size=ts, stock=15)
    ProductVariant.objects.create(product=remera, color=azul, size=tm, stock=20)
    ProductVariant.objects.create(product=remera, color=azul, size=tl, stock=10)
    ProductVariant.objects.create(product=remera, color=gris, size=tm, stock=0)
    ProductVariant.objects.create(product=remera, color=gris, size=tl, stock=12)
    ProductVariant.objects.create(product=remera, color=negro, size=tm, stock=25)
    ProductVariant.objects.create(product=remera, color=negro, size=txl, stock=7)

    # Variantes de Campera Rompevientos
    ProductVariant.objects.create(product=campera, color=negro, size=tm, stock=10)
    ProductVariant.objects.create(product=campera, color=negro, size=tl, stock=15)
    ProductVariant.objects.create(product=campera, color=rojo, size=tm, stock=6)
    ProductVariant.objects.create(product=campera, color=rojo, size=tl, stock=3)

    # Variantes de Gorra (Talla única o pocas, usemos S y M)
    ProductVariant.objects.create(product=gorra, color=negro, size=tm, stock=30)
    ProductVariant.objects.create(product=gorra, color=gris, size=tm, stock=15)
    ProductVariant.objects.create(product=gorra, color=blanco, size=tm, stock=2)
    print("Variantes de productos creadas.")

    # 7. Crear Cupones de Descuento
    # Cupón de porcentaje (10% descuento)
    Coupon.objects.create(
        code="DESCUENTO10",
        discount_type="percentage",
        discount_value=10.00,
        active=True,
        valid_from=timezone.now() - timedelta(days=1),
        valid_to=timezone.now() + timedelta(days=30)
    )

    # Cupón de monto fijo (Gs. 50,000 descuento)
    Coupon.objects.create(
        code="PROMO50K",
        discount_type="fixed",
        discount_value=50000.00,
        active=True,
        valid_from=timezone.now() - timedelta(days=1),
        valid_to=timezone.now() + timedelta(days=30)
    )

    # Cupón expirado (para pruebas)
    Coupon.objects.create(
        code="EXPIRADO",
        discount_type="percentage",
        discount_value=25.00,
        active=True,
        valid_from=timezone.now() - timedelta(days=10),
        valid_to=timezone.now() - timedelta(days=1)
    )
    print("Cupones de prueba creados.")

    # 8. Crear Reseñas de Productos
    Review.objects.create(
        product=tenis,
        user_name="Juan Pérez",
        rating=5,
        comment="Excelente calzado, los Tenis Urban son comodísimos para correr en el parque Ñu Guasu. ¡Recomendados!"
    )
    Review.objects.create(
        product=tenis,
        user_name="María Giménez",
        rating=4,
        comment="Muy lindos y cómodos. El color rojo neón es llamativo y tiene buenísima amortiguación."
    )
    Review.objects.create(
        product=remera,
        user_name="Carlos Amarilla",
        rating=5,
        comment="Increíble relación calidad-precio. La tela DryFit es super fresca y no junta olor. Compraría más colores."
    )
    print("Reseñas creadas.")

    print("\n¡Base de datos sembrada con éxito!")
    print("Podes iniciar el servidor con: python manage.py runserver")
    print("E ingresar al panel de administración en http://127.0.0.1:8000/admin con:")
    print("Usuario: admin | Contraseña: admin123")

if __name__ == '__main__':
    seed()
