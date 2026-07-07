from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.test import TestCase

from .models import deshabilitar_cuenta_usuario


class DeshabilitarCuentaUsuarioTests(TestCase):
    def test_desactivar_cuenta_usuario_inactiva_y_bloquea_login(self):
        usuario = User.objects.create_user(
            username='usuario_prueba',
            email='usuario@prueba.com',
            password='contraseña123',
            is_active=True,
        )

        usuario_desactivado = deshabilitar_cuenta_usuario(usuario)

        self.assertFalse(usuario_desactivado.is_active)
        self.assertIsNone(
            authenticate(username='usuario_prueba', password='contraseña123')
        )
