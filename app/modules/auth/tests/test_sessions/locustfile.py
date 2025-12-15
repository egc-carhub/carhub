import re
import uuid

from locust import HttpUser, between, task

from core.environment.host import get_host_for_locust_testing


class AuthenticatedUser(HttpUser):
    # Simula un tiempo de espera entre acciones de 1 a 3 segundos
    wait_time = between(1, 3)

    def on_start(self):
        """
        Al iniciar cada usuario simulado:
        1. Genera credenciales únicas.
        2. Realiza el flujo de Registro (Signup) para obtener una sesión válida.
        """
        self.email = f"loadtest_{uuid.uuid4()}@example.com"
        self.password = "password123"
        self.name = "Load"
        self.surname = "Tester"

        self.signup()

    def extract_csrf_token(self, response):
        """Extrae el token CSRF del HTML usando regex."""
        # Busca un input tipo hidden con name="csrf_token" y captura su value
        # Pattern match for standard WTForms rendering
        # Accepts 'name="csrf_token" ... value="..."'
        match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', response.text)
        if match:
            return match.group(1)
        # Fallback for value first
        match = re.search(r'value="([^"]+)"[^>]*name="csrf_token"', response.text)
        if match:
            return match.group(1)
        return None

    def signup(self):
        # 1. GET al formulario de signup para obtener el CSRF token
        # URL CORRECTA: /signup/ (sin prefijo /auth)
        response = self.client.get("/signup/")
        csrf_token = self.extract_csrf_token(response)

        if not csrf_token:
            print(f"[{self.email}] Error: No se pudo obtener CSRF token en signup")
            return

        # 2. POST con los datos de registro
        # Nota: El registro exitoso loguea automáticamente al usuario
        res = self.client.post(
            "/signup/",
            data={
                "csrf_token": csrf_token,
                "name": self.name,
                "surname": self.surname,
                "email": self.email,
                "password": self.password,
                "submit": "Submit",
            },
        )

        if res.status_code != 200:
            # Si redirige (302) es éxito, requests/locust sigue redirects por defecto y devuelve 200 del destino
            # Si devuelve otro código, es error.
            print(f"[{self.email}] Error en signup: {res.status_code}")

    @task(3)
    def list_sessions(self):
        """Carga la lista de sesiones activas (Endpoint frecuente)."""
        self.client.get("/sessions")

    @task(1)
    def delete_other_sessions(self):
        """Cierra otras sesiones (Endpoint menos frecuente)."""
        # Para peticiones que no son formularios (como DELETE via AJAX),
        # Flask-WTF espera el token en la cabecera X-CSRFToken.
        # Generalmente, el token está disponible en la cookie 'csrf_token'.

        csrf_token = self.client.cookies.get("csrf_token")
        headers = {}
        if csrf_token:
            headers["X-CSRFToken"] = csrf_token

        self.client.delete("/sessions", headers=headers)

    host = get_host_for_locust_testing()
    min_wait = 5000
    max_wait = 9000
