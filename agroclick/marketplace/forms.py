from django import forms
from .models import Producto
from django.contrib.auth.models import User

class RegistroForm(forms.Form):
    username = forms.CharField(max_length=150)
    email = forms.EmailField()

    password = forms.CharField(
        widget=forms.PasswordInput
    )

    ROL_CHOICES = [
        ('comprador', 'Comprador'),
        ('vendedor', 'Vendedor'),
    ]

    rol = forms.ChoiceField(
        choices=ROL_CHOICES
    )

class ProductoForm(forms.ModelForm):

    class Meta:
        model = Producto

        fields = [
            'nombre',
            'categoria',
            'descripcion',
            'precio',
            'unidad_venta',
            'stock',
            'imagen'
        ]