from django.db import models
from django.contrib.auth.models import User


def deshabilitar_cuenta_usuario(usuario):
    usuario.is_active = False
    usuario.save(update_fields=['is_active'])
    return usuario


def habilitar_cuenta_usuario(usuario):
    usuario.is_active = True
    usuario.save(update_fields=['is_active'])
    return usuario


class Perfil(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)

    ROL_CHOICES = [
        ('comprador', 'Comprador'),
        ('vendedor', 'Vendedor'),
    ]

    rol = models.CharField(max_length=20, choices=ROL_CHOICES)
    aprobado = models.BooleanField(default=False)

    def __str__(self):
        return self.usuario.username
class Producto(models.Model):

    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('pausado', 'Pausado'),
        ('eliminado', 'Eliminado'),
    ]

    vendedor = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    nombre = models.CharField(max_length=100)

    categoria = models.CharField(max_length=100)

    descripcion = models.TextField()

    precio = models.IntegerField()

    unidad_venta = models.CharField(max_length=50)

    stock = models.IntegerField()

    imagen = models.ImageField(upload_to='productos/', blank=True, null=True)
    imagen2 = models.ImageField(upload_to='productos/', blank=True, null=True)
    imagen3 = models.ImageField(upload_to='productos/', blank=True, null=True)
    imagen4 = models.ImageField(upload_to='productos/', blank=True, null=True)
    imagen5 = models.ImageField(upload_to='productos/', blank=True, null=True)

    borrador = models.BooleanField(default=True)

    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='activo'
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre


class ProductImage(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='imagenes')
    imagen = models.ImageField(upload_to='productos/')
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['orden', 'id']

    def __str__(self):
        return f"Imagen de {self.producto.nombre} ({self.id})"


class ProductActionLog(models.Model):
    """Registro de acciones administrativas sobre productos."""
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    admin = models.ForeignKey(User, on_delete=models.CASCADE)
    accion = models.CharField(max_length=50)
    razon = models.TextField(blank=True, null=True)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.accion} - {self.producto.nombre} por {self.admin.username}"


class Notificacion(models.Model):
    """Notificaciones enviadas a usuarios (vendedores)."""
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificaciones')
    mensaje = models.TextField()
    leida = models.BooleanField(default=False)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notificación a {self.usuario.username} - {self.fecha.isoformat()}"


class Carrito(models.Model):
    """Carrito de compras del comprador."""
    comprador = models.OneToOneField(User, on_delete=models.CASCADE, related_name='carrito')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Carrito de {self.comprador.username}"

    def obtener_total(self):
        """Calcula el total del carrito."""
        return sum(item.obtener_subtotal() for item in self.items.all())

    def obtener_cantidad_items(self):
        """Retorna la cantidad de items en el carrito."""
        return sum(item.cantidad for item in self.items.all())


class TicketSoporte(models.Model):
    """Solicitud de soporte enviada por un comprador o vendedor desde su perfil."""

    RAZON_CHOICES = [
        ('problema_tecnico', 'Problema técnico'),
        ('pedido_producto', 'Consulta sobre pedido o producto'),
        ('cuenta_perfil', 'Problema con mi cuenta o perfil'),
        ('reclamo', 'Reclamo'),
        ('otro', 'Otro'),
    ]

    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('en_proceso', 'En proceso'),
        ('resuelto', 'Resuelto'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tickets_soporte')
    razon = models.CharField(max_length=30, choices=RAZON_CHOICES)
    descripcion = models.TextField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    respuesta_admin = models.TextField(blank=True, null=True)
    atendido_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets_atendidos'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"Ticket #{self.id} - {self.usuario.username} ({self.get_razon_display()})"


class SolicitudEntrega(models.Model):
    """Guarda la preferencia de entrega elegida por el comprador al iniciar el pago."""

    TIPO_ENTREGA_CHOICES = [
        ('delivery', 'Delivery'),
        ('tienda', 'Entrega en la tienda'),
    ]

    comprador = models.ForeignKey(User, on_delete=models.CASCADE, related_name='solicitudes_entrega')
    tipo_entrega = models.CharField(max_length=20, choices=TIPO_ENTREGA_CHOICES)
    direccion_entrega = models.CharField(max_length=255, blank=True, null=True)
    referencia = models.CharField(max_length=255, blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"Entrega de {self.comprador.username} - {self.get_tipo_entrega_display()}"


class ItemCarrito(models.Model):
    """Items individuales en el carrito."""
    carrito = models.ForeignKey(Carrito, on_delete=models.CASCADE, related_name='items')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)
    fecha_agregado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.cantidad}x {self.producto.nombre} en carrito de {self.carrito.comprador.username}"

    def obtener_subtotal(self):
        """Calcula el subtotal de este item."""
        return self.producto.precio * self.cantidad

    class Meta:
        unique_together = ('carrito', 'producto')