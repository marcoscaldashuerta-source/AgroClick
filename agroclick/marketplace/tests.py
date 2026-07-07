from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.test import TestCase

from .models import Perfil, deshabilitar_cuenta_usuario


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


class DeshabilitarUsuariosAdminViewTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass',
            is_staff=True,
            is_superuser=True,
        )
        self.vendedor = User.objects.create_user(
            username='usuario_vendedor',
            email='vendedor@example.com',
            password='pass1234'
        )
        self.comprador = User.objects.create_user(
            username='usuario_comprador',
            email='comprador@example.com',
            password='pass1234'
        )
        Perfil.objects.create(usuario=self.vendedor, rol='vendedor', aprobado=True)
        Perfil.objects.create(usuario=self.comprador, rol='comprador', aprobado=True)

    def test_vista_muestra_usuarios_por_rol_y_puede_deshabilitar(self):
        self.client.force_login(self.admin)
        response = self.client.get('/deshabilitar-usuarios/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Vendedores')
        self.assertContains(response, 'Compradores')
        self.assertContains(response, 'Sin rol')
        self.assertContains(response, 'usuario_vendedor')
        self.assertContains(response, 'usuario_comprador')

        response = self.client.post('/deshabilitar-usuarios/', {'usuario_id': self.comprador.id}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'El usuario')
        self.assertContains(response, 'ha sido deshabilitado')
        self.assertContains(response, 'usuario_comprador')

        self.comprador.refresh_from_db()
        self.assertFalse(self.comprador.is_active)
