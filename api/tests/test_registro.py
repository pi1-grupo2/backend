from django.contrib.auth.hashers import check_password
from rest_framework import status
from rest_framework.test import APITestCase

from api.models import Organizador

URL_REGISTRO = "/api/auth/registro/"
URL_LOGIN = "/api/auth/login/"
URL_SESION = "/api/auth/sesion/"
URL_ORGANIZADOR = "/api/organizador/"


def datos_validos(**cambios):
    datos = {"nombre": "Laura Gómez", "correo": "laura@correo.com", "password": "clave-segura-1"}
    datos.update(cambios)
    return datos


class RegistroExitosoTests(APITestCase):
    def test_crea_la_cuenta_y_responde_como_el_login(self):
        respuesta = self.client.post(URL_REGISTRO, datos_validos(), format="json")

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(set(respuesta.data), {"token", "expira_en", "organizador"})
        self.assertEqual(respuesta.data["organizador"]["correo"], "laura@correo.com")
        self.assertEqual(respuesta.data["organizador"]["nombre"], "Laura Gómez")

    def test_la_respuesta_no_incluye_la_contrasena(self):
        respuesta = self.client.post(URL_REGISTRO, datos_validos(), format="json")

        self.assertNotIn("password", respuesta.data)
        self.assertNotIn("password", respuesta.data["organizador"])

    def test_la_contrasena_se_guarda_con_hash(self):
        self.client.post(URL_REGISTRO, datos_validos(), format="json")

        organizador = Organizador.objects.get(correo="laura@correo.com")
        self.assertNotEqual(organizador.password, "clave-segura-1")
        self.assertTrue(check_password("clave-segura-1", organizador.password))

    def test_la_cuenta_nueva_tiene_limite_de_seis_horas(self):
        respuesta = self.client.post(URL_REGISTRO, datos_validos(), format="json")

        self.assertEqual(float(respuesta.data["organizador"]["limite_diario_horas"]), 6.0)

    def test_el_token_recibido_sirve_para_consultar_la_sesion(self):
        token = self.client.post(URL_REGISTRO, datos_validos(), format="json").data["token"]

        respuesta = self.client.get(URL_SESION, HTTP_AUTHORIZATION=f"Bearer {token}")

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["correo"], "laura@correo.com")

    def test_se_puede_iniciar_sesion_con_la_cuenta_creada(self):
        self.client.post(URL_REGISTRO, datos_validos(), format="json")

        respuesta = self.client.post(
            URL_LOGIN,
            {"correo": "laura@correo.com", "password": "clave-segura-1"},
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)

    def test_el_correo_se_guarda_en_minusculas_y_sin_espacios(self):
        respuesta = self.client.post(
            URL_REGISTRO,
            datos_validos(correo="  Laura@Correo.COM "),
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(respuesta.data["organizador"]["correo"], "laura@correo.com")

    def test_no_exige_sesion_previa(self):
        respuesta = self.client.post(
            URL_REGISTRO,
            datos_validos(),
            format="json",
            HTTP_AUTHORIZATION="Bearer token-que-no-existe",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)


class RegistroCorreoRepetidoTests(APITestCase):
    def test_un_correo_ya_registrado_responde_409(self):
        self.client.post(URL_REGISTRO, datos_validos(), format="json")

        respuesta = self.client.post(URL_REGISTRO, datos_validos(nombre="Otra persona"), format="json")

        self.assertEqual(respuesta.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(Organizador.objects.filter(correo="laura@correo.com").count(), 1)

    def test_el_mismo_correo_con_mayusculas_tambien_responde_409(self):
        self.client.post(URL_REGISTRO, datos_validos(), format="json")

        respuesta = self.client.post(
            URL_REGISTRO,
            datos_validos(correo="LAURA@correo.com"),
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_409_CONFLICT)

    def test_el_correo_de_la_cuenta_demo_no_se_puede_reutilizar(self):
        respuesta = self.client.post(
            URL_REGISTRO,
            datos_validos(correo="natalia@demo.com"),
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_409_CONFLICT)


class RegistroValidacionTests(APITestCase):
    def assert_rechaza(self, datos, campo, mensaje):
        antes = Organizador.objects.count()

        respuesta = self.client.post(URL_REGISTRO, datos, format="json")

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual([str(error) for error in respuesta.data[campo]], [mensaje])
        self.assertEqual(Organizador.objects.count(), antes)

    def test_sin_nombre(self):
        self.assert_rechaza(datos_validos(nombre="   "), "nombre", "Falta el nombre.")

    def test_sin_correo(self):
        datos = datos_validos()
        del datos["correo"]
        self.assert_rechaza(datos, "correo", "Falta el correo electrónico.")

    def test_correo_mal_formado(self):
        self.assert_rechaza(
            datos_validos(correo="laura-sin-arroba"),
            "correo",
            "El correo debe tener el formato nombre@correo.com.",
        )

    def test_sin_contrasena(self):
        self.assert_rechaza(datos_validos(password=""), "password", "Falta la contraseña.")

    def test_contrasena_de_siete_caracteres(self):
        self.assert_rechaza(
            datos_validos(password="1234567"),
            "password",
            "La contraseña debe tener al menos 8 caracteres.",
        )

    def test_contrasena_de_ocho_caracteres_se_acepta(self):
        respuesta = self.client.post(URL_REGISTRO, datos_validos(password="12345678"), format="json")

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)

    def test_cuerpo_vacio_informa_los_tres_campos(self):
        respuesta = self.client.post(URL_REGISTRO, {}, format="json")

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(set(respuesta.data), {"nombre", "correo", "password"})


class RegistroAislamientoTests(APITestCase):
    def test_cada_cuenta_guarda_su_propio_limite(self):
        token_a = self.client.post(URL_REGISTRO, datos_validos(), format="json").data["token"]
        token_b = self.client.post(
            URL_REGISTRO,
            datos_validos(correo="pedro@correo.com", nombre="Pedro"),
            format="json",
        ).data["token"]

        self.client.patch(
            URL_ORGANIZADOR,
            {"limite_diario_horas": 4},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {token_b}",
        )

        limite_a = self.client.get(URL_ORGANIZADOR, HTTP_AUTHORIZATION=f"Bearer {token_a}").data
        limite_b = self.client.get(URL_ORGANIZADOR, HTTP_AUTHORIZATION=f"Bearer {token_b}").data
        self.assertEqual(float(limite_a["limite_diario_horas"]), 6.0)
        self.assertEqual(float(limite_b["limite_diario_horas"]), 4.0)
