from core.blueprints.base_blueprint import BaseBlueprint

# Crear el Blueprint principal del módulo de autenticación
auth_bp = BaseBlueprint("auth", __name__, template_folder="templates")

# Importar controladores SOLO una vez
from app.modules.auth.controllers import *  # noqa: E402,F401,F403
