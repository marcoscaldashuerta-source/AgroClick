from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.test import TestCase

from .models import Perfil, Producto, Carrito, ItemCarrito, Pedido, deshabilitar_cuenta_usuario


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

    def test_vista_muestra_usuarios_por_rol_y_puede_deshabilitar_y_habilitar(self):
        self.client.force_login(self.admin)
        response = self.client.get('/deshabilitar-usuarios/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Vendedores')
        self.assertContains(response, 'Compradores')
        self.assertNotContains(response, 'Sin rol')
        self.assertContains(response, 'usuario_vendedor')
        self.assertContains(response, 'usuario_comprador')
        self.assertContains(response, 'Deshabilitar')

        response = self.client.post('/deshabilitar-usuarios/', {'usuario_id': self.comprador.id}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'El usuario')
        self.assertContains(response, 'ha sido deshabilitado')
        self.assertContains(response, 'usuario_comprador')
        self.comprador.refresh_from_db()
        self.assertFalse(self.comprador.is_active)

        response = self.client.get('/deshabilitar-usuarios/')
        self.assertContains(response, 'Habilitar')

        response = self.client.post('/deshabilitar-usuarios/', {'usuario_id': self.comprador.id}, follow=True)
        self.assertContains(response, 'El usuario')
        self.assertContains(response, 'ha sido habilitado')
        self.assertContains(response, 'usuario_comprador')
        self.comprador.refresh_from_db()
        self.assertTrue(self.comprador.is_active)


class CheckoutOrdersTests(TestCase):
    def test_checkout_crea_pedido_y_lo_muestra_en_pagina_del_vendedor(self):
        comprador = User.objects.create_user(username='comprador_test', email='comprador@test.com', password='pass1234')
        vendedor = User.objects.create_user(username='vendedor_test', email='vendedor@test.com', password='pass1234')
        Perfil.objects.create(usuario=comprador, rol='comprador', aprobado=True)
        Perfil.objects.create(usuario=vendedor, rol='vendedor', aprobado=True)

        producto = Producto.objects.create(
            vendedor=vendedor,
            nombre='Tomate',
            categoria='Fruta',
            descripcion='Tomate rojo',
            precio=5000,
            unidad_venta='kg',
            stock=10,
            borrador=False,
            estado='activo',
        )
        carrito = Carrito.objects.create(comprador=comprador)
        ItemCarrito.objects.create(carrito=carrito, producto=producto, cantidad=2)

        self.client.force_login(comprador)
        response = self.client.post('/carrito/checkout/', {
            'tipo_entrega': 'delivery',
            'direccion_entrega': 'Calle 123',
            'referencia': 'Casa azul',
            'tipo_pago': 'transferencia',
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Pedido.objects.filter(comprador=comprador, vendedor=vendedor).count(), 1)
        self.assertEqual(carrito.items.count(), 0)

        pedido = Pedido.objects.get(comprador=comprador, vendedor=vendedor)
        self.assertEqual(pedido.cantidad, 2)
        self.assertEqual(pedido.precio_unitario, 5000)
        self.assertEqual(pedido.direccion_entrega, 'Calle 123')

        self.client.force_login(vendedor)
        response = self.client.get('/')
        self.assertContains(response, 'Tomate')
        self.assertContains(response, 'Calle 123')
