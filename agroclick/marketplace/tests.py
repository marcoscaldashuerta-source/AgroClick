from io import BytesIO

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from .models import Perfil, Producto, Carrito, ItemCarrito, Pedido, deshabilitar_cuenta_usuario, ProductImage


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


class PublicarProductoDraftTests(TestCase):
    def test_guardar_borrador_sin_nombre_muestra_error_especifico(self):
        vendedor = User.objects.create_user(username='vendedor_draft', email='vendedor_draft@example.com', password='pass1234')
        Perfil.objects.create(usuario=vendedor, rol='vendedor', aprobado=True)

        self.client.force_login(vendedor)
        response = self.client.post('/publicar/', {'guardar_borrador': 'Guardar borrador'}, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'El nombre del producto es obligatorio para guardar un borrador.')
        self.assertFalse(Producto.objects.exists())


class ActualizarEstadoPedidoTests(TestCase):
    def test_confirmar_pedido_descuenta_stock_y_cambia_estado(self):
        comprador = User.objects.create_user(username='comprador_prueba', email='comprador@prueba.com', password='pass1234')
        vendedor = User.objects.create_user(username='vendedor_prueba', email='vendedor@prueba.com', password='pass1234')
        Perfil.objects.create(usuario=comprador, rol='comprador', aprobado=True)
        Perfil.objects.create(usuario=vendedor, rol='vendedor', aprobado=True)

        producto = Producto.objects.create(
            vendedor=vendedor,
            nombre='Zanahoria',
            categoria='Verdura',
            descripcion='Zanahoria fresca',
            precio=3000,
            unidad_venta='kg',
            stock=8,
            borrador=False,
            estado='activo',
        )
        pedido = Pedido.objects.create(
            comprador=comprador,
            vendedor=vendedor,
            producto=producto,
            cantidad=3,
            precio_unitario=producto.precio,
            total=producto.precio * 3,
            tipo_entrega='delivery',
            direccion_entrega='Calle 456',
            referencia='Portón negro',
            tipo_pago='transferencia',
            estado='pendiente',
        )

        self.client.force_login(vendedor)
        response = self.client.post(f'/pedido/estado/{pedido.id}/', {'accion': 'confirmar'}, follow=True)

        self.assertEqual(response.status_code, 200)
        pedido.refresh_from_db()
        producto.refresh_from_db()
        self.assertEqual(pedido.estado, 'confirmado')
        self.assertEqual(producto.stock, 5)


class EditarProductoMainImageTests(TestCase):
    def test_se_puede_cambiar_la_imagen_principal_a_una_existente(self):
        vendedor = User.objects.create_user(username='vendedor_principal', email='vendedor_principal@example.com', password='pass1234')
        Perfil.objects.create(usuario=vendedor, rol='vendedor', aprobado=True)

        def create_uploaded_image(name):
            image = Image.new('RGB', (1, 1), color=(255, 0, 0))
            buffer = BytesIO()
            image.save(buffer, format='PNG')
            return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/png')

        producto = Producto.objects.create(
            vendedor=vendedor,
            nombre='Tomate',
            categoria='Fruta',
            descripcion='Tomate rojo',
            precio=1000,
            unidad_venta='kg',
            stock=10,
            imagen=create_uploaded_image('principal.png'),
            borrador=False,
            estado='activo',
        )
        imagen_galeria = ProductImage.objects.create(
            producto=producto,
            imagen=create_uploaded_image('galeria.png'),
            orden=1,
        )

        self.client.force_login(vendedor)
        response = self.client.post(f'/editar-producto/{producto.id}/', {
            'nombre': producto.nombre,
            'categoria': 'Fruta',
            'descripcion': producto.descripcion,
            'precio': producto.precio,
            'unidad_venta': producto.unidad_venta,
            'stock': producto.stock,
            'main_image_index': '1',
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        producto.refresh_from_db()
        self.assertEqual(producto.imagen.name, imagen_galeria.imagen.name)


class EditarProductoMainImagePreservaAnteriorTests(TestCase):
    def test_al_cambiar_la_imagen_principal_se_preserva_la_anterior_en_la_galeria(self):
        vendedor = User.objects.create_user(username='vendedor_preserva', email='vendedor_preserva@example.com', password='pass1234')
        Perfil.objects.create(usuario=vendedor, rol='vendedor', aprobado=True)

        def create_uploaded_image(name):
            image = Image.new('RGB', (3, 3), color=(0, 0, 255))
            buffer = BytesIO()
            image.save(buffer, format='PNG')
            return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/png')

        producto = Producto.objects.create(
            vendedor=vendedor,
            nombre='Aguacate',
            categoria='Fruta',
            descripcion='Aguacate orgánico',
            precio=2000,
            unidad_venta='kg',
            stock=15,
            imagen=create_uploaded_image('principal.png'),
            borrador=False,
            estado='activo',
        )
        imagen_galeria = ProductImage.objects.create(
            producto=producto,
            imagen=create_uploaded_image('galeria.png'),
            orden=1,
        )

        self.client.force_login(vendedor)
        response = self.client.post(f'/editar-producto/{producto.id}/', {
            'nombre': producto.nombre,
            'categoria': 'Fruta',
            'descripcion': producto.descripcion,
            'precio': producto.precio,
            'unidad_venta': producto.unidad_venta,
            'stock': producto.stock,
            'main_image_index': '1',
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        producto.refresh_from_db()
        self.assertEqual(producto.imagen.name, imagen_galeria.imagen.name)
        self.assertTrue(ProductImage.objects.filter(producto=producto, imagen__name__icontains='principal.png').exists())


class EditarProductoRemoverMainImageTests(TestCase):
    def test_al_eliminar_la_imagen_principal_se_promociona_la_galeria_restante(self):
        vendedor = User.objects.create_user(
            username='vendedor_remueve',
            email='vendedor_remueve@example.com',
            password='pass1234',
        )
        Perfil.objects.create(usuario=vendedor, rol='vendedor', aprobado=True)

        def create_uploaded_image(name):
            image = Image.new('RGB', (2, 2), color=(255, 255, 0))
            buffer = BytesIO()
            image.save(buffer, format='PNG')
            return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/png')

        producto = Producto.objects.create(
            vendedor=vendedor,
            nombre='Banano',
            categoria='Fruta',
            descripcion='Banano fresco',
            precio=1200,
            unidad_venta='kg',
            stock=12,
            imagen=create_uploaded_image('principal.png'),
            borrador=False,
            estado='activo',
        )
        imagen_galeria = ProductImage.objects.create(
            producto=producto,
            imagen=create_uploaded_image('galeria.png'),
            orden=1,
        )

        self.client.force_login(vendedor)
        response = self.client.post(f'/editar-producto/{producto.id}/', {
            'nombre': producto.nombre,
            'categoria': 'Fruta',
            'descripcion': producto.descripcion,
            'precio': producto.precio,
            'unidad_venta': producto.unidad_venta,
            'stock': producto.stock,
            'main_image_index': '0',
            'deleted_image_ids': '',
            'removed_main_image': '1',
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        producto.refresh_from_db()
        self.assertEqual(producto.imagen.name, imagen_galeria.imagen.name)
        self.assertFalse(producto.imagenes.exists())


class PublicarProductoMainImageTests(TestCase):
    def test_publicar_producto_usa_la_imagen_seleccionada_como_principal(self):
        vendedor = User.objects.create_user(username='vendedor_publica', email='vendedor_publica@example.com', password='pass1234')
        Perfil.objects.create(usuario=vendedor, rol='vendedor', aprobado=True)

        def create_uploaded_image(name):
            image = Image.new('RGB', (2, 2), color=(0, 255, 0))
            buffer = BytesIO()
            image.save(buffer, format='PNG')
            return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/png')

        self.client.force_login(vendedor)
        response = self.client.post('/publicar/', {
            'nombre': 'Pepino',
            'categoria': 'Verdura',
            'descripcion': 'Pepino fresco',
            'precio': '1500',
            'unidad_venta': 'kg',
            'stock': '12',
            'main_image_index': '1',
            'images': [create_uploaded_image('uno.png'), create_uploaded_image('dos.png')],
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        producto = Producto.objects.get(nombre='Pepino')
        self.assertTrue(producto.imagen)
        self.assertTrue(producto.imagenes.exists())
        self.assertEqual(producto.imagen.name, producto.imagenes.first().imagen.name)

