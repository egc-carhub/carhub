import pytest
from unittest.mock import MagicMock
from app import db
from app.modules.fakenodo.models import Deposition
from app.modules.fakenodo.services import FakenodoService


def test_sample_assertion(test_client):
    """
    Sample test to verify that the test framework and environment are working correctly.
    It does not communicate with the Flask application; it only performs a simple assertion to
    confirm that the tests in this module can be executed.
    """
    greeting = "Hello, World!"
    assert greeting == "Hello, World!", "The greeting does not coincide with 'Hello, World!'"



@pytest.fixture(scope='module')
def test_client(test_client):
    """
    Prepara el entorno de pruebas con datos iniciales (semilla).
    """
    with test_client.application.app_context():
        # Crear una deposición de prueba inicial para los tests de búsqueda
        # Nota: Usamos dep_metadata directo porque estamos tocando el modelo, no el servicio
        seed_deposition = Deposition(
            dep_metadata={"title": "Seed Data", "upload_type": "dataset"},
            status="published",
            doi="10.1000/xyz123"
        )
        db.session.add(seed_deposition)
        db.session.commit()

    yield test_client


def test_create_deposition_success(test_client):
    """
    Prueba: Crear una deposición correctamente a través del Servicio.
    """
    with test_client.application.app_context():
        # 1. Instanciamos el servicio (IMPORTANTE: es una clase)
        service = FakenodoService()

        # 2. Mockeamos el objeto de entrada (DSMetaData)
        # Tu servicio espera un objeto con atributos .title, .publication_type.value, etc.
        # No espera un diccionario simple.
        mock_ds_metadata = MagicMock()
        mock_ds_metadata.title = "Test Deposition from Mock"
        mock_ds_metadata.description = "Created from unit test with MagicMock"
        # Simulamos que es un dataset (publication_type.value == 'none')
        mock_ds_metadata.publication_type.value = "none" 
        mock_ds_metadata.authors = [] # Lista vacía de autores
        mock_ds_metadata.tags = "tag1, tag2"

        # 3. Ejecución: Llamada al servicio
        # El argumento en tu services.py se llama 'ds_meta_data', no 'dep_metadata'
        response = service.create_new_deposition(ds_meta_data=mock_ds_metadata)

        # 4. Verificación
        # Tu servicio devuelve un diccionario, no un objeto Deposition
        assert response is not None
        assert "id" in response
        assert response['message'] == "Deposition succesfully created in Fakenodo"
        # Verificamos que los datos dentro del JSON coincidan con el Mock
        assert response['metadata']['title'] == "Test Deposition from Mock"
        assert response['metadata']['upload_type'] == "dataset"


def test_retrieve_deposition_by_doi(test_client):
    """
    Prueba: Buscar una deposición existente por su DOI.
    Usa el método del servicio get_doi o get_deposition.
    """
    with test_client.application.app_context():
        service = FakenodoService()
        
        # Primero recuperamos el ID de la deposición semilla (creada en el fixture)
        seed_dep = Deposition.query.filter_by(doi="10.1000/xyz123").first()
        assert seed_dep is not None, "La semilla no se creó correctamente"

        # Probamos el método get_deposition del servicio
        response = service.get_deposition(deposition_id=seed_dep.id)
        
        assert response['doi'] == "10.1000/xyz123"
        assert response['status'] == "published"


def test_deposition_metadata_integrity(test_client):
    """
    Prueba: Verificar que el modelo Deposition guarda estructuras JSON correctamente.
    Esta prueba es más de integración con la BD.
    """
    with test_client.application.app_context():
        complex_metadata = {
            "creators": [{"name": "Doe, John", "affiliation": "UVLHub"}],
            "keywords": ["testing", "unit", "flask"]
        }
        
        # Guardamos directamente usando el modelo
        dep = Deposition(
            dep_metadata=complex_metadata,
            status="draft",
            doi="temp-doi-999"
        )
        db.session.add(dep)
        db.session.commit()

        # Recuperar y validar estructura anidada
        saved_dep = Deposition.query.filter_by(doi="temp-doi-999").first()
        assert saved_dep.dep_metadata['creators'][0]['name'] == "Doe, John"
        assert "testing" in saved_dep.dep_metadata['keywords']