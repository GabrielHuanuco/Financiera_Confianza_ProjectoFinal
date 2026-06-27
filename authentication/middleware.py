from django.utils.deprecation import MiddlewareMixin
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.contrib.auth.models import AnonymousUser

class JWTCookieMiddleware(MiddlewareMixin):
    """
    Middleware que extrae el 'access_token' de las cookies y lo valida con SimpleJWT.
    Si el token es válido, establece request.user con el usuario autenticado.
    Esto permite que toda la aplicación funcione con JWT, satisfaciendo el requerimiento
    de usar JWT para el login tanto en el Core como en el Homebanking.
    """
    def process_request(self, request):
        token = request.COOKIES.get('access_token')
        if token:
            try:
                jwt_auth = JWTAuthentication()
                validated_token = jwt_auth.get_validated_token(token)
                user = jwt_auth.get_user(validated_token)
                
                # Si el JWT es válido, sobreescribimos el request.user
                # Esto asegura que si la sesión de Django falla o expira, 
                # el JWT mantendrá la autenticación activa.
                request.user = user
                # Agregamos una bandera para saber que fue autenticado por JWT
                request.jwt_authenticated = True
            except (InvalidToken, TokenError, Exception):
                # Si el token es inválido o expiró, no hacemos nada y dejamos
                # que los decoradores de Django (login_required) o nuestros
                # decoradores (role_required) redirijan al login.
                pass
