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

Buenas prácticas y recomendaciones
---------------------------------
- Añade y mantiene `requirements.txt` con `pip freeze`.
- No uses el servidor de desarrollo en producción.
- Hacer respaldo de la base de datos antes de operaciones destructivas.
- Proteger las credenciales: no subir contraseñas al repositorio.

Si quieres, puedo:
- Generar un `requirements.txt` con dependencias actuales.
- Cambiar o eliminar el usuario `admin` y crear otro con tus datos.
- Crear un `README.md` en formato Markdown en lugar de `README.txt`.

Contacto
--------
- Proyecto local: carpeta `agroclick/` en tu workspace.

---
Generado automáticamente — dime si quieres que lo transforme a `README.md` con formato Markdown y badge, o que incluya ejemplos de screenshots o pasos de despliegue en producción.
