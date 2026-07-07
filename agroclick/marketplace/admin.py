from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import Perfil, deshabilitar_cuenta_usuario


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