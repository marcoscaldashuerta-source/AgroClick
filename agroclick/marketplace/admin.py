from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import (
    Perfil,
    deshabilitar_cuenta_usuario,
    Carrito,
    ItemCarrito,
    TicketSoporte,
    SolicitudEntrega,
    Pedido,
    Producto,
    ProductActionLog,
    DatosTransferenciaVendedor,
)


def deshabilitar_cuentas_seleccionadas(modeladmin, request, queryset):
    for usuario in queryset:
        deshabilitar_cuenta_usuario(usuario)


deshabilitar_cuentas_seleccionadas.short_description = 'Deshabilitar cuentas seleccionadas'


admin.site.unregister(User)


@admin.register(User)
class UsuarioAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'is_active', 'is_staff')
    list_filter = ('is_active', 'is_staff')
    actions = [deshabilitar_cuentas_seleccionadas]


admin.site.register(Perfil)
admin.site.register(DatosTransferenciaVendedor)


@admin.register(ItemCarrito)
class ItemCarritoAdmin(admin.ModelAdmin):
    list_display = ('id', 'carrito', 'producto', 'cantidad', 'obtener_subtotal')
    list_filter = ('carrito__comprador', 'fecha_agregado')
    search_fields = ('producto__nombre', 'carrito__comprador__username')
    readonly_fields = ('fecha_agregado',)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('producto', 'carrito')
        return self.readonly_fields


@admin.register(Carrito)
class CarritoAdmin(admin.ModelAdmin):
    list_display = ('id', 'comprador', 'obtener_cantidad_items', 'obtener_total', 'fecha_actualizacion')
    list_filter = ('fecha_creacion', 'fecha_actualizacion')
    search_fields = ('comprador__username',)
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('comprador',)
        return self.readonly_fields


@admin.register(TicketSoporte)
class TicketSoporteAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'razon', 'estado', 'fecha_creacion', 'atendido_por')
    list_filter = ('estado', 'razon', 'fecha_creacion')
    search_fields = ('usuario__username', 'descripcion')
    readonly_fields = ('usuario', 'fecha_creacion', 'fecha_actualizacion')


@admin.register(SolicitudEntrega)
class SolicitudEntregaAdmin(admin.ModelAdmin):
    list_display = ('id', 'comprador', 'tipo_entrega', 'direccion_entrega', 'fecha_creacion')
    list_filter = ('tipo_entrega', 'fecha_creacion')
    search_fields = ('comprador__username', 'direccion_entrega')


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'comprador', 'vendedor', 'producto', 'cantidad', 'total', 'estado', 'fecha_creacion')
    list_filter = ('estado', 'tipo_entrega', 'tipo_pago', 'fecha_creacion')
    search_fields = ('comprador__username', 'vendedor__username', 'producto__nombre', 'direccion_entrega')
    readonly_fields = ('fecha_creacion',)


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'vendedor', 'precio', 'stock', 'estado', 'fecha_creacion')
    list_filter = ('estado', 'categoria', 'fecha_creacion')
    search_fields = ('nombre', 'vendedor__username', 'descripcion')
    readonly_fields = ('fecha_creacion',)
    change_list_template = 'admin/marketplace/product/change_list.html'


@admin.register(ProductActionLog)
class ProductActionLogAdmin(admin.ModelAdmin):
    """Registro de actividad del sistema: solo lectura para administradores."""
    list_display = ('id', 'producto', 'actor_role', 'accion', 'fecha')
    list_filter = ('accion', 'fecha')
    search_fields = ('producto__nombre', 'actor__username', 'accion')
    readonly_fields = ('producto', 'actor', 'accion', 'fecha')
    ordering = ('-fecha',)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False
