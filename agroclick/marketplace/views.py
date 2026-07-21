import re

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Q
from django.db.utils import OperationalError
from .forms import RegistroForm, ProductoForm, TicketSoporteForm, EntregaForm, DatosTransferenciaVendedorForm
from .models import Perfil, Producto, deshabilitar_cuenta_usuario, ProductActionLog, Notificacion, Carrito, ItemCarrito, TicketSoporte, SolicitudEntrega, Pedido, DatosTransferenciaVendedor
from .models import PaymentProof
from .forms import PaymentProofForm
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import user_passes_test
from django.utils.dateparse import parse_date

MAX_IMAGENES_POR_PRODUCTO = 5


@user_passes_test(lambda u: u.is_authenticated and u.is_staff)
def historial_registros(request):
    """Vista para que el administrador vea el historial de acciones del sistema.

    Filtros disponibles por: accion, usuario (admin que realizó la acción), fecha inicio y fecha fin.
    """
    qs = ProductActionLog.objects.select_related('producto', 'actor').all().order_by('-fecha')

    accion = request.GET.get('accion', '').strip()
    usuario = request.GET.get('usuario', '').strip()
    actor_rol = request.GET.get('actor_rol', '').strip()
    fecha_inicio = request.GET.get('fecha_inicio', '').strip()
    fecha_fin = request.GET.get('fecha_fin', '').strip()

    if accion:
        qs = qs.filter(accion__iexact=accion)

    if usuario:
        qs = qs.filter(actor__username__icontains=usuario)

    if actor_rol:
        if actor_rol == 'admin':
            qs = qs.filter(actor__is_staff=True)
        else:
            qs = qs.filter(actor__perfil__rol__iexact=actor_rol)

    if fecha_inicio:
        d = parse_date(fecha_inicio)
        if d:
            qs = qs.filter(fecha__date__gte=d)

    if fecha_fin:
        d = parse_date(fecha_fin)
        if d:
            qs = qs.filter(fecha__date__lte=d)

    # Opciones para los selects
    acciones_disponibles = ProductActionLog.objects.values_list('accion', flat=True).distinct()
    actors_disponibles = User.objects.filter(id__in=ProductActionLog.objects.values_list('actor', flat=True)).order_by('username')
    roles_disponibles = ['admin', 'vendedor', 'comprador']

    return render(request, 'historial_registros.html', {
        'registros': qs,
        'acciones_disponibles': acciones_disponibles,
        'actors_disponibles': actors_disponibles,
        'roles_disponibles': roles_disponibles,
        'f_actor_rol': actor_rol,
        'f_accion': accion,
        'f_usuario': usuario,
        'f_fecha_inicio': fecha_inicio,
        'f_fecha_fin': fecha_fin,
    })

def mis_pedidos(request):
    """Muestra los pedidos realizados por el comprador autenticado."""
    if not request.user.is_authenticated:
        return redirect('/accounts/login/')

    try:
        perfil = request.user.perfil
    except Perfil.DoesNotExist:
        return redirect('/')

    if perfil.rol != 'comprador':
        return redirect('/')

    pedidos = Pedido.objects.filter(comprador=request.user).select_related('vendedor', 'producto').order_by('-fecha_creacion')
    return render(request, 'mis_pedidos.html', {'pedidos': pedidos})


def mis_datos_vendedor(request):
    """Permite al vendedor configurar los datos bancarios para transferencias."""
    if not request.user.is_authenticated:
        return redirect('/accounts/login/')

    try:
        perfil = request.user.perfil
    except Perfil.DoesNotExist:
        return redirect('/')

    if perfil.rol != 'vendedor':
        return redirect('/')

    datos, _ = DatosTransferenciaVendedor.objects.get_or_create(vendedor=request.user)
    if request.method == 'POST':
        formulario = DatosTransferenciaVendedorForm(request.POST, instance=datos)
        if formulario.is_valid():
            formulario.save()
            messages.success(request, 'Tus datos para transferencia fueron guardados correctamente.')
            return redirect('mis_datos_vendedor')
    else:
        formulario = DatosTransferenciaVendedorForm(instance=datos)

    return render(request, 'mis_datos_vendedor.html', {
        'formulario': formulario,
        'datos_completos': datos.esta_completo,
    })


def inicio(request):
    # Obtener todos los productos activos y publicados como base
    productos = Producto.objects.filter(borrador=False, estado='activo').order_by('-fecha_creacion')
    
    # Obtener parámetros de búsqueda
    busqueda = request.GET.get('busqueda', '').strip()
    categoria = request.GET.get('categoria', '').strip()
    precio_min = request.GET.get('precio_min', '')
    precio_max = request.GET.get('precio_max', '')
    orden = request.GET.get('orden', '-fecha_creacion')
    
    # Aplicar filtro por búsqueda (nombre y descripción)
    if busqueda:
        productos = productos.filter(
            Q(nombre__icontains=busqueda) | 
            Q(descripcion__icontains=busqueda)
        )
    
    # Aplicar filtro por categoría
    if categoria:
        productos = productos.filter(categoria__iexact=categoria)
    
    # Aplicar filtro por precio mínimo
    if precio_min:
        try:
            precio_min_val = float(precio_min)
            productos = productos.filter(precio__gte=precio_min_val)
        except ValueError:
            pass
    
    # Aplicar filtro por precio máximo
    if precio_max:
        try:
            precio_max_val = float(precio_max)
            productos = productos.filter(precio__lte=precio_max_val)
        except ValueError:
            pass
    
    # Aplicar ordenamiento
    if orden == 'precio_asc':
        productos = productos.order_by('precio')
    elif orden == 'precio_desc':
        productos = productos.order_by('-precio')
    elif orden == 'nombre_asc':
        productos = productos.order_by('nombre')
    elif orden == 'nombre_desc':
        productos = productos.order_by('-nombre')
    else:  # por defecto, más recientes primero
        productos = productos.order_by('-fecha_creacion')
    
    # Obtener lista de categorías únicas para el filtro
    categorias = Producto.objects.filter(
        borrador=False, 
        estado='activo'
    ).values_list('categoria', flat=True).distinct().order_by('categoria')
    
    perfil = None
    is_vendedor = False
    is_aprobado = False
    is_admin = request.user.is_authenticated and request.user.is_staff
    pending_vendedores = []
    pedidos_vendedor = []

    is_comprador = False
    if request.user.is_authenticated:
        try:
            perfil = request.user.perfil
        except Perfil.DoesNotExist:
            perfil = None

        if perfil:
            is_vendedor = perfil.rol == 'vendedor'
            is_comprador = perfil.rol == 'comprador'
            is_aprobado = perfil.aprobado

            if is_vendedor and is_aprobado:
                pedidos_vendedor = Pedido.objects.filter(vendedor=request.user).select_related('comprador', 'producto').order_by('-fecha_creacion')[:10]

        if is_admin:
            pending_vendedores = Perfil.objects.filter(rol='vendedor', aprobado=False)

    # Determinar si hay filtros activos
    tiene_filtros = bool(busqueda or categoria or precio_min or precio_max)

    notificaciones_count = 0
    if request.user.is_authenticated:
        try:
            notificaciones_count = Notificacion.objects.filter(usuario=request.user, leida=False).count()
        except OperationalError:
            notificaciones_count = 0

    # Marcar productos nuevos (creados en los últimos 14 días)
    now = timezone.now()
    for p in productos:
        try:
            p.is_new = (now - p.fecha_creacion) <= timedelta(days=14)
        except Exception:
            p.is_new = False

    return render(request, 'inicio.html', {
        'productos': productos,
        'perfil': perfil,
        'is_comprador': is_comprador,
        'is_vendedor': is_vendedor,
        'is_aprobado': is_aprobado,
        'is_admin': is_admin,
        'pending_vendedores': pending_vendedores,
        'pedidos_vendedor': pedidos_vendedor,
        'categorias': categorias,
        'busqueda': busqueda,
        'categoria': categoria,
        'precio_min': precio_min,
        'precio_max': precio_max,
        'orden': orden,
        'tiene_filtros': tiene_filtros,
        'notificaciones_count': notificaciones_count,
    })

def registro(request):

    if request.method == 'POST':
        form = RegistroForm(request.POST)

        if form.is_valid():

            usuario = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password']
            )

            Perfil.objects.create(
                usuario=usuario,
                rol=form.cleaned_data['rol'],
                aprobado=False
            )

            return redirect('login')

    else:
        form = RegistroForm()

    return render(
        request,
        'registro.html',
        {'form': form}
    )

def publicar_producto(request):

    if not request.user.is_authenticated:
        return redirect('/accounts/login/')

    try:
        perfil = request.user.perfil
    except Perfil.DoesNotExist:
        return redirect('/')

    if perfil.rol != 'vendedor':
        return redirect('/')

    if not perfil.aprobado:
        return redirect('/')

    if request.method == 'POST':

        saving_draft = 'guardar_borrador' in request.POST
        form = ProductoForm(request.POST, request.FILES, saving_draft=saving_draft)

        if saving_draft:
            nombre = (request.POST.get('nombre') or '').strip()
            if not nombre:
                form.add_error('nombre', 'El nombre del producto es obligatorio para guardar un borrador.')
                return render(
                    request,
                    'publicar_producto.html',
                    {'form': form, 'remaining_slots': MAX_IMAGENES_POR_PRODUCTO}
                )

        if form.is_valid():

            producto = form.save(commit=False)
            producto.vendedor = request.user

            if saving_draft:
                producto.borrador = True
                messages.success(request, 'Producto guardado como borrador correctamente.')
            else:
                producto.borrador = False
                messages.success(request, 'Producto publicado correctamente.')

            producto.save()

            # Registrar publicación si no es borrador y no existe registro previo
            if not producto.borrador:
                exists = ProductActionLog.objects.filter(producto=producto, accion__iexact='publicado', actor=request.user).exists()
                if not exists:
                    ProductActionLog.objects.create(producto=producto, actor=request.user, accion='publicado')

            # Manejar múltiples imágenes subidas desde el campo 'images'
            imagenes_subidas = request.FILES.getlist('images')
            if imagenes_subidas:
                from .models import ProductImage
                imagenes_existentes = producto.imagenes.count() + (1 if producto.imagen else 0)
                espacios_disponibles = MAX_IMAGENES_POR_PRODUCTO - imagenes_existentes
                if espacios_disponibles > 0:
                    imagenes_agregadas = 0
                    indice_imagen_principal = request.POST.get('main_image_index')
                    try:
                        indice_imagen_principal = int(indice_imagen_principal)
                    except (TypeError, ValueError):
                        indice_imagen_principal = 0
                    indice_imagen_principal = max(0, min(indice_imagen_principal, len(imagenes_subidas) - 1))
                    for indice_imagen, archivo_imagen in enumerate(imagenes_subidas):
                        if imagenes_agregadas >= espacios_disponibles:
                            break
                        if indice_imagen == indice_imagen_principal:
                            producto.imagen = archivo_imagen
                            producto.save(update_fields=['imagen'])
                            imagenes_agregadas += 1
                            continue
                        if not producto.imagen and indice_imagen > indice_imagen_principal:
                            producto.imagen = archivo_imagen
                            producto.save(update_fields=['imagen'])
                            imagenes_agregadas += 1
                            continue
                        ProductImage.objects.create(producto=producto, imagen=archivo_imagen, orden=imagenes_agregadas)
                        imagenes_agregadas += 1

            return redirect('/')

    else:

        form = ProductoForm()

    return render(
        request,
        'publicar_producto.html',
        {'form': form, 'remaining_slots': MAX_IMAGENES_POR_PRODUCTO}
    )


def cerrar_sesion(request):
    logout(request)
    return redirect('login')


def aprobar_vendedores(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        return redirect('inicio')

    if request.method == 'POST':
        perfil_id = request.POST.get('perfil_id')
        perfil = get_object_or_404(Perfil, id=perfil_id, rol='vendedor')
        perfil.aprobado = True
        perfil.save()
        messages.success(request, f'El vendedor {perfil.usuario.username} ha sido aprobado correctamente.')
        next_url = request.POST.get('next')
        if next_url:
            return redirect(next_url)
        return redirect('inicio')

    messages.info(request, 'Puedes aprobar vendedores directamente desde la pantalla de inicio.')
    return redirect('inicio')


def supervisar_productos(request):
    """Vista para que el administrador supervise todos los productos."""
    if not request.user.is_authenticated or not request.user.is_staff:
        return redirect('/')

    productos = Producto.objects.all().order_by('-fecha_creacion')

    vendedor = request.GET.get('vendedor', '').strip()
    categoria = request.GET.get('categoria', '').strip()
    estado = request.GET.get('estado', '').strip()

    if vendedor:
        productos = productos.filter(vendedor__username__iexact=vendedor)

    if categoria:
        productos = productos.filter(categoria__iexact=categoria)

    if estado:
        productos = productos.filter(estado__iexact=estado)

    # Lista de vendedores y categorías para filtros
    vendedores = User.objects.filter(is_active=True).order_by('username')
    categorias = Producto.objects.values_list('categoria', flat=True).distinct().order_by('categoria')

    return render(request, 'supervisar_productos.html', {
        'productos': productos,
        'vendedores': vendedores,
        'categorias': categorias,
        'filtro_vendedor': vendedor,
        'filtro_categoria': categoria,
        'filtro_estado': estado,
    })


def eliminar_producto_admin(request, producto_id):
    """Marca un producto como eliminado desde la vista de administrador sin borrarlo físicamente."""
    if not request.user.is_authenticated or not request.user.is_staff:
        return redirect('/')

    producto = get_object_or_404(Producto, id=producto_id)
    vendedor = producto.vendedor

    if request.method == 'POST':
        razon = request.POST.get('razon', '').strip()
        nombre_producto = producto.nombre
        producto.soft_delete()

        # Crear notificación para el vendedor
        mensaje = f"Tu producto '{nombre_producto}' fue eliminado por un administrador. Motivo: {razon}"
        Notificacion.objects.create(usuario=vendedor, mensaje=mensaje)

        return redirect('supervisar_productos')

    return render(request, 'confirmar_eliminar_producto_admin.html', {'producto': producto})


def _normalizar_mensaje_notificacion(mensaje):
    if not mensaje:
        return mensaje

    return re.sub(
        r'(?i)\bpedido\s*#(\d+)\b',
        lambda match: f'Pedido N°{match.group(1)}',
        mensaje,
    )


def ver_notificaciones(request):
    if not request.user.is_authenticated:
        return redirect('/accounts/login/')

    notificaciones = list(Notificacion.objects.filter(usuario=request.user).order_by('-fecha'))

    for notificacion in notificaciones:
        mensaje_normalizado = _normalizar_mensaje_notificacion(notificacion.mensaje)
        notificacion.leida = True
        if mensaje_normalizado != notificacion.mensaje:
            notificacion.mensaje = mensaje_normalizado
        notificacion.save(update_fields=['mensaje', 'leida'])

    return render(request, 'notificaciones.html', {
        'notificaciones': notificaciones,
    })


def deshabilitar_usuarios_admin(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        return redirect('/')

    usuarios_por_rol = {
        'Vendedores': [],
        'Compradores': []
    }

    perfiles = Perfil.objects.select_related('usuario').all()
    for perfil in perfiles:
        if perfil.rol == 'vendedor' and perfil.aprobado:
            usuarios_por_rol['Vendedores'].append(perfil.usuario)
        elif perfil.rol == 'comprador':
            usuarios_por_rol['Compradores'].append(perfil.usuario)

    if request.method == 'POST':
        usuario_id = request.POST.get('usuario_id')
        usuario = get_object_or_404(User, id=usuario_id)
        perfil_usuario = get_object_or_404(Perfil, usuario=usuario)

        if perfil_usuario.rol == 'vendedor' and not perfil_usuario.aprobado:
            messages.info(request, "No puedes deshabilitar vendedores pendientes de aprobación.")
            return redirect('deshabilitar_usuarios_admin')

        usuario.is_active = not usuario.is_active
        usuario.save(update_fields=['is_active'])

        if usuario.is_active:
            messages.success(request, f"El usuario '{usuario.username}' ha sido habilitado.")
        else:
            messages.success(request, f"El usuario '{usuario.username}' ha sido deshabilitado.")

        return redirect('deshabilitar_usuarios_admin')

    return render(request, 'deshabilitar_usuarios.html', {
        'usuarios_por_rol': usuarios_por_rol,
        'hide_global_messages': True,
    })


def mis_productos(request):
    """Vista que muestra todos los productos del vendedor autenticado"""
    if not request.user.is_authenticated:
        return redirect('/accounts/login/')

    try:
        perfil = request.user.perfil
    except Perfil.DoesNotExist:
        return redirect('/')

    if perfil.rol != 'vendedor':
        return redirect('/')

    # Obtener todos los productos del vendedor excepto los eliminados
    productos = Producto.objects.filter(
        vendedor=request.user
    ).exclude(estado='eliminado').order_by('-fecha_creacion')

    return render(request, 'mis_productos.html', {'productos': productos})


def editar_producto(request, producto_id):
    """Vista que permite al vendedor editar sus productos"""
    if not request.user.is_authenticated:
        return redirect('/accounts/login/')

    try:
        perfil = request.user.perfil
    except Perfil.DoesNotExist:
        return redirect('/')

    if perfil.rol != 'vendedor':
        return redirect('/')

    # Obtener el producto y verificar que pertenece al vendedor
    producto = get_object_or_404(Producto, id=producto_id, vendedor=request.user)

    # No permitir editar productos eliminados
    if producto.estado == 'eliminado':
        return redirect('mis_productos')

    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES, instance=producto)

        if form.is_valid():
            producto = form.save(commit=False)
            producto.vendedor = request.user
            producto.save()

            from .models import ProductImage

            deleted_image_ids_raw = request.POST.get('deleted_image_ids', '')
            deleted_image_ids = []
            for raw_id in deleted_image_ids_raw.split(','):
                cleaned = str(raw_id).strip()
                if cleaned.isdigit():
                    deleted_image_ids.append(int(cleaned))

            removed_main_image = request.POST.get('removed_main_image', '0') == '1'

            for image_id in deleted_image_ids:
                ProductImage.objects.filter(producto=producto, id=image_id).delete()

            imagenes_actuales = []
            if producto.imagen:
                imagenes_actuales.append(('principal', producto.imagen, None))
            for imagen_galeria in producto.imagenes.order_by('orden', 'id').all():
                imagenes_actuales.append(('galeria', imagen_galeria.imagen, imagen_galeria))

            main_image_index = request.POST.get('main_image_index')
            try:
                indice_imagen_principal = int(main_image_index)
            except (TypeError, ValueError):
                indice_imagen_principal = 0

            if imagenes_actuales:
                if removed_main_image and producto.imagen:
                    siguiente_galeria = producto.imagenes.order_by('orden', 'id').first()
                    if siguiente_galeria is not None:
                        try:
                            producto.imagen = siguiente_galeria.imagen
                            producto.save(update_fields=['imagen'])
                            siguiente_galeria.delete()
                        except Exception:
                            pass
                    else:
                        try:
                            producto.imagen = None
                            producto.save(update_fields=['imagen'])
                        except Exception:
                            pass
                indice_normalizado = max(0, min(indice_imagen_principal, len(imagenes_actuales) - 1))
                seleccionado = imagenes_actuales[indice_normalizado]
                if seleccionado[0] == 'galeria':
                    instancia_galeria = seleccionado[2]
                    if instancia_galeria is not None:
                        try:
                            instancia_galeria.delete()
                        except Exception:
                            pass

                    imagen_actual_principal = producto.imagen
                    if imagen_actual_principal and imagen_actual_principal.name != seleccionado[1].name:
                        try:
                            ya_esta_en_galeria = producto.imagenes.filter(imagen__name=imagen_actual_principal.name).exists()
                        except Exception:
                            ya_esta_en_galeria = False
                        if not ya_esta_en_galeria:
                            try:
                                ProductImage.objects.create(
                                    producto=producto,
                                    imagen=imagen_actual_principal,
                                    orden=producto.imagenes.count(),
                                )
                            except Exception:
                                pass
                    try:
                        producto.imagen = seleccionado[1]
                        producto.save(update_fields=['imagen'])
                    except Exception:
                        pass

            # Manejar imágenes añadidas desde el campo 'images' al editar
            imagenes_subidas = request.FILES.getlist('images')
            if imagenes_subidas:
                imagenes_existentes = producto.imagenes.count() + (1 if producto.imagen else 0)
                espacios_disponibles = MAX_IMAGENES_POR_PRODUCTO - imagenes_existentes
                if espacios_disponibles > 0:
                    imagenes_agregadas = 0
                    indice_imagen_principal_nuevo = None
                    indice_total_previa = len(imagenes_actuales) + len(imagenes_subidas)
                    indice_imagen_principal = max(0, min(indice_imagen_principal, indice_total_previa - 1))
                    if indice_imagen_principal >= len(imagenes_actuales):
                        indice_imagen_principal_nuevo = indice_imagen_principal - len(imagenes_actuales)

                    imagen_actual_principal = producto.imagen
                    for indice_imagen, archivo_imagen in enumerate(imagenes_subidas):
                        if imagenes_agregadas >= espacios_disponibles:
                            break
                        if indice_imagen_principal_nuevo is not None and indice_imagen == indice_imagen_principal_nuevo:
                            if imagen_actual_principal and imagen_actual_principal.name != archivo_imagen.name:
                                ya_esta_en_galeria = producto.imagenes.filter(imagen__name=imagen_actual_principal.name).exists()
                                if not ya_esta_en_galeria:
                                    ProductImage.objects.create(
                                        producto=producto,
                                        imagen=imagen_actual_principal,
                                        orden=producto.imagenes.count(),
                                    )
                            producto.imagen = archivo_imagen
                            producto.save(update_fields=['imagen'])
                            imagenes_agregadas += 1
                            continue
                        if not producto.imagen and indice_imagen == 0 and indice_imagen_principal_nuevo is None:
                            producto.imagen = archivo_imagen
                            producto.save(update_fields=['imagen'])
                            imagenes_agregadas += 1
                            continue
                        ProductImage.objects.create(producto=producto, imagen=archivo_imagen, orden=imagenes_agregadas)
                        imagenes_agregadas += 1

            return redirect('mis_productos')

    else:
        form = ProductoForm(instance=producto)

    imagenes_existentes = producto.imagenes.count() + (1 if producto.imagen else 0)
    espacios_disponibles = max(0, MAX_IMAGENES_POR_PRODUCTO - imagenes_existentes)

    return render(request, 'editar_producto.html', {
        'form': form,
        'producto': producto,
        'remaining_slots': espacios_disponibles
    })


def pausar_producto(request, producto_id):
    """Vista que permite pausar/reactivar un producto"""
    if not request.user.is_authenticated:
        return redirect('/accounts/login/')

    try:
        perfil = request.user.perfil
    except Perfil.DoesNotExist:
        return redirect('/')

    if perfil.rol != 'vendedor':
        return redirect('/')

    producto = get_object_or_404(Producto, id=producto_id, vendedor=request.user)

    # No permitir pausar/reactivar productos eliminados
    if producto.estado == 'eliminado':
        return redirect('mis_productos')

    if request.method == 'POST':
        if producto.estado == 'activo':
            producto.estado = 'pausado'
            producto.save()
            ProductActionLog.objects.create(producto=producto, actor=request.user, accion='pausado')
        else:
            producto.estado = 'activo'
            producto.save()
            ProductActionLog.objects.create(producto=producto, actor=request.user, accion='activado')

    return redirect('mis_productos')


def eliminar_producto(request, producto_id):
    """Vista que permite eliminar un producto de forma permanente"""
    if not request.user.is_authenticated:
        return redirect('/accounts/login/')

    try:
        perfil = request.user.perfil
    except Perfil.DoesNotExist:
        return redirect('/')

    if perfil.rol != 'vendedor':
        return redirect('/')

    producto = get_object_or_404(Producto, id=producto_id, vendedor=request.user)

    if request.method == 'POST':
        confirmacion = request.POST.get('confirmar_eliminar')

        if confirmacion == 'si':
            producto.soft_delete()
            messages.success(request, 'El producto se eliminó correctamente.')
            return redirect('mis_productos')
        else:
            return redirect('mis_productos')

    return render(request, 'confirmar_eliminar_producto.html', {'producto': producto})


@require_POST
def eliminar_productos_seleccionados(request):
    """Elimina múltiples productos seleccionados por el vendedor autenticado."""
    if not request.user.is_authenticated:
        return redirect('/accounts/login/')

    try:
        perfil = request.user.perfil
    except Perfil.DoesNotExist:
        return redirect('/')

    if perfil.rol != 'vendedor':
        return redirect('/')

    confirmacion = request.POST.get('confirmar_eliminar')
    if confirmacion != 'si':
        return redirect('mis_productos')

    producto_ids_raw = request.POST.get('producto_ids', '')
    producto_ids = []
    for raw_value in producto_ids_raw.split(','):
        valor_limpio = str(raw_value).strip()
        if valor_limpio.isdigit():
            producto_ids.append(int(valor_limpio))

    if not producto_ids:
        return redirect('mis_productos')

    productos = list(Producto.objects.filter(id__in=producto_ids, vendedor=request.user).exclude(estado='eliminado'))
    if not productos:
        return redirect('mis_productos')

    for producto in productos:
        producto.soft_delete()

    messages.success(request, f'Se eliminaron {len(productos)} producto(s).')
    return redirect('mis_productos')


# ==================== CARRITO DE COMPRAS ====================

def agregar_al_carrito(request, producto_id):
    """Agrega un producto al carrito."""
    if not request.user.is_authenticated:
        return redirect('/accounts/login/')

    try:
        perfil = request.user.perfil
    except Perfil.DoesNotExist:
        return redirect('/')

    if perfil.rol != 'comprador':
        messages.error(request, 'Solo los compradores pueden agregar productos al carrito.')
        return redirect('inicio')

    producto = get_object_or_404(Producto, id=producto_id, borrador=False, estado='activo')

    # Obtener o crear el carrito del usuario
    carrito, created = Carrito.objects.get_or_create(comprador=request.user)

    # Obtener o crear el item en el carrito
    item, created = ItemCarrito.objects.get_or_create(carrito=carrito, producto=producto)

    if not created:
        # Si ya existía, aumentar la cantidad
        item.cantidad += 1
        item.save()

    return redirect('ver_carrito')


def ver_carrito(request):
    """Muestra el carrito de compras del usuario."""
    if not request.user.is_authenticated:
        return redirect('/accounts/login/')

    try:
        carrito = Carrito.objects.get(comprador=request.user)
    except Carrito.DoesNotExist:
        carrito = None

    total = 0
    if carrito:
        total = carrito.obtener_total()

    return render(request, 'cart.html', {
        'carrito': carrito,
        'total': total,
    })


@require_POST
def actualizar_cantidad_carrito(request, item_id):
    """Actualiza la cantidad de un item en el carrito."""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'No has iniciado sesión.'})

    try:
        carrito = Carrito.objects.get(comprador=request.user)
    except Carrito.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'No se encontró un carrito para este usuario.'})

    item = get_object_or_404(ItemCarrito, id=item_id, carrito=carrito)

    cantidad = request.POST.get('cantidad', 0)
    try:
        cantidad = int(cantidad)
    except ValueError:
        return JsonResponse({'success': False, 'error': 'La cantidad ingresada no es válida.'})

    if cantidad < 0:
        return JsonResponse({'success': False, 'error': 'La cantidad no puede ser negativa.'})

    if cantidad > item.producto.stock:
        return JsonResponse({'success': False, 'error': f'Stock insuficiente. Disponible: {item.producto.stock} unidades.'})

    if cantidad == 0:
        item.delete()
    else:
        item.cantidad = cantidad
        item.save()

    # Calcular nuevos totales
    carrito_total = carrito.obtener_total()
    item_subtotal = item.obtener_subtotal() if cantidad > 0 else 0

    return JsonResponse({
        'success': True,
        'carrito_total': carrito_total,
        'item_subtotal': item_subtotal,
        'items_count': carrito.obtener_cantidad_items()
    })


def eliminar_del_carrito(request, item_id):
    """Elimina un item del carrito."""
    if not request.user.is_authenticated:
        return redirect('/accounts/login/')

    try:
        carrito = Carrito.objects.get(comprador=request.user)
    except Carrito.DoesNotExist:
        return redirect('ver_carrito')

    item = get_object_or_404(ItemCarrito, id=item_id, carrito=carrito)
    item.delete()

    return redirect('ver_carrito')


def vaciar_carrito(request):
    """Vacía completamente el carrito."""
    if not request.user.is_authenticated:
        return redirect('/accounts/login/')

    try:
        carrito = Carrito.objects.get(comprador=request.user)
        carrito.items.all().delete()
    except Carrito.DoesNotExist:
        pass

    return redirect('ver_carrito')


# ==================== CHECKOUT ====================

def checkout(request):
    """Paso previo al pago: el comprador elige Delivery o retiro en tienda."""
    if not request.user.is_authenticated:
        return redirect('/accounts/login/')

    try:
        carrito_usuario = Carrito.objects.get(comprador=request.user)
    except Carrito.DoesNotExist:
        carrito_usuario = None

    if not carrito_usuario or not carrito_usuario.items.exists():
        return redirect('ver_carrito')

    items_del_carrito = list(
        carrito_usuario.items.select_related('producto__vendedor').all()
    )
    vendedores = {item.producto.vendedor for item in items_del_carrito}
    vendedores_sin_transferencia = []
    for vendedor in vendedores:
        try:
            datos = vendedor.datos_transferencia
        except DatosTransferenciaVendedor.DoesNotExist:
            datos = None
        if not datos or not datos.esta_completo:
            vendedores_sin_transferencia.append(vendedor)

    transferencia_disponible = not vendedores_sin_transferencia

    if request.method == 'POST':
        formulario = EntregaForm(request.POST)

        if formulario.is_valid():
            solicitud_entrega = formulario.save(commit=False)
            solicitud_entrega.comprador = request.user

            if solicitud_entrega.tipo_pago == 'transferencia' and not transferencia_disponible:
                formulario.add_error(
                    'tipo_pago',
                    'Transferencia no disponible: uno o más vendedores aún no configuran sus datos bancarios.',
                )
            else:
                if solicitud_entrega.tipo_entrega != 'delivery':
                    solicitud_entrega.direccion_entrega = None
                    solicitud_entrega.referencia = None

                solicitud_entrega.save()

                pedidos_creados = []
                items_por_vendedor = {}
                for item in items_del_carrito:
                    vendedor = item.producto.vendedor
                    items_por_vendedor.setdefault(vendedor, []).append(item)

                for vendedor, items in items_por_vendedor.items():
                    cantidad_total = sum(item.cantidad for item in items)
                    total_general = sum(item.producto.precio * item.cantidad for item in items)
                    primer_item = items[0]
                    productos_detalle = ', '.join(
                        f"{item.producto.nombre} (x{item.cantidad})" for item in items
                    )
                    pedido = Pedido.objects.create(
                        comprador=request.user,
                        vendedor=vendedor,
                        producto=primer_item.producto,
                        solicitud=solicitud_entrega,
                        productos_detalle=productos_detalle,
                        cantidad=cantidad_total,
                        precio_unitario=primer_item.producto.precio,
                        total=total_general,
                        tipo_entrega=solicitud_entrega.tipo_entrega,
                        direccion_entrega=solicitud_entrega.direccion_entrega,
                        referencia=solicitud_entrega.referencia,
                        tipo_pago=solicitud_entrega.tipo_pago,
                        estado='pendiente',
                    )
                    pedidos_creados.append(pedido)
                    for item in items:
                        ProductActionLog.objects.create(producto=item.producto, actor=request.user, accion='pedido_creado')

                carrito_usuario.items.all().delete()

                return render(request, 'checkout_success.html', {
                    'pedidos': pedidos_creados,
                    'pago_transferencia': solicitud_entrega.tipo_pago == 'transferencia',
                })
    else:
        formulario = EntregaForm()

    return render(request, 'checkout.html', {
        'formulario': formulario,
        'carrito_usuario': carrito_usuario,
        'total_carrito': carrito_usuario.obtener_total(),
        'transferencia_disponible': transferencia_disponible,
        'vendedores_sin_transferencia': vendedores_sin_transferencia,
    })


@require_http_methods(['POST'])
def actualizar_estado_pedido(request, pedido_id):
    """Permite al vendedor avanzar o cancelar un pedido desde su panel."""
    if not request.user.is_authenticated:
        return redirect('/accounts/login/')

    try:
        perfil = request.user.perfil
    except Perfil.DoesNotExist:
        return redirect('/')

    if perfil.rol != 'vendedor' or not perfil.aprobado:
        return redirect('/')

    pedido = get_object_or_404(Pedido, id=pedido_id, vendedor=request.user)
    accion = request.POST.get('accion', '').strip().lower()

    if accion == 'confirmar':
        if pedido.estado != 'pendiente':
            messages.error(request, 'Este pedido ya fue procesado.')
            return redirect('inicio')

        ultimo_comprobante = pedido.comprobantes.order_by('-fecha_subida').first()
        if pedido.tipo_pago == 'transferencia' and not ultimo_comprobante:
            messages.error(request, 'El comprador aún no ha subido el comprobante de transferencia.')
            return redirect('inicio')

        if pedido.producto.stock < pedido.cantidad:
            messages.error(request, 'No hay suficiente stock para confirmar este pedido.')
            return redirect('inicio')

        pedido.producto.stock -= pedido.cantidad
        pedido.producto.save(update_fields=['stock'])
        pedido.estado = 'preparando'
        pedido.motivo_cancelacion = ''
        if ultimo_comprobante:
            ultimo_comprobante.estado = 'aprobado'
            ultimo_comprobante.revisado_por = request.user
            ultimo_comprobante.fecha_revision = timezone.now()
            ultimo_comprobante.save(update_fields=['estado', 'revisado_por', 'fecha_revision'])
        ProductActionLog.objects.create(producto=pedido.producto, actor=request.user, accion='pedido_preparando', razon=f'Pedido N°{pedido.id}')
        Notificacion.objects.create(
            usuario=pedido.comprador,
            mensaje=f'Tu Pedido N°{pedido.id} fue aceptado y se está preparando.',
        )
        messages.success(request, f'Pedido N°{pedido.id} aceptado y en preparación.')
    elif accion == 'marcar_listo':
        if pedido.tipo_entrega != 'tienda':
            messages.error(request, 'Esta acción solo está disponible para pedidos con retiro en tienda.')
            return redirect('inicio')
        if pedido.estado != 'preparando':
            messages.error(request, 'El pedido debe estar en preparación antes de marcarlo como listo.')
            return redirect('inicio')

        pedido.estado = 'listo'
        ProductActionLog.objects.create(producto=pedido.producto, actor=request.user, accion='pedido_listo', razon=f'Pedido N°{pedido.id}')
        Notificacion.objects.create(
            usuario=pedido.comprador,
            mensaje=f'Tu Pedido N°{pedido.id} está listo para retiro.',
        )
        messages.success(request, f'Pedido N°{pedido.id} marcado como listo para retiro.')
    elif accion == 'cancelar':
        if pedido.estado != 'pendiente':
            messages.error(request, 'Solo se pueden cancelar pedidos pendientes.')
            return redirect('inicio')

        motivo_cancelacion = request.POST.get('motivo_cancelacion', '').strip()
        if motivo_cancelacion:
            mensaje = f"Tu pedido N°{pedido.id} fue cancelado por el vendedor. Motivo: {motivo_cancelacion}"
        else:
            mensaje = f"Tu pedido N°{pedido.id} fue cancelado por el vendedor."

        Notificacion.objects.create(usuario=pedido.comprador, mensaje=mensaje)
        pedido.estado = 'cancelado'
        pedido.motivo_cancelacion = motivo_cancelacion
        ProductActionLog.objects.create(producto=pedido.producto, actor=request.user, accion='pedido_cancelado', razon=f'Pedido N°{pedido.id} - {motivo_cancelacion}')
        messages.success(request, f'Pedido N°{pedido.id} cancelado.')
    else:
        messages.error(request, 'Acción inválida.')
        return redirect('inicio')

    pedido.save(update_fields=['estado', 'motivo_cancelacion'])
    return redirect('inicio')


@require_http_methods(['POST'])
def confirmar_retiro_pedido(request, pedido_id):
    """Permite al comprador confirmar que retiró un pedido listo en tienda."""
    if not request.user.is_authenticated:
        return redirect('/accounts/login/')

    try:
        perfil = request.user.perfil
    except Perfil.DoesNotExist:
        return redirect('/')

    if perfil.rol != 'comprador':
        return redirect('/')

    pedido = get_object_or_404(
        Pedido,
        id=pedido_id,
        comprador=request.user,
        tipo_entrega='tienda',
    )

    if pedido.estado != 'listo':
        messages.error(request, 'El pedido todavía no está listo para confirmar el retiro.')
        return redirect('mis_pedidos')

    pedido.estado = 'completado'
    pedido.save(update_fields=['estado'])
    ProductActionLog.objects.create(
        producto=pedido.producto,
        actor=request.user,
        accion='pedido_completado',
        razon=f'Pedido N°{pedido.id} retirado por el comprador',
    )
    Notificacion.objects.create(
        usuario=pedido.vendedor,
        mensaje=f'El comprador confirmó el retiro del Pedido N°{pedido.id}. El pedido fue completado.',
    )
    messages.success(request, f'Pedido N°{pedido.id} completado. Gracias por confirmar el retiro.')
    return redirect('mis_pedidos')


def subir_comprobante(request, pedido_id):
    """Permite al comprador subir el comprobante de pago para un pedido."""
    if not request.user.is_authenticated:
        return redirect('/accounts/login/')

    pedido = get_object_or_404(Pedido, id=pedido_id, comprador=request.user)

    if pedido.tipo_pago != 'transferencia':
        messages.error(request, 'Este pedido no requiere comprobante de transferencia.')
        return redirect('mis_pedidos')
    if pedido.estado != 'pendiente':
        messages.error(request, 'Este pedido ya fue procesado y no admite nuevos comprobantes.')
        return redirect('mis_pedidos')

    if request.method == 'POST':
        form = PaymentProofForm(request.POST, request.FILES)
        if form.is_valid():
            comprobante = form.save(commit=False)
            comprobante.pedido = pedido
            comprobante.subido_por = request.user
            comprobante.estado = 'pendiente'
            comprobante.save()

            # Registrar acción en log y notificar al vendedor
            ProductActionLog.objects.create(producto=pedido.producto, actor=request.user, accion='comprobante_subido', razon=f'Pedido N°{pedido.id}')
            mensaje = f"Se ha subido un comprobante de pago para el pedido N°{pedido.id}. Revisa y valida el comprobante."
            Notificacion.objects.create(usuario=pedido.vendedor, mensaje=mensaje)

            messages.success(request, 'Comprobante subido correctamente. El vendedor será notificado.')
            return redirect('mis_pedidos')
    else:
        form = PaymentProofForm()

    return render(request, 'subir_comprobante.html', {'form': form, 'pedido': pedido})


def ver_comprobantes_vendedor(request):
    """Lista comprobantes pendientes para el vendedor autenticado."""
    if not request.user.is_authenticated:
        return redirect('/accounts/login/')

    try:
        perfil = request.user.perfil
    except Perfil.DoesNotExist:
        return redirect('/')

    if perfil.rol != 'vendedor' or not perfil.aprobado:
        return redirect('/')

    comprobantes = PaymentProof.objects.filter(pedido__vendedor=request.user).select_related('pedido', 'subido_por').order_by('-fecha_subida')

    return render(request, 'ver_comprobantes_vendedor.html', {'comprobantes': comprobantes})


@require_http_methods(['POST'])
def revisar_comprobante(request, proof_id):
    """Permite al vendedor aprobar o rechazar un comprobante."""
    if not request.user.is_authenticated:
        return redirect('/accounts/login/')

    try:
        perfil = request.user.perfil
    except Perfil.DoesNotExist:
        return redirect('/')

    if perfil.rol != 'vendedor' or not perfil.aprobado:
        return redirect('/')

    comprobante = get_object_or_404(PaymentProof, id=proof_id, pedido__vendedor=request.user)
    accion = request.POST.get('accion', '').strip().lower()

    if accion == 'aprobar':
        pedido = comprobante.pedido
        if pedido.estado == 'pendiente' and pedido.producto.stock < pedido.cantidad:
            messages.error(request, 'No hay suficiente stock para aprobar y preparar este pedido.')
            return redirect('ver_comprobantes_vendedor')

        comprobante.estado = 'aprobado'
        comprobante.revisado_por = request.user
        comprobante.fecha_revision = timezone.now()
        comprobante.save()

        if pedido.estado == 'pendiente':
            pedido.producto.stock -= pedido.cantidad
            pedido.producto.save(update_fields=['stock'])
            pedido.estado = 'preparando'
            pedido.save(update_fields=['estado'])

        ProductActionLog.objects.create(producto=pedido.producto, actor=request.user, accion='pago_aprobado', razon=f'Pedido N°{pedido.id}')

        Notificacion.objects.create(usuario=pedido.comprador, mensaje=f"Tu pago para el Pedido N°{pedido.id} fue aprobado y el pedido se está preparando.")

        messages.success(request, f'Comprobante #{comprobante.id} aprobado y comprador notificado.')

    elif accion == 'rechazar':
        motivo = request.POST.get('motivo', '').strip()
        comprobante.estado = 'rechazado'
        comprobante.revisado_por = request.user
        comprobante.fecha_revision = timezone.now()
        comprobante.save()

        # Notificar al comprador con instrucciones
        texto = f"Tu comprobante para el pedido N°{comprobante.pedido.id} fue rechazado."
        if motivo:
            texto += f" Motivo: {motivo}"
        texto += " Por favor sube nuevamente un comprobante correcto."

        Notificacion.objects.create(usuario=comprobante.pedido.comprador, mensaje=texto)
        messages.success(request, f'Comprobante #{comprobante.id} rechazado y comprador notificado.')

    else:
        messages.error(request, 'Acción inválida.')

    return redirect('ver_comprobantes_vendedor')


# ==================== SOPORTE ====================

def enviar_soporte(request):
    """Formulario de soporte para compradores y vendedores desde su perfil."""
    if not request.user.is_authenticated:
        return redirect('/accounts/login/')

    if request.method == 'POST':
        form = TicketSoporteForm(request.POST)

        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.usuario = request.user
            ticket.save()
            messages.success(request, 'Tu solicitud de soporte fue enviada correctamente. Te responderemos pronto.')
            return redirect('enviar_soporte')
    else:
        form = TicketSoporteForm()

    mis_tickets = TicketSoporte.objects.filter(usuario=request.user)

    return render(request, 'soporte.html', {
        'form': form,
        'mis_tickets': mis_tickets,
    })


def panel_soporte(request):
    """Panel de administración: lista y gestiona todas las solicitudes de soporte."""
    if not request.user.is_authenticated or not request.user.is_staff:
        return redirect('/')

    tickets = TicketSoporte.objects.select_related('usuario').all()

    estado = request.GET.get('estado', '').strip()
    razon = request.GET.get('razon', '').strip()
    usuario = request.GET.get('usuario', '').strip()

    if estado:
        tickets = tickets.filter(estado=estado)

    if razon:
        tickets = tickets.filter(razon=razon)

    if usuario:
        tickets = tickets.filter(usuario__username__icontains=usuario)

    total_pendientes = TicketSoporte.objects.filter(estado='pendiente').count()

    return render(request, 'panel_soporte.html', {
        'tickets': tickets,
        'filtro_estado': estado,
        'filtro_razon': razon,
        'filtro_usuario': usuario,
        'total_pendientes': total_pendientes,
        'razon_choices': TicketSoporte.RAZON_CHOICES,
        'estado_choices': TicketSoporte.ESTADO_CHOICES,
    })


def responder_ticket(request, ticket_id):
    """Permite al administrador responder y actualizar el estado de un ticket."""
    if not request.user.is_authenticated or not request.user.is_staff:
        return redirect('/')

    ticket = get_object_or_404(TicketSoporte, id=ticket_id)

    if request.method == 'POST':
        respuesta = request.POST.get('respuesta_admin', '').strip()
        nuevo_estado = request.POST.get('estado', ticket.estado)

        ticket.respuesta_admin = respuesta
        ticket.estado = nuevo_estado
        ticket.atendido_por = request.user
        ticket.save()

        # Notificar al usuario que su ticket fue actualizado
        mensaje = f"Tu solicitud de soporte #{ticket.id} fue actualizada a '{ticket.get_estado_display()}'."
        if respuesta:
            mensaje += f" Respuesta: {respuesta}"
        Notificacion.objects.create(usuario=ticket.usuario, mensaje=mensaje)

        messages.success(request, f'Ticket #{ticket.id} actualizado y usuario notificado.')
        return redirect('panel_soporte')

    return render(request, 'responder_ticket.html', {'ticket': ticket})
