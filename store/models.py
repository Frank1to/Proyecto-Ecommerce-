from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nombre")
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True, verbose_name="Descripción")

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category, related_name='products', on_delete=models.CASCADE, verbose_name="Categoría")
    name = models.CharField(max_length=200, verbose_name="Nombre")
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(verbose_name="Descripción")
    price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Precio base (Gs. o USD)")
    image = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name="Imagen principal")
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Última modificación")

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def average_rating(self):
        reviews = self.reviews.all()
        if not reviews:
            return 0
        return sum(review.rating for review in reviews) / len(reviews)


class Color(models.Model):
    name = models.CharField(max_length=50, verbose_name="Color")
    hex_code = models.CharField(max_length=7, default="#FFFFFF", help_text="Ejemplo: #FF0000 para rojo", verbose_name="Código Hexadecimal")

    class Meta:
        verbose_name = "Color"
        verbose_name_plural = "Colores"

    def __str__(self):
        return self.name


class Size(models.Model):
    name = models.CharField(max_length=50, verbose_name="Talla/Tamaño")

    class Meta:
        verbose_name = "Talla"
        verbose_name_plural = "Tallas"

    def __str__(self):
        return self.name


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, related_name='variants', on_delete=models.CASCADE, verbose_name="Producto")
    color = models.ForeignKey(Color, on_delete=models.CASCADE, verbose_name="Color")
    size = models.ForeignKey(Size, on_delete=models.CASCADE, verbose_name="Talla")
    stock = models.IntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Stock disponible")
    price_override = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Dejar en blanco si usa el precio base del producto", verbose_name="Precio alternativo")

    class Meta:
        verbose_name = "Variante de Producto"
        verbose_name_plural = "Variantes de Productos"
        unique_together = ('product', 'color', 'size')

    def __str__(self):
        return f"{self.product.name} - Color: {self.color.name}, Talla: {self.size.name} (Stock: {self.stock})"

    @property
    def price(self):
        if self.price_override is not None:
            return self.price_override
        return self.product.price


class Coupon(models.Model):
    DISCOUNT_TYPES = (
        ('percentage', 'Porcentaje (%)'),
        ('fixed', 'Monto Fijo'),
    )
    code = models.CharField(max_length=50, unique=True, verbose_name="Código de Cupón")
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES, default='percentage', verbose_name="Tipo de Descuento")
    discount_value = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Valor de Descuento")
    active = models.BooleanField(default=True, verbose_name="Activo")
    valid_from = models.DateTimeField(verbose_name="Válido desde")
    valid_to = models.DateTimeField(verbose_name="Válido hasta")

    class Meta:
        verbose_name = "Cupón de Descuento"
        verbose_name_plural = "Cupones de Descuento"

    def __str__(self):
        return f"{self.code} ({self.get_discount_type_display()}: {self.discount_value})"

    def is_valid(self):
        now = timezone.now()
        return self.active and self.valid_from <= now <= self.valid_to


class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pendiente de Pago'),
        ('paid', 'Pagado'),
        ('shipped', 'Enviado'),
        ('cancelled', 'Cancelado'),
    )
    first_name = models.CharField(max_length=100, verbose_name="Nombre")
    last_name = models.CharField(max_length=100, verbose_name="Apellido")
    email = models.EmailField(verbose_name="Correo Electrónico")
    address = models.CharField(max_length=250, verbose_name="Dirección de Envío")
    city = models.CharField(max_length=100, verbose_name="Ciudad")
    country = models.CharField(max_length=100, default="Paraguay", verbose_name="País")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Total del Pedido")
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders', verbose_name="Cupón aplicado")
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Monto Descontado")
    paid = models.BooleanField(default=False, verbose_name="¿Está pagado?")
    payment_id = models.CharField(max_length=150, blank=True, null=True, verbose_name="ID de Transacción")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Estado de la Orden")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Fecha de Actualización")

    class Meta:
        verbose_name = "Pedido / Orden"
        verbose_name_plural = "Pedidos / Órdenes"
        ordering = ('-created_at',)

    def __str__(self):
        return f"Orden #{self.id} - {self.first_name} {self.last_name}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE, verbose_name="Pedido")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Producto")
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Variante")
    price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Precio de compra")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Cantidad")

    class Meta:
        verbose_name = "Ítem de Pedido"
        verbose_name_plural = "Ítems de Pedidos"

    def __str__(self):
        variant_desc = f" ({self.variant.color.name} - {self.variant.size.name})" if self.variant else ""
        return f"{self.quantity}x {self.product.name}{variant_desc}"

    @property
    def subtotal(self):
        return self.price * self.quantity


class Review(models.Model):
    product = models.ForeignKey(Product, related_name='reviews', on_delete=models.CASCADE, verbose_name="Producto")
    user_name = models.CharField(max_length=100, verbose_name="Nombre de Usuario")
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], verbose_name="Calificación (1-5)")
    comment = models.TextField(verbose_name="Comentario")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha")

    class Meta:
        verbose_name = "Reseña / Calificación"
        verbose_name_plural = "Reseñas / Calificaciones"
        ordering = ('-created_at',)

    def __str__(self):
        return f"Reseña de {self.user_name} para {self.product.name} ({self.rating}★)"
