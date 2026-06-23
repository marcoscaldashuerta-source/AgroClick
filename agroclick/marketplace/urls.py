from django.urls import path
from . import views

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('registro/', views.registro, name='registro'),
    path('publicar/', views.publicar_producto, name='publicar_producto'),
    path('logout/', views.cerrar_sesion, name='cerrar_sesion'),
    path('aprobar-vendedores/', views.aprobar_vendedores, name='aprobar_vendedores'),
    path('mis-productos/', views.mis_productos, name='mis_productos'),
    path('editar-producto/<int:producto_id>/', views.editar_producto, name='editar_producto'),
    path('pausar-producto/<int:producto_id>/', views.pausar_producto, name='pausar_producto'),
    path('eliminar-producto/<int:producto_id>/', views.eliminar_producto, name='eliminar_producto'),
]