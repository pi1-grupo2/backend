from drf_spectacular.extensions import OpenApiAuthenticationExtension


class TokenOrganizadorEsquema(OpenApiAuthenticationExtension):
    """Le explica a drf-spectacular que la API usa un token Bearer propio."""

    target_class = "api.autenticacion.TokenOrganizadorAuthentication"
    name = "tokenOrganizador"

    def get_security_definition(self, auto_schema):
        return {"type": "http", "scheme": "bearer"}