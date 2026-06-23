AgroClick - Marketplace Agrícola

Descripción
-----------
AgroClick es una aplicación Django sencilla para conectar productores (vendedores) y compradores.
Permite a vendedores publicar, editar, pausar y eliminar productos; y a compradores buscar y filtrar productos.

Funcionalidades principales
--------------------------
- Registro de usuarios (comprador / vendedor)
- Publicar producto con imagen, precio, stock y descripción
- Editar producto: precio, stock, descripción e imagen
- Pausar/reactivar publicación de producto
- Eliminar producto (con confirmación)
- Búsqueda para compradores por nombre/descripcion, categoría y rango de precio
- Panel de administración Django (/admin/)

Requisitos
----------
- Python 3.8+ (probado en 3.13 en el entorno local)
- Virtualenv o venv
- Dependencias básicas: Django, Pillow

Instalación y ejecución (Windows)
---------------------------------
1. Crear y activar entorno virtual (si no existe):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1    # Powershell
# o en cmd: .\.venv\Scripts\activate
```

2. Instalar dependencias (recomendado crear `requirements.txt`):

```powershell
pip install django pillow
pip freeze > requirements.txt
# en otro equipo: pip install -r requirements.txt
```

3. Aplicar migraciones y crear superusuario:

```powershell
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

4. Ejecutar servidor de desarrollo:

```powershell
python manage.py runserver
# Abrir: http://127.0.0.1:8000/  y  http://127.0.0.1:8000/admin/
```

Notas sobre credenciales
------------------------
- En este entorno se creó un superusuario temporal `admin` con email `admin@example.com`.
- Cambia la contraseña inmediatamente desde `/admin/` → `Users` o usando `python manage.py changepassword admin`.

Rutas relevantes
----------------
- Inicio / catálogo: `/`  (búsqueda y filtros incluidos)
- Publicar producto (vendedores): `/publicar/`
- Mis productos (vendedores): `/mis-productos/`
- Editar producto: `/editar-producto/<id>/`
- Pausar/reactivar producto: `/pausar-producto/<id>/`
- Eliminar producto (confirmación): `/eliminar-producto/<id>/`
- Admin: `/admin/`

Configuración de media (imágenes)
---------------------------------
- Las imágenes se guardan en `media/productos/`.
- Asegúrate en `settings.py` de tener configuradas las variables `MEDIA_URL` y `MEDIA_ROOT` y de servir `MEDIA` en desarrollo:

```python
# settings.py (ejemplo)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# urls.py del proyecto (solo en desarrollo)
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # ... tus rutas
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```


Cambios recientes (implementados)
--------------------------------
- Modelo de imágenes: se añadió el modelo `ProductImage` para permitir una galería normalizada de imágenes por producto (migración `0005_productimage` creada y aplicada).
- Subida múltiple: las plantillas `publicar_producto.html` y `editar_producto.html` usan ahora un único campo `<input name="images" multiple>` para subir varias imágenes a la vez.
- Límite de imágenes: el backend limita a 5 imágenes por producto. La lógica está en `marketplace/views.py` y hay validación cliente en JavaScript que avisa al usuario.
- Frontend y plantillas: se actualizaron `inicio.html`, `mis_productos.html`, `aprobar_vendedores.html`, `publicar_producto.html`, `editar_producto.html` para mostrar galería, miniaturas y mantener la estética del sitio.
- Autenticación/registro en español: `RegistroForm` ahora muestra mensajes de validación en español; además se añadió `CustomAuthenticationForm` para personalizar mensajes de login (incluye mensaje específico cuando un vendedor no está aprobado).
- Internacionalización: `LANGUAGE_CODE` en `settings.py` se cambió a `es` para usar traducciones nativas de Django cuando aplican.
- Aprobación de vendedores: la vista `aprobar_vendedores` permite a administradores marcar `Perfil.aprobado = True`; tras aprobar, el vendedor podrá acceder a las funciones de vendedor (publicar, mis productos).
- Navegación: la barra superior de la plantilla de aprobaciones evita enlaces redundantes y muestra el nombre del administrador autenticado.

Cómo probar los cambios localmente
---------------------------------
1. Asegúrate de haber instalado dependencias y activado el entorno virtual.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt  # o pip install django pillow
```

2. Crear/aplicar migraciones (necesario para `ProductImage`):

```powershell
python manage.py makemigrations marketplace
python manage.py migrate
```

3. Ejecutar servidor de desarrollo y abrir la app:

```powershell
python manage.py runserver
# Abrir: http://127.0.0.1:8000/
```

4. Flujo de prueba recomendado:
- Regístrate como vendedor desde `/registro/`.
- Inicia sesión; mientras `Perfil.aprobado` sea `False`, si intentas publicar verás un mensaje indicando que la cuenta está en revisión.
- Como administrador, entra en `/aprobar-vendedores/` (o usa el panel 'Aprobaciones' en la página principal) y aprueba al vendedor.
- El vendedor podrá entonces publicar y subir hasta 5 imágenes por producto usando el campo múltiple `images`.

Notas técnicas y ubicaciones clave
---------------------------------
- Modelo de galería: `marketplace/models.py` → `ProductImage`.
- Lógica de subida y límites: `marketplace/views.py` (métodos `publicar_producto`, `editar_producto`).
- Formulario de autenticación personalizado: `marketplace/forms.py` → `CustomAuthenticationForm`.
- Plantillas principales modificadas: `marketplace/templates/publicar_producto.html`, `editar_producto.html`, `inicio.html`, `mis_productos.html`, `aprobar_vendedores.html`.
- Estilos y scripts: `marketplace/static/marketplace/css/styles.css` y `marketplace/static/marketplace/js/app.js` (se añadieron validaciones JS simples en las plantillas para controlar el número de archivos seleccionados).

Contacto
--------
- Proyecto local: carpeta `agroclick/` en tu workspace.
