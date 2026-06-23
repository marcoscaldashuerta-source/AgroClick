from django.db import models
from django.contrib.auth.models import User

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