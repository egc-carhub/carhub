from core.blueprints.base_blueprint import BaseBlueprint

# Blueprint for notifications module
notifications_bp = BaseBlueprint("notifications", __name__, template_folder="templates")

# Import routes to register blueprint when module manager loads this module
from app.modules.notifications import routes  # noqa: F401, E402
