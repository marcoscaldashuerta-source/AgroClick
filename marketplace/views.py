from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Q
from .forms import RegistroForm, ProductoForm
from .models import Perfil, Producto
from django.utils import timezone
from datetime import timedelta

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

    if request.user.is_authenticated:
        try:
            perfil = request.user.perfil
        except Perfil.DoesNotExist:
            perfil = None

        if perfil:
            is_vendedor = perfil.rol == 'vendedor'
            is_aprobado = perfil.aprobado

        if is_admin:
            pending_vendedores = Perfil.objects.filter(rol='vendedor', aprobado=False)

    # Determinar si hay filtros activos
    tiene_filtros = bool(busqueda or categoria or precio_min or precio_max)

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
        'is_vendedor': is_vendedor,
        'is_aprobado': is_aprobado,
        'is_admin': is_admin,
        'pending_vendedores': pending_vendedores,
        'categorias': categorias,
        'busqueda': busqueda,
        'categoria': categoria,
        'precio_min': precio_min,
        'precio_max': precio_max,
        'orden': orden,
        'tiene_filtros': tiene_filtros,
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
        else:
            producto.estado = 'activo'

        producto.save()

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
            return redirect('mis_productos')
        else:
            return redirect('mis_productos')

    # Si no es POST, mostrar página de confirmación
    return render(request, 'confirmar_eliminar_producto.html', {'producto': producto})