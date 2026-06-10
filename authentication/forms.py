from django import forms
from django.contrib.auth.models import User
from .models import Cliente

class RegisterForm(forms.Form):
    nombres = forms.CharField(max_length=100, required=True, error_messages={'required': 'Ingrese sus nombres.'})
    apellidos = forms.CharField(max_length=100, required=True, error_messages={'required': 'Ingrese sus apellidos.'})
    tipo_documento = forms.ChoiceField(
        choices=[
            ('', 'Seleccione su tipo de documento'),
            ('DNI', 'DNI'),
            ('CE', 'Carnet de Extranjería'),
            ('RUC', 'RUC'),
        ],
        required=True,
        error_messages={'required': 'Seleccione su tipo de documento.'}
    )
    dni = forms.CharField(max_length=20, required=True, error_messages={'required': 'Ingrese su número de documento.'})
    correo = forms.EmailField(required=True, error_messages={'required': 'Ingrese su correo.', 'invalid': 'Ingrese un correo válido.'})
    telefono = forms.CharField(max_length=20, required=True, error_messages={'required': 'Ingrese su teléfono.'})
    password = forms.CharField(widget=forms.PasswordInput, required=True, error_messages={'required': 'Ingrese su contraseña.'})
    confirm_password = forms.CharField(widget=forms.PasswordInput, required=True, error_messages={'required': 'Confirme su contraseña.'})

    def clean_dni(self):
        dni = self.cleaned_data.get('dni')
        tipo = self.cleaned_data.get('tipo_documento')
        if not dni.isdigit():
            raise forms.ValidationError("El documento debe contener solo dígitos.")
        if tipo == 'DNI' and len(dni) != 8:
            raise forms.ValidationError("El DNI debe tener 8 dígitos.")
        elif tipo == 'RUC' and len(dni) != 11:
            raise forms.ValidationError("El RUC debe tener 11 dígitos.")
        elif tipo == 'CE' and len(dni) not in [9, 12]:
            raise forms.ValidationError("El Carnet de Extranjería debe tener 9 o 12 dígitos.")
        
        if User.objects.filter(username=dni).exists() or Cliente.objects.filter(dni=dni).exists():
            raise forms.ValidationError("El documento ya está registrado.")
        return dni

    def clean_correo(self):
        correo = self.cleaned_data.get('correo')
        if User.objects.filter(email=correo).exists():
            raise forms.ValidationError("El correo ya está registrado.")
        return correo

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Las contraseñas no coinciden.")
        return cleaned_data


class LoginForm(forms.Form):
    tipo_documento = forms.ChoiceField(
        choices=[
            ('',    'Seleccione su tipo de documento'),
            ('DNI', 'DNI'),
            ('CE',  'Carnet de Extranjería'),
            ('RUC', 'RUC'),
        ],
        required=True,
        error_messages={'required': 'Seleccione su tipo de documento.'}
    )
    username = forms.CharField(
        max_length=20,
        required=True,
        error_messages={'required': 'Ingrese su número de documento.'}
    )
    password = forms.CharField(
        widget=forms.PasswordInput,
        required=True,
        error_messages={'required': 'Ingrese su contraseña.'}
    )