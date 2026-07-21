import os

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_delete
from django.dispatch import receiver


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
        ('delivery', 'Delivery'),
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

    def soft_delete(self):
        """Marca el producto como eliminado sin borrar su registro ni sus datos asociados."""
        if self.estado != 'eliminado':
            self.estado = 'eliminado'
            self.save(update_fields=['estado'])
        return self


class ProductImage(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='imagenes')
    imagen = models.ImageField(upload_to='productos/')
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['orden', 'id']

    def __str__(self):
        return f"Imagen de {self.producto.nombre} ({self.id})"


def _eliminar_archivo_si_existe(instancia, nombre_campo):
    campo = getattr(instancia, nombre_campo, None)
    if not campo:
        return
    try:
        nombre_archivo = campo.name
    except Exception:
        nombre_archivo = None
    if not nombre_archivo:
        return
    try:
        if campo.storage.exists(nombre_archivo):
            campo.storage.delete(nombre_archivo)
    except Exception:
        pass


@receiver(post_delete, sender=Producto)
def eliminar_archivos_producto(sender, instance, **kwargs):
    for nombre_campo in ['imagen', 'imagen2', 'imagen3', 'imagen4', 'imagen5']:
        _eliminar_archivo_si_existe(instance, nombre_campo)


@receiver(post_delete, sender=ProductImage)
def eliminar_archivos_productimage(sender, instance, **kwargs):
    _eliminar_archivo_si_existe(instance, 'imagen')


class ProductActionLog(models.Model):
    """Registro de acciones administrativas sobre productos."""
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    actor = models.ForeignKey(User, on_delete=models.CASCADE)
    accion = models.CharField(max_length=50)
    razon = models.TextField(blank=True, null=True)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.accion} - {self.producto.nombre} por {self.actor.username}"

    @property
    def actor_role(self):
        """Devuelve el rol legible del actor que realizó la acción."""
        try:
            if self.actor.is_staff:
                return 'administrador'
        except Exception:
            pass
        try:
            perfil = getattr(self.actor, 'perfil', None)
            if perfil and getattr(perfil, 'rol', None):
                return perfil.rol
        except Exception:
            pass
        return 'desconocido'


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
    """Guarda la preferencia de entrega y pago elegida por el comprador al confirmar la compra."""

    TIPO_ENTREGA_CHOICES = [
        ('delivery', 'Delivery'),
        ('tienda', 'Entrega en la tienda'),
    ]

    TIPO_PAGO_CHOICES = [
        ('transferencia', 'Transferencia'),
        ('efectivo', 'Efectivo'),
    ]

    comprador = models.ForeignKey(User, on_delete=models.CASCADE, related_name='solicitudes_entrega')
    tipo_entrega = models.CharField(max_length=20, choices=TIPO_ENTREGA_CHOICES)
    direccion_entrega = models.CharField(max_length=255, blank=True, null=True)
    referencia = models.CharField(max_length=255, blank=True, null=True)
    tipo_pago = models.CharField(max_length=20, choices=TIPO_PAGO_CHOICES)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"Entrega de {self.comprador.username} - {self.get_tipo_entrega_display()}"


class DatosTransferenciaVendedor(models.Model):
    """Datos bancarios que un vendedor publica para recibir transferencias."""

    TIPO_CUENTA_CHOICES = [
        ('corriente', 'Cuenta corriente'),
        ('vista', 'Cuenta vista'),
        ('ahorro', 'Cuenta de ahorro'),
        ('rut', 'Cuenta RUT'),
    ]

    vendedor = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='datos_transferencia',
    )
    banco = models.CharField(max_length=100)
    tipo_cuenta = models.CharField(max_length=20, choices=TIPO_CUENTA_CHOICES)
    numero_cuenta = models.CharField(max_length=50)
    titular = models.CharField(max_length=150)
    rut = models.CharField(max_length=20)
    email = models.EmailField()
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Datos de transferencia de {self.vendedor.username}"

    @property
    def esta_completo(self):
        return all([
            self.banco,
            self.tipo_cuenta,
            self.numero_cuenta,
            self.titular,
            self.rut,
            self.email,
        ])


class Pedido(models.Model):
    """Registro de un pedido confirmado por un comprador para un vendedor."""

    ESTADO_PEDIDO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('confirmado', 'Confirmado'),
        ('preparando', 'Preparando'),
        ('cancelado', 'Cancelado'),
    ]

    ESTADO_ENTREGA_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('asignado', 'Asignado'),
        ('en_camino', 'En camino'),
        ('entregado', 'Entregado'),
        ('no_entregado', 'No entregado'),
    ]

    comprador = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pedidos_realizados')
    vendedor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pedidos_recibidos')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='pedidos')
    solicitud = models.ForeignKey(SolicitudEntrega, on_delete=models.CASCADE, related_name='pedidos', null=True, blank=True)
    productos_detalle = models.TextField(blank=True, default='')
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.IntegerField(default=0)
    total = models.IntegerField(default=0)
    tipo_entrega = models.CharField(max_length=20, choices=SolicitudEntrega.TIPO_ENTREGA_CHOICES)
    direccion_entrega = models.CharField(max_length=255, blank=True, null=True)
    referencia = models.CharField(max_length=255, blank=True, null=True)
    tipo_pago = models.CharField(max_length=20, choices=SolicitudEntrega.TIPO_PAGO_CHOICES)
    estado = models.CharField(max_length=20, choices=ESTADO_PEDIDO_CHOICES, default='pendiente')
    estado_entrega = models.CharField(max_length=20, choices=ESTADO_ENTREGA_CHOICES, default='pendiente')
    repartidor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='pedidos_delivery_asignados')
    motivo_cancelacion = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"Pedido N°{self.id} - {self.producto.nombre} ({self.cantidad} unidades)"

    @property
    def referencia_historica(self):
        """Devuelve una referencia estable para mostrar en la UI aunque el producto haya sido eliminado lógicamente."""
        if self.productos_detalle:
            return self.productos_detalle
        try:
            return self.producto.nombre
        except Exception:
            return ''


class PaymentProof(models.Model):
    """Comprobante de pago subido por el comprador para un pedido."""
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
    ]

    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='comprobantes')
    imagen = models.ImageField(upload_to='comprobantes/', null=False, blank=False)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    subido_por = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comprobantes_subidos')
    revisado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='comprobantes_revisados')
    fecha_subida = models.DateTimeField(auto_now_add=True)
    fecha_revision = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Comprobante #{self.id} - Pedido N°{self.pedido.id} ({self.estado})"


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
