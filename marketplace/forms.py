from django import forms
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