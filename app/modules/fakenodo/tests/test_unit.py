import io

import pytest
from flask import Flask
from werkzeug.datastructures import FileStorage

from app.modules.fakenodo.routes import fakenodo_bp, upload_file

# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------


@pytest.fixture
def app():
    """
    Crea una instancia de la app Flask para pruebas.
    """
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(fakenodo_bp, url_prefix="/api")
    return app


@pytest.fixture
def client(app):
    """
    Cliente de pruebas de Flask.
    """
    return app.test_client()


# ---------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------


def test_create_deposition(client):
    response = client.post("/api/deposit/datasets", json={"metadata": {"title": "Mi primer dataset"}})

    assert response.status_code == 201

    data = response.get_json()
    assert isinstance(data, dict)
    assert "id" in data
    assert isinstance(data["id"], int)


def test_upload_file(app):
    dep_id = 123456

    fake_file_content = b"Este es el contenido del car-file"
    fake_filename = "modelo.car"

    fake_file_storage = FileStorage(
        stream=io.BytesIO(fake_file_content), filename=fake_filename, name="file", content_type="text/plain"
    )

    files_arg = {"file": fake_file_storage}

    with app.test_request_context():
        response_data, status_code = upload_file(dep_id, data={}, files=files_arg)

    assert status_code == 201
    assert response_data["key"] == "file"


def test_upload_file_no_file_attached(app):
    dep_id = 123456

    files_arg = {}

    with app.test_request_context():
        response_data, status_code = upload_file(dep_id, data={}, files=files_arg)

    assert status_code == 400
    assert response_data.get_json()["error"] == "No se encontró ningún archivo"


def test_publish_deposition(client):
    dep_id = 654321

    response = client.post(f"/api/deposit/datasets/{dep_id}/actions/publish")

    assert response.status_code == 202

    data = response.get_json()
    assert data["id"] == dep_id
    assert data["state"] == "done"
    assert data["submitted"] is True
    assert data["doi"] == f"10.9999/fakenodo.{dep_id}.v1"


def test_full_deposition_flow(app):
    """
    Prueba el flujo completo:
    1. Crear deposición
    2. Subir archivo
    3. Publicar
    """

    # 1. Crear deposición - manteniendo el cliente para esta parte
    with app.test_client() as client:
        create_resp = client.post("/api/deposit/datasets", json={"metadata": {"title": "Dataset completo"}})
        assert create_resp.status_code == 201
        dep_id = create_resp.get_json()["id"]

    # 2. Subir archivo - llamando directamente a la función como en el primer test
    fake_file_content = b"datos del modelo"
    fake_filename = "modelo_final.car"

    fake_file_storage = FileStorage(
        stream=io.BytesIO(fake_file_content), filename=fake_filename, name="file", content_type="text/plain"
    )

    files_arg = {"file": fake_file_storage}

    with app.test_request_context():
        response_data, status_code = upload_file(dep_id, data={}, files=files_arg)

    assert status_code == 201
    assert response_data["key"] == "file"  # Nota: usa .name, no .filename

    # 3. Publicar - usando el cliente HTTP
    with app.test_client() as client:
        publish_resp = client.post(f"/api/deposit/datasets/{dep_id}/actions/publish")
        assert publish_resp.status_code == 202

        publish_data = publish_resp.get_json()
        assert publish_data["id"] == dep_id
        assert "doi" in publish_data
