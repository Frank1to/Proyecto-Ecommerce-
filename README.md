# ⚡ Urban Boutique - E-commerce Premium API & Web App

Urban Boutique es una aplicación web y API de E-commerce de altísima calidad desarrollada en **Django** y **Django REST Framework**. Cuenta con un diseño visual moderno en modo oscuro (Vanilla CSS, *glassmorphism* y micro-animaciones fluidas), selectores dinámicos de variantes por color y talla, gestión de inventario, cupones, reseñas y facturación automática en PDF.

---

## ✨ Características Principales

*   **🎨 Diseño Premium UX/UI**: Temática oscura y sofisticada con efectos de vidrio y transiciones suaves de 0.3 segundos.
*   **👟 Variantes de Productos**: Soporte relacional completo para variantes de **Color** (con círculos de colores interactivos) y **Talla** (insignias reactivas) con control estricto del stock físico en tiempo real.
*   **🛒 Carrito de Compras en Sesión**: Funcionalidad AJAX (Fetch API) para añadir, actualizar cantidades y eliminar ítems de forma dinámica sin recargar la página.
*   **🏷️ Sistema de Cupones**: Aplicación dinámica de cupones de descuento (porcentaje o monto fijo) con recálculo de precios instantáneo.
*   **💳 Simulador de Pasarela de Pagos (Stripe / MercadoPago)**: Modal bancario integrado con una tarjeta de crédito virtual interactiva que se formatea y actualiza conforme el usuario escribe sus datos. Permite simular aprobaciones y rechazos.
*   **📄 Facturas en PDF**: Generación automática y al vuelo de facturas de compra profesionales utilizando la librería **ReportLab**, incluyendo desglose de impuestos (IVA 10% para Paraguay), cupones aplicados y datos de envío.
*   **🔌 API REST Completa**: Endpoints RESTful listos para usar (`django-rest-framework`) para catálogo de productos, validación de cupones, envío de reseñas y procesamiento de checkout con transacciones atómicas.
*   **🧪 Pruebas Unitarias**: Suite de pruebas automatizadas que verifican la consistencia de modelos, cupones y la lógica de cómputo del carrito.

---

## 🛠️ Tecnologías Utilizadas

*   **Backend**: Python, Django, Django REST Framework.
*   **Frontend**: HTML5 Semántico, Vanilla CSS (Variables, Flexbox, Grid), JavaScript ES6+.
*   **PDF**: ReportLab.
*   **Base de Datos**: SQLite3 (desarrollo local).

---

## 🚀 Guía de Instalación y Uso Local

### 1. Clonar el repositorio e ingresar al directorio
```bash
git clone <url-de-tu-repositorio>
cd <nombre-del-directorio>
```

### 2. Crear y activar el entorno virtual
En Windows (PowerShell):
```bash
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Instalar dependencias
```bash
pip install django djangorestframework reportlab pillow
```

### 4. Realizar migraciones de base de datos
```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Sembrar base de datos inicial (Seed)
Ejecuta el script de semilla para crear categorías, productos con variantes, cupones y el superusuario administrador:
```bash
python seed_db.py
```

### 6. Iniciar el Servidor de Desarrollo
```bash
python manage.py runserver
```

Abre tu navegador e ingresa a: **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)**

*   **Panel de Administración**: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)
    *   **Usuario**: `admin`
    *   **Contraseña**: `admin123`

---

## 🧪 Pruebas Unitarias
Para correr la suite de tests automatizados, ejecuta:
```bash
python manage.py test
```
