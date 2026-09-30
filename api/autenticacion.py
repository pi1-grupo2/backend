from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .models import Sesion

MENSAJE_CREDENCIALES = "Credenciales inválidas"


class TokenOrganizadorAuthentication(BaseAuthentication):
    def authenticate(self, request):
        encabezado = request.headers.get("Authorization", "")
        if not encabezado:
            return None
        esquema, _, token = encabezado.partition(" ")
        if esquema.lower() != "bearer" or not token:
            raise AuthenticationFailed(MENSAJE_CREDENCIALES)

        try:
            sesion = Sesion.objects.select_related("organizador").get(token=token)
        except Sesion.DoesNotExist:
            raise AuthenticationFailed(MENSAJE_CREDENCIALES)
        return (sesion.organizador, sesion)
