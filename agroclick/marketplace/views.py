from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Q
from django.db.utils import OperationalError
from .forms import RegistroForm, ProductoForm, TicketSoporteForm, EntregaForm
from .models import Perfil, Producto, deshabilitar_cuenta_usuario, ProductActionLog, Notificacion, Carrito, ItemCarrito, TicketSoporte, SolicitudEntrega, Pedido
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import user_passes_test
from django.utils.dateparse import parse_date


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

    MAX_IMAGES = 5

    if request.method == 'POST':

        form = ProductoForm(request.POST, request.FILES)

        if form.is_valid():

            producto = form.save(commit=False)
            producto.vendedor = request.user

            if 'guardar_borrador' in request.POST:
                producto.borrador = True
            else:
                producto.borrador = False

            producto.save()

            # Registrar publicación si no es borrador y no existe registro previo
            if not producto.borrador:
                exists = ProductActionLog.objects.filter(producto=producto, accion__iexact='publicado', actor=request.user).exists()
                if not exists:
                    ProductActionLog.objects.create(producto=producto, actor=request.user, accion='publicado')

            # Handle multiple uploaded images from single input 'images'
            images = request.FILES.getlist('images')
            if images:
                from .models import ProductImage
                existing = producto.imagenes.count() + (1 if producto.imagen else 0)
                remaining = MAX_IMAGES - existing
                if remaining <= 0:
                    messages.warning(request, f'Se alcanzó el límite de {MAX_IMAGES} imágenes por producto. No se añadieron imágenes adicionales.')
                else:
                    added = 0
                    for f in images:
                        if added >= remaining:
                            break
                        # set first available as main image if none
                        if not producto.imagen:
                            producto.imagen = f
                            producto.save()
                            added += 1
                            continue
                        ProductImage.objects.create(producto=producto, imagen=f, orden=added)
                        added += 1
                    if added < len(images):
                        messages.warning(request, f'Se subieron {added} imágenes; el resto fueron ignoradas para cumplir el límite de {MAX_IMAGES}.')
                    else:
                        messages.success(request, f'Se subieron {added} imágenes correctamente.')

            return redirect('/')

    else:

        form = ProductoForm()

    return render(
        request,
        'publicar_producto.html',
        {'form': form, 'remaining_slots': MAX_IMAGES}
    )


def cerrar_sesion(request):
    logout(request)
    return redirect('login')


def aprobar_vendedores(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        return redirect('/')

    perfil = None
    is_vendedor = False
    is_aprobado = False
    try:
        perfil = request.user.perfil
    except Perfil.DoesNotExist:
        perfil = None

    if perfil:
        is_vendedor = perfil.rol == 'vendedor'
        is_aprobado = perfil.aprobado

    if request.method == 'POST':
        perfil_id = request.POST.get('perfil_id')
        perfil = get_object_or_404(Perfil, id=perfil_id, rol='vendedor')
        perfil.aprobado = True
        perfil.save()
        return redirect('aprobar_vendedores')

    pending_vendedores = Perfil.objects.filter(rol='vendedor', aprobado=False)
    return render(request, 'aprobar_vendedores.html', {
        'pending_vendedores': pending_vendedores,
        'is_vendedor': is_vendedor,
        'is_aprobado': is_aprobado,
    })


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
    """Elimina (marca como eliminado) un producto desde la vista de administrador y registra la acción."""
    if not request.user.is_authenticated or not request.user.is_staff:
        return redirect('/')

    producto = get_object_or_404(Producto, id=producto_id)

    if request.method == 'POST':
        razon = request.POST.get('razon', '').strip()
        # Marcar producto como eliminado
        producto.estado = 'eliminado'
        producto.save()

        # Registrar la acción
        ProductActionLog.objects.create(
            producto=producto,
            actor=request.user,
            accion='eliminado',
            razon=razon
        )

        # Crear notificación para el vendedor
        mensaje = f"Tu producto '{producto.nombre}' fue eliminado por un administrador. Motivo: {razon}"
        Notificacion.objects.create(usuario=producto.vendedor, mensaje=mensaje)

        messages.success(request, 'Producto eliminado y vendedor notificado.')
        return redirect('supervisar_productos')

    return render(request, 'confirmar_eliminar_producto_admin.html', {'producto': producto})


def ver_notificaciones(request):
    if not request.user.is_authenticated:
        return redirect('/accounts/login/')

    notificaciones = Notificacion.objects.filter(usuario=request.user).order_by('-fecha')
    # Marcar como leídas todas las notificaciones vistas
    notificaciones.update(leida=True)

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
        if perfil.rol == 'vendedor':
            usuarios_por_rol['Vendedores'].append(perfil.usuario)
        elif perfil.rol == 'comprador':
            usuarios_por_rol['Compradores'].append(perfil.usuario)

    if request.method == 'POST':
        usuario_id = request.POST.get('usuario_id')
        usuario = get_object_or_404(User, id=usuario_id)
        get_object_or_404(Perfil, usuario=usuario)
        usuario.is_active = not usuario.is_active
        usuario.save(update_fields=['is_active'])

        if usuario.is_active:
            messages.success(request, f"El usuario '{usuario.username}' ha sido habilitado.")
        else:
            messages.success(request, f"El usuario '{usuario.username}' ha sido deshabilitado.")

        return redirect('deshabilitar_usuarios_admin')

    return render(request, 'deshabilitar_usuarios.html', {
        'usuarios_por_rol': usuarios_por_rol,
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

    MAX_IMAGES = 5

    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES, instance=producto)

        if form.is_valid():
            producto = form.save(commit=False)
            producto.vendedor = request.user
            producto.save()

            # Handle added images from single multiple input 'images' on edit
            images = request.FILES.getlist('images')
            if images:
                from .models import ProductImage
                existing = producto.imagenes.count() + (1 if producto.imagen else 0)
                remaining = MAX_IMAGES - existing
                if remaining <= 0:
                    messages.warning(request, f'Se alcanzó el límite de {MAX_IMAGES} imágenes por producto. No se añadieron imágenes adicionales.')
                else:
                    added = 0
                    for f in images:
                        if added >= remaining:
                            break
                        if not producto.imagen:
                            producto.imagen = f
                            producto.save()
                            added += 1
                            continue
                        ProductImage.objects.create(producto=producto, imagen=f, orden=added)
                        added += 1
                    if added < len(images):
                        messages.warning(request, f'Se subieron {added} imágenes; el resto fueron ignoradas para cumplir el límite de {MAX_IMAGES}.')
                    else:
                        messages.success(request, f'Se subieron {added} imágenes correctamente.')

            return redirect('mis_productos')

    else:
        form = ProductoForm(instance=producto)

    existing = producto.imagenes.count() + (1 if producto.imagen else 0)
    remaining_slots = max(0, MAX_IMAGES - existing)

    return render(request, 'editar_producto.html', {
        'form': form,
        'producto': producto,
        'remaining_slots': remaining_slots
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
        # Confirmar la acción
        confirmacion = request.POST.get('confirmar_eliminar')

        if confirmacion == 'si':
            producto.estado = 'eliminado'
            producto.save()
            ProductActionLog.objects.create(producto=producto, actor=request.user, accion='eliminado')
            return redirect('mis_productos')
        else:
            return redirect('mis_productos')

    # Si no es POST, mostrar página de confirmación
    return render(request, 'confirmar_eliminar_producto.html', {'producto': producto})


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
        return JsonResponse({'success': False, 'error': 'No autenticado'})

    try:
        carrito = Carrito.objects.get(comprador=request.user)
    except Carrito.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Carrito no encontrado'})

    item = get_object_or_404(ItemCarrito, id=item_id, carrito=carrito)

    cantidad = request.POST.get('cantidad', 0)
    try:
        cantidad = int(cantidad)
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Cantidad inválida'})

    if cantidad < 0:
        return JsonResponse({'success': False, 'error': 'La cantidad no puede ser negativa'})

    if cantidad > item.producto.stock:
        return JsonResponse({'success': False, 'error': f'Stock insuficiente. Disponible: {item.producto.stock}'})

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
    producto_nombre = item.producto.nombre
    item.delete()

    messages.success(request, f'"{producto_nombre}" eliminado del carrito.')
    return redirect('ver_carrito')


def vaciar_carrito(request):
    """Vacía completamente el carrito."""
    if not request.user.is_authenticated:
        return redirect('/accounts/login/')

    try:
        carrito = Carrito.objects.get(comprador=request.user)
        carrito.items.all().delete()
        messages.success(request, 'Carrito vaciado.')
    except Carrito.DoesNotExist:
        pass

    return redirect('ver_carrito')


# ==================== CHECKOUT ====================

def checkout(request):
    """Paso previo al pago: el comprador elige Delivery o retiro en tienda."""
    if not request.user.is_authenticated:
        return redirect('/accounts/login/')

    try:
        carrito = Carrito.objects.get(comprador=request.user)
    except Carrito.DoesNotExist:
        carrito = None

    if not carrito or not carrito.items.exists():
        messages.error(request, 'Tu carrito está vacío.')
        return redirect('ver_carrito')

    if request.method == 'POST':
        form = EntregaForm(request.POST)

        if form.is_valid():
            solicitud = form.save(commit=False)
            solicitud.comprador = request.user

            if solicitud.tipo_entrega != 'delivery':
                solicitud.direccion_entrega = None
                solicitud.referencia = None

            solicitud.save()

            for item in carrito.items.select_related('producto').all():
                producto = item.producto
                Pedido.objects.create(
                    comprador=request.user,
                    vendedor=producto.vendedor,
                    producto=producto,
                    solicitud=solicitud,
                    cantidad=item.cantidad,
                    precio_unitario=producto.precio,
                    total=producto.precio * item.cantidad,
                    tipo_entrega=solicitud.tipo_entrega,
                    direccion_entrega=solicitud.direccion_entrega,
                    referencia=solicitud.referencia,
                    tipo_pago=solicitud.tipo_pago,
                    estado='pendiente',
                )
                # Registrar creación de pedido por el comprador
                ProductActionLog.objects.create(producto=producto, actor=request.user, accion='pedido_creado')

            carrito.items.all().delete()
            messages.success(request, 'Compra confirmada correctamente.')
            return redirect('checkout')
    else:
        form = EntregaForm()

    return render(request, 'checkout.html', {
        'form': form,
        'carrito': carrito,
        'total': carrito.obtener_total(),
    })


@require_http_methods(['POST'])
def actualizar_estado_pedido(request, pedido_id):
    """Permite al vendedor confirmar o cancelar un pedido desde su panel."""
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
        if pedido.producto.stock < pedido.cantidad:
            messages.error(request, 'No hay suficiente stock para confirmar este pedido.')
            return redirect('inicio')

        pedido.producto.stock -= pedido.cantidad
        pedido.producto.save(update_fields=['stock'])
        pedido.estado = 'confirmado'
        pedido.motivo_cancelacion = ''
        ProductActionLog.objects.create(producto=pedido.producto, actor=request.user, accion='pedido_confirmado', razon=f'Pedido #{pedido.id}')
        messages.success(request, f'Pedido #{pedido.id} confirmado.')
    elif accion == 'cancelar':
        motivo_cancelacion = request.POST.get('motivo_cancelacion', '').strip()
        if motivo_cancelacion:
            mensaje = f"Tu pedido #{pedido.id} fue cancelado por el vendedor. Motivo: {motivo_cancelacion}"
        else:
            mensaje = f"Tu pedido #{pedido.id} fue cancelado por el vendedor."

        Notificacion.objects.create(usuario=pedido.comprador, mensaje=mensaje)
        pedido.estado = 'cancelado'
        pedido.motivo_cancelacion = motivo_cancelacion
        ProductActionLog.objects.create(producto=pedido.producto, actor=request.user, accion='pedido_cancelado', razon=f'Pedido #{pedido.id} - {motivo_cancelacion}')
        messages.success(request, f'Pedido #{pedido.id} cancelado.')
    else:
        messages.error(request, 'Acción inválida.')
        return redirect('inicio')

    pedido.save(update_fields=['estado', 'motivo_cancelacion'])
    return redirect('inicio')


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