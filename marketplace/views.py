from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from .forms import RegistroForm
from .models import Perfil

def inicio(request):
    return render(request, 'inicio.html')

def registro(request):

    if request.method == 'POST':
        form = RegistroForm(request.POST)

        if form.is_valid():

            usuario = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password']
            )

            Perfil.objects.create(
                usuario=usuario,
                rol=form.cleaned_data['rol'],
                aprobado=False
            )

            return redirect('/admin')

    else:
        form = RegistroForm()

    return render(
        request,
        'registro.html',
        {'form': form}
    )
