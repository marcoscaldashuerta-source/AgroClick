from django.urls import path
from . import views

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('registro/', views.registro, name='registro'),
    path('publicar/', views.publicar_producto, name='publicar_producto'),
    path('logout/', views.cerrar_sesion, name='cerrar_sesion'),
    path('aprobar-vendedores/', views.aprobar_vendedores, name='aprobar_vendedores'),
    path('deshabilitar-usuarios/', views.deshabilitar_usuarios_admin, name='deshabilitar_usuarios_admin'),
    path('supervisar-productos/', views.supervisar_productos, name='supervisar_productos'),
    path('eliminar-producto-admin/<int:producto_id>/', views.eliminar_producto_admin, name='eliminar_producto_admin'),
    path('notificaciones/', views.ver_notificaciones, name='ver_notificaciones'),
    path('mis-productos/', views.mis_productos, name='mis_productos'),
    path('editar-producto/<int:producto_id>/', views.editar_producto, name='editar_producto'),
    path('pausar-producto/<int:producto_id>/', views.pausar_producto, name='pausar_producto'),
    path('eliminar-producto/<int:producto_id>/', views.eliminar_producto, name='eliminar_producto'),
    # Rutas del carrito
    path('carrito/', views.ver_carrito, name='ver_carrito'),
    path('carrito/agregar/<int:producto_id>/', views.agregar_al_carrito, name='agregar_al_carrito'),
    path('carrito/actualizar/<int:item_id>/', views.actualizar_cantidad_carrito, name='actualizar_cantidad_carrito'),
    path('carrito/eliminar/<int:item_id>/', views.eliminar_del_carrito, name='eliminar_del_carrito'),
    path('carrito/vaciar/', views.vaciar_carrito, name='vaciar_carrito'),
    path('carrito/checkout/', views.checkout, name='checkout'),
    # Rutas de soporte
    path('soporte/', views.enviar_soporte, name='enviar_soporte'),
    path('admin-soporte/', views.panel_soporte, name='panel_soporte'),
    path('admin-soporte/<int:ticket_id>/', views.responder_ticket, name='responder_ticket'),
]