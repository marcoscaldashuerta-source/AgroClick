from io import BytesIO

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from .models import Perfil, Producto, Carrito, ItemCarrito, Pedido, Notificacion, deshabilitar_cuenta_usuario, ProductImage


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
            username='admin_deshab_test',
            email='admin_deshab_test@example.com',
            password='adminpass',
            is_staff=True,
            is_superuser=True,
        )
        self.vendedor = User.objects.create_user(
            username='usuario_vendedor_deshab',
            email='vendedor_deshab@example.com',
            password='pass1234'
        )
        self.comprador = User.objects.create_user(
            username='usuario_comprador_deshab',
            email='comprador_deshab@example.com',
            password='pass1234'
        )
        self.vendedor_pendiente = User.objects.create_user(
            username='vendedor_pendiente_deshab',
            email='vendedor_pendiente_deshab@example.com',
            password='pass1234'
        )
        Perfil.objects.create(usuario=self.vendedor, rol='vendedor', aprobado=True)
        Perfil.objects.create(usuario=self.comprador, rol='comprador', aprobado=True)
        Perfil.objects.create(usuario=self.vendedor_pendiente, rol='vendedor', aprobado=False)

    def test_vista_muestra_usuarios_por_rol_y_puede_deshabilitar_y_habilitar(self):
        self.client.force_login(self.admin)
        response = self.client.get('/deshabilitar-usuarios/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Vendedores')
        self.assertContains(response, 'Compradores')
        self.assertNotContains(response, 'Sin rol')
        self.assertContains(response, 'usuario_vendedor_deshab')
        self.assertContains(response, 'usuario_comprador_deshab')
        self.assertContains(response, 'Deshabilitar')

        response = self.client.post('/deshabilitar-usuarios/', {'usuario_id': self.comprador.id}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'El usuario')
        self.assertContains(response, 'ha sido deshabilitado')
        self.assertContains(response, 'usuario_comprador_deshab')
        self.comprador.refresh_from_db()
        self.assertFalse(self.comprador.is_active)

        response = self.client.get('/deshabilitar-usuarios/')
        self.assertContains(response, 'Habilitar')

        response = self.client.post('/deshabilitar-usuarios/', {'usuario_id': self.comprador.id}, follow=True)
        self.assertContains(response, 'El usuario')
        self.assertContains(response, 'ha sido habilitado')
        self.assertContains(response, 'usuario_comprador_deshab')
        self.comprador.refresh_from_db()
        self.assertTrue(self.comprador.is_active)

    def test_vendedores_pendientes_no_aparecen_ni_se_pueden_deshabilitar(self):
        self.client.force_login(self.admin)

        response = self.client.get('/deshabilitar-usuarios/')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'vendedor_pendiente_deshab')

        response = self.client.post('/deshabilitar-usuarios/', {'usuario_id': self.vendedor_pendiente.id}, follow=True)
        self.assertContains(response, 'No puedes deshabilitar vendedores pendientes de aprobación.')
        self.vendedor_pendiente.refresh_from_db()
        self.assertTrue(self.vendedor_pendiente.is_active)


class NotificacionesPedidoFormattingTests(TestCase):
    def test_ver_notificaciones_normaliza_mensajes_antiguos_con_pedido_numero(self):
        usuario = User.objects.create_user(
            username='usuario_notificaciones',
            email='notificaciones@example.com',
            password='pass1234',
        )
        notificacion = Notificacion.objects.create(
            usuario=usuario,
            mensaje='Tu pedido #7 fue cancelado por el vendedor.',
        )

        self.client.force_login(usuario)
        response = self.client.get('/notificaciones/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pedido N°7')
        self.assertContains(response, 'Tu Pedido N°7')
        notificacion.refresh_from_db()
        self.assertIn('Pedido N°7', notificacion.mensaje)


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

    def test_checkout_con_varios_productos_del_mismo_vendedor_crea_un_solo_pedido(self):
        comprador = User.objects.create_user(username='comprador_multi', email='comprador_multi@test.com', password='pass1234')
        vendedor = User.objects.create_user(username='vendedor_multi', email='vendedor_multi@test.com', password='pass1234')
        Perfil.objects.create(usuario=comprador, rol='comprador', aprobado=True)
        Perfil.objects.create(usuario=vendedor, rol='vendedor', aprobado=True)

        tomate = Producto.objects.create(
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
        platano = Producto.objects.create(
            vendedor=vendedor,
            nombre='Plátano',
            categoria='Fruta',
            descripcion='Plátano maduro',
            precio=2500,
            unidad_venta='kg',
            stock=10,
            borrador=False,
            estado='activo',
        )
        carrito = Carrito.objects.create(comprador=comprador)
        ItemCarrito.objects.create(carrito=carrito, producto=tomate, cantidad=1)
        ItemCarrito.objects.create(carrito=carrito, producto=platano, cantidad=1)

        self.client.force_login(comprador)
        response = self.client.post('/carrito/checkout/', {
            'tipo_entrega': 'delivery',
            'direccion_entrega': 'Calle 456',
            'referencia': 'Depto 2',
            'tipo_pago': 'transferencia',
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Pedido.objects.filter(comprador=comprador, vendedor=vendedor).count(), 1)
        pedido = Pedido.objects.get(comprador=comprador, vendedor=vendedor)
        self.assertEqual(pedido.cantidad, 2)
        self.assertEqual(pedido.total, 7500)
        self.assertEqual(pedido.direccion_entrega, 'Calle 456')
        self.assertIn('Tomate', pedido.productos_detalle)
        self.assertIn('Plátano', pedido.productos_detalle)


class NavbarMisPedidosTests(TestCase):
    def test_navbar_muestra_boton_mis_pedidos_para_comprador(self):
        comprador = User.objects.create_user(
            username='comprador_navbar',
            email='comprador_navbar@example.com',
            password='pass1234'
        )
        Perfil.objects.create(usuario=comprador, rol='comprador', aprobado=True)

        self.client.force_login(comprador)
        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mis pedidos')
        self.assertContains(response, '/mis-pedidos/')

    def test_mis_pedidos_permite_acceso_a_comprador_no_aprobado(self):
        comprador = User.objects.create_user(
            username='comprador_no_aprobado',
            email='comprador_no_aprobado@example.com',
            password='pass1234'
        )
        Perfil.objects.create(usuario=comprador, rol='comprador', aprobado=False)

        self.client.force_login(comprador)
        response = self.client.get('/mis-pedidos/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mis pedidos')


class PublicarProductoDraftTests(TestCase):
    def test_guardar_borrador_sin_nombre_muestra_error_especifico(self):
        vendedor = User.objects.create_user(username='vendedor_draft', email='vendedor_draft@example.com', password='pass1234')
        Perfil.objects.create(usuario=vendedor, rol='vendedor', aprobado=True)

        self.client.force_login(vendedor)
        response = self.client.post('/publicar/', {'guardar_borrador': 'Guardar borrador'}, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'El nombre del producto es obligatorio para guardar un borrador.')
        self.assertFalse(Producto.objects.exists())


class PublicarProductoSinImagenTests(TestCase):
    def test_publicar_sin_imagen_muestra_error_y_no_crea_producto(self):
        vendedor = User.objects.create_user(username='vendedor_sin_imagen', email='vendedor_sin_imagen@example.com', password='pass1234')
        Perfil.objects.create(usuario=vendedor, rol='vendedor', aprobado=True)

        self.client.force_login(vendedor)
        response = self.client.post('/publicar/', {
            'nombre': 'Pepino',
            'categoria': 'Verdura',
            'descripcion': 'Pepino fresco',
            'precio': '1500',
            'unidad_venta': 'kg',
            'stock': '12',
            'publicar': 'Publicar ahora',
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Debes agregar al menos una imagen antes de publicar o guardar el producto.')
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


class DeliveryPedidosTests(TestCase):
    def setUp(self):
        self.comprador = User.objects.create_user(username='comprador_delivery', email='comprador_delivery@test.com', password='pass1234')
        self.vendedor = User.objects.create_user(username='vendedor_delivery', email='vendedor_delivery@test.com', password='pass1234')
        self.delivery = User.objects.create_user(username='delivery_usuario', email='delivery_usuario@test.com', password='pass1234')
        Perfil.objects.create(usuario=self.comprador, rol='comprador', aprobado=True)
        Perfil.objects.create(usuario=self.vendedor, rol='vendedor', aprobado=True)
        Perfil.objects.create(usuario=self.delivery, rol='delivery', aprobado=True)

        self.producto = Producto.objects.create(
            vendedor=self.vendedor,
            nombre='Lechuga',
            categoria='Verdura',
            descripcion='Lechuga fresca',
            precio=1200,
            unidad_venta='unidad',
            stock=20,
            borrador=False,
            estado='activo',
        )
        self.pedido = Pedido.objects.create(
            comprador=self.comprador,
            vendedor=self.vendedor,
            producto=self.producto,
            cantidad=2,
            precio_unitario=self.producto.precio,
            total=self.producto.precio * 2,
            productos_detalle='Lechuga (x2)',
            tipo_entrega='delivery',
            direccion_entrega='Calle 123',
            referencia='Puerta roja',
            tipo_pago='efectivo',
            estado='confirmado',
        )
        self.client.force_login(self.delivery)

    def test_pedidos_delivery_muestra_pedido_disponible(self):
        response = self.client.get('/delivery/pedidos/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pedidos disponibles')
        self.assertContains(response, 'Realizar delivery')
        self.assertContains(response, 'Calle 123')

    def test_realizar_delivery_asigna_pedido_a_repartidor(self):
        response = self.client.post(f'/delivery/pedido/{self.pedido.id}/asignar/', follow=True)
        self.assertEqual(response.status_code, 200)
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.repartidor, self.delivery)
        self.assertEqual(self.pedido.estado_entrega, 'asignado')
        self.assertContains(response, 'Mis pedidos asignados')
        self.assertContains(response, 'Calle 123')

    def test_ver_detalle_pedido_delivery_muestra_informacion_completa(self):
        self.pedido.repartidor = self.delivery
        self.pedido.estado_entrega = 'asignado'
        self.pedido.save()

        response = self.client.get(f'/delivery/pedido/{self.pedido.id}/detalle/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Calle 123')
        self.assertContains(response, 'comprador_delivery')
        self.assertContains(response, 'Lechuga')
        self.assertContains(response, 'vendedor_delivery')
        self.assertContains(response, 'Puerta roja')

    def test_mis_pedidos_muestra_estado_entrega_en_detalle_del_pedido(self):
        self.pedido.repartidor = self.delivery
        self.pedido.estado_entrega = 'en_camino'
        self.pedido.save()

        self.client.force_login(self.comprador)
        response = self.client.get('/mis-pedidos/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="detail-estado-entrega"')
        self.assertContains(response, 'Estado entrega:')
        self.assertContains(response, 'En camino')

    def test_actualizar_estado_entrega_a_en_camino_y_entregado(self):
        self.pedido.repartidor = self.delivery
        self.pedido.estado_entrega = 'asignado'
        self.pedido.save()

        response = self.client.post(f'/delivery/pedido/{self.pedido.id}/actualizar-estado/', {'estado_entrega': 'en_camino'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado_entrega, 'en_camino')

        response = self.client.post(f'/delivery/pedido/{self.pedido.id}/actualizar-estado/', {'estado_entrega': 'entregado'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado_entrega, 'entregado')
        self.assertTrue(Notificacion.objects.filter(usuario=self.comprador, mensaje__icontains='entregado').exists())
        self.assertTrue(Notificacion.objects.filter(usuario=self.vendedor, mensaje__icontains='entregado').exists())


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


class EliminarProductoSoftDeleteTests(TestCase):
    def test_la_vista_de_eliminacion_marcar_producto_como_eliminado_y_preserva_datos(self):
        vendedor = User.objects.create_user(username='vendedor_soft_delete', email='vendedor_soft_delete@example.com', password='pass1234')
        Perfil.objects.create(usuario=vendedor, rol='vendedor', aprobado=True)

        def create_uploaded_image(name):
            image = Image.new('RGB', (2, 2), color=(0, 255, 0))
            buffer = BytesIO()
            image.save(buffer, format='PNG')
            return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/png')

        producto = Producto.objects.create(
            vendedor=vendedor,
            nombre='Plátano',
            categoria='Fruta',
            descripcion='Plátano maduro',
            precio=1200,
            unidad_venta='kg',
            stock=5,
            imagen=create_uploaded_image('principal.png'),
            borrador=False,
            estado='activo',
        )
        ProductImage.objects.create(producto=producto, imagen=create_uploaded_image('galeria.png'), orden=1)

        self.assertTrue(producto.imagen.storage.exists(producto.imagen.name))
        self.assertTrue(producto.imagenes.first().imagen.storage.exists(producto.imagenes.first().imagen.name))

        self.client.force_login(vendedor)
        response = self.client.post(f'/eliminar-producto/{producto.id}/', {'confirmar_eliminar': 'si'}, follow=True)

        self.assertEqual(response.status_code, 200)
        producto.refresh_from_db()
        self.assertEqual(producto.estado, 'eliminado')
        self.assertTrue(Producto.objects.filter(id=producto.id).exists())
        self.assertTrue(ProductImage.objects.filter(producto_id=producto.id).exists())
        self.assertTrue(producto.imagen.storage.exists(producto.imagen.name))
        self.assertTrue(producto.imagenes.first().imagen.storage.exists(producto.imagenes.first().imagen.name))


class PedidoReferenciaHistoricaTests(TestCase):
    def test_pedido_conserva_referencia_historica_al_eliminar_producto(self):
        vendedor = User.objects.create_user(username='vendedor_historial', email='vendedor_historial@example.com', password='pass1234')
        comprador = User.objects.create_user(username='comprador_historial', email='comprador_historial@example.com', password='pass1234')
        Perfil.objects.create(usuario=vendedor, rol='vendedor', aprobado=True)
        Perfil.objects.create(usuario=comprador, rol='comprador', aprobado=True)

        producto = Producto.objects.create(
            vendedor=vendedor,
            nombre='Lechuga',
            categoria='Verdura',
            descripcion='Lechuga fresca',
            precio=1500,
            unidad_venta='kg',
            stock=8,
            borrador=False,
            estado='activo',
        )
        pedido = Pedido.objects.create(
            comprador=comprador,
            vendedor=vendedor,
            producto=producto,
            cantidad=2,
            precio_unitario=producto.precio,
            total=producto.precio * 2,
            tipo_entrega='delivery',
            direccion_entrega='Calle 999',
            referencia='Casa verde',
            tipo_pago='transferencia',
            estado='pendiente',
        )

        producto.soft_delete()

        self.assertEqual(pedido.referencia_historica, 'Lechuga')
        self.assertEqual(pedido.producto.nombre, 'Lechuga')


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

