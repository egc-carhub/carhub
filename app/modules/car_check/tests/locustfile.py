import os
import random
import sys

from locust import HttpUser, between, task
from core.environment.host import get_host_for_locust_testing
from app import create_app
from app.modules.hubfile.models import Hubfile

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
sys.path.insert(0, project_root)


def get_all_file_ids():
    """
    Obtiene todos los ids de la base de datos.
    """
    app = create_app()
    
    with app.app_context():
        try:
            ids = [hubfile.id for hubfile in Hubfile.query.with_entities(Hubfile.id).all()]
            print(f"Obtenidos {len(ids)} IDs desde la base de datos para el test de carga.")
            return ids
        except Exception as e:
            print(f"Error al conectar con la base de datos para obtener los IDs: {e}")
            return []
        
        
AVAILABLE_FILES = get_all_file_ids()


class CarCheckUsers(HttpUser):
    """
    Define el comportamiento del usuario durante la prueba de carga
    """
    
    wait_time = between(4, 8)
    host = get_host_for_locust_testing()
    
    @task
    def check_car_file_set(self):
        """
        Simula la petición de un archivo .car en concreto
        Utiliza un ID aleatorio de los disponibles
        """
        
        if AVAILABLE_FILES:
            file_id = random.choice(AVAILABLE_FILES)
            self.client.get(f"/car_check/{file_id}", name="car_check/[file_id]")