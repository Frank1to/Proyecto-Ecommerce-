// Funciones de utilidad comunes para la Tienda E-commerce

// 1. Mostrar notificaciones Toast animadas en pantalla
function showToast(message, type = 'success') {
    // Buscar o crear el contenedor de toasts
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    
    // Crear la notificación
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    // Icono correspondiente
    let icon = '💡';
    if (type === 'success') icon = '✅';
    else if (type === 'error') icon = '❌';
    else if (type === 'warning') icon = '⚠️';
    
    toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
    container.appendChild(toast);
    
    // Auto-eliminar después de 4 segundos con desvanecimiento
    setTimeout(() => {
        toast.style.transition = 'opacity 0.5s ease-out, transform 0.5s ease-out';
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        setTimeout(() => {
            toast.remove();
        }, 500);
    }, 4000);
}

// 2. Helper para obtener el token CSRF de las cookies en Django
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// 3. Añadir producto al carrito mediante petición AJAX Fetch
async function addToCart(variantId, quantity = 1) {
    if (!variantId) {
        showToast('Por favor, selecciona una combinación de color y talla.', 'warning');
        return false;
    }
    
    const csrfToken = getCookie('csrftoken');
    const formData = new FormData();
    formData.append('variant_id', variantId);
    formData.append('quantity', quantity);
    
    try {
        const response = await fetch('/cart/add/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken
            },
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast(data.message, 'success');
            // Actualizar la insignia numérica del carrito en el navbar
            const badge = document.getElementById('cart-badge-count');
            if (badge) {
                badge.innerText = data.cart_length;
                badge.style.display = data.cart_length > 0 ? 'flex' : 'none';
            }
            return true;
        } else {
            showToast(data.message || 'Error al agregar al carrito.', 'error');
            return false;
        }
    } catch (error) {
        console.error('Error:', error);
        showToast('Ocurrió un error de red al agregar al carrito.', 'error');
        return false;
    }
}
