from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import Perfil, deshabilitar_cuenta_usuario, Carrito, ItemCarrito, TicketSoporte


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