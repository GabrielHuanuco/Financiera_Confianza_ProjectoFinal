from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from .forms import LoginForm, RegisterForm
from .models import Cliente
import uuid

def register_view(request):
    if request.user.is_authenticated:
        return redirect('/dashboard/')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            nombres = form.cleaned_data['nombres']
            apellidos = form.cleaned_data['apellidos']
            dni = form.cleaned_data['dni']
            correo = form.cleaned_data['correo']
            telefono = form.cleaned_data['telefono']
            password = form.cleaned_data['password']

            # Create User. Username is DNI
            user = User.objects.create_user(
                username=dni,
                email=correo,
                password=password,
                first_name=nombres,
                last_name=apellidos
            )

            # Create Cliente
            Cliente.objects.create(
                usuario=user,
                uid=uuid.uuid4(),
                telefono=telefono,
                dni=dni,
                direccion='',
                ingresos=0.00,
                score_crediticio=0,
                estado=True
            )

            messages.success(request, 'Tu cuenta ha sido creada exitosamente. Ya puedes iniciar sesión.')
            return redirect('authentication:login')
    else:
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})

def login_view(request):
    """Vista de inicio de sesión."""

    # Si ya está logueado, va al dashboard directamente
    if request.user.is_authenticated:
        return redirect('/dashboard/')

    form = LoginForm()

    if request.method == 'POST':
        form = LoginForm(request.POST)

        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            # Django autentica por username (que es el número de documento)
            user = authenticate(request, username=username, password=password)

            if user is not None:
                if user.is_active:
                    login(request, user)
                    # Redirige a la página que pidió, o al dashboard
                    next_url = request.GET.get('next', '/dashboard/')
                    return redirect(next_url)
                else:
                    form.add_error(None, 'Tu cuenta está desactivada. Contacta a soporte.')
            else:
                form.add_error(None, 'Número de documento o contraseña incorrectos.')

    return render(request, 'login.html', {'form': form})


def logout_view(request):
    """Cierra la sesión y redirige al login."""
    logout(request)
    return redirect('/auth/')