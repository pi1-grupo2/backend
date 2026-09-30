import secrets
from datetime import timedelta

from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission

from .models import Sesion

MENSAJE_CREDENCIALES = "Credenciales inválidas"
MENSAJE_SESION = "Sesión inválida o expirada"
DURACION_SESION = timedelta(hours=8)


def crear_sesion(organizador):
    return Sesion.objects.create(
        organizador=organizador,
        token=secrets.token_urlsafe(32),
        expira_en=timezone.now() + DURACION_SESION,
    )


class TokenOrganizadorAuthentication(BaseAuthentication):
    def authenticate(self, request):
        encabezado = request.headers.get("Authorization", "")
        if not encabezado:
            return None
        esquema, _, token = encabezado.partition(" ")
        if esquema.lower() != "bearer" or not token:
            raise AuthenticationFailed(MENSAJE_SESION)

        try:
            sesion = Sesion.objects.select_related("organizador").get(token=token)
        except Sesion.DoesNotExist:
            raise AuthenticationFailed(MENSAJE_SESION)

        if sesion.expira_en <= timezone.now():
            sesion.delete()
            raise AuthenticationFailed(MENSAJE_SESION)
        return (sesion.organizador, sesion)

    def authenticate_header(self, request):
        return "Bearer"


class SesionRequerida(BasePermission):
    def has_permission(self, request, view):
        usuario = getattr(request, "user", None)
        if usuario is not None and getattr(usuario, "is_authenticated", False):
            return True
        raise AuthenticationFailed(MENSAJE_SESION)
