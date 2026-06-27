from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from .forms import LoginForm, RegisterForm
from .models import Cliente
import uuid
from rest_framework_simplejwt.tokens import RefreshToken

ROLES_TRABAJADOR = ['ASESOR', 'RIESGOS', 'COMITE', 'GERENCIA', 'ADMIN']


def _get_rol(user):
    """Retorna el rol del usuario o 'CLIENTE' si no tiene perfil."""
    try:
        return user.cliente.rol
    except Exception:
        return 'CLIENTE'


def register_view(request):
    if request.user.is_authenticated:
        rol = _get_rol(request.user)
        if rol in ROLES_TRABAJADOR:
            return redirect('/core/')
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
    """Vista de inicio de sesión exclusiva para CLIENTES."""

    # Si ya está logueado, redirigir al área correcta
    if request.user.is_authenticated:
        rol = _get_rol(request.user)
        if rol in ROLES_TRABAJADOR:
            return redirect('/core/')
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
                    rol = _get_rol(user)

                    # Verificar que sea cliente — el login de Homebanking es solo para clientes
                    if rol in ROLES_TRABAJADOR:
                        form.add_error(None, 'Este acceso es exclusivo para clientes. Los trabajadores deben ingresar por el Core Bancario.')
                    else:
                        login(request, user)
                        next_url = request.GET.get('next', '/dashboard/')
                        if next_url.startswith('/core'):
                            next_url = '/dashboard/'
                        
                        refresh = RefreshToken.for_user(user)
                        response = redirect(next_url)
                        response.set_cookie('access_token', str(refresh.access_token), httponly=True)
                        return response
                else:
                    form.add_error(None, 'Tu cuenta está desactivada. Contacta a soporte.')
            else:
                form.add_error(None, 'Número de documento o contraseña incorrectos.')

    return render(request, 'login.html', {'form': form})


def logout_view(request):
    """Cierra la sesión y redirige al login correspondiente."""
    is_trabajador = False
    if request.user.is_authenticated:
        rol = _get_rol(request.user)
        if rol in ROLES_TRABAJADOR:
            is_trabajador = True
            
    logout(request)
    
    if is_trabajador:
        response = redirect('authentication:login_trabajador')
    else:
        response = redirect('authentication:login')
        
    response.delete_cookie('access_token')
    return response


def login_trabajador_view(request):
    """Vista de inicio de sesión exclusiva para trabajadores (Asesor, Riesgos, Comité, Gerencia, Admin)."""

    # Si ya está logueado, redirigir al área correcta
    if request.user.is_authenticated:
        rol = _get_rol(request.user)
        if rol in ROLES_TRABAJADOR:
            return redirect('/core/')
        return redirect('/dashboard/')

    from .forms import LoginTrabajadorForm
    form = LoginTrabajadorForm()

    if request.method == 'POST':
        form = LoginTrabajadorForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(request, username=username, password=password)

            if user is not None:
                if user.is_active:
                    # Verificar que sea trabajador
                    try:
                        cliente = user.cliente
                        if cliente.rol in ROLES_TRABAJADOR:
                            login(request, user)
                            refresh = RefreshToken.for_user(user)
                            response = redirect('/core/')
                            response.set_cookie('access_token', str(refresh.access_token), httponly=True)
                            return response
                        else:
                            form.add_error(None, 'Este acceso es exclusivo para trabajadores de Financiera Confianza. Los clientes deben ingresar por Banca por Internet.')
                    except Exception:
                        form.add_error(None, 'Usuario no encontrado en el sistema.')
                else:
                    form.add_error(None, 'Tu cuenta está desactivada. Contacta a soporte.')
            else:
                form.add_error(None, 'Usuario o contraseña incorrectos.')

    return render(request, 'login_trabajador.html', {'form': form})
