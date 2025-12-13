import io

import pytest
from flask import Flask

from app.modules.fakenodo.routes import fakenodo_bp


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
    """
    Prueba la creación de una deposición.
    """
    response = client.post(
        "/api/deposit/datasets",
        json={"metadata": {"title": "Mi primer dataset"}}
    )

    assert response.status_code == 201

    data = response.get_json()
    assert isinstance(data, dict)
    assert "id" in data
    assert isinstance(data["id"], int)


def test_upload_file_success(client):
    """
    Prueba la subida correcta de un archivo.
    """
    dep_id = 123456

    data = {
        "file": (io.BytesIO(b"contenido de prueba"), "modelo.car")
    }

    response = client.post(
        f"/api/deposit/datasets/{dep_id}/files",
        data=data,
        content_type="multipart/form-data",
    )

    assert response.status_code == 201

    response_data = response.get_json()
    assert response_data["key"] == "modelo.car"


def test_upload_file_no_file_attached(client):
    """
    Prueba la subida sin adjuntar archivo.
    """
    dep_id = 123456

    response = client.post(
        f"/api/deposit/datasets/{dep_id}/files",
        data={},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400

    data = response.get_json()
    assert "error" in data
    assert data["error"] == "No se encontró ningún archivo"


def test_publish_deposition(client):
    """
    Prueba la publicación de una deposición existente.
    """
    dep_id = 654321

    response = client.post(
        f"/api/deposit/datasets/{dep_id}/actions/publish"
    )

    assert response.status_code == 202

    data = response.get_json()
    assert data["id"] == dep_id
    assert data["state"] == "done"
    assert data["submitted"] is True
    assert data["doi"] == f"10.9999/fakenodo.{dep_id}.v1"


def test_full_deposition_flow(client):
    """
    Prueba el flujo completo:
    1. Crear deposición
    2. Subir archivo
    3. Publicar
    """
    # 1. Crear deposición
    create_resp = client.post(
        "/api/deposit/datasets",
        json={"metadata": {"title": "Dataset completo"}}
    )
    assert create_resp.status_code == 201

    dep_id = create_resp.get_json()["id"]

    # 2. Subir archivo
    upload_resp = client.post(
        f"/api/deposit/datasets/{dep_id}/files",
        data={
            "file": (io.BytesIO(b"datos del modelo"), "modelo_final.car")
        },
        content_type="multipart/form-data",
    )
    assert upload_resp.status_code == 201
    assert upload_resp.get_json()["key"] == "modelo_final.car"

    # 3. Publicar
    publish_resp = client.post(
        f"/api/deposit/datasets/{dep_id}/actions/publish"
    )
    assert publish_resp.status_code == 202

    publish_data = publish_resp.get_json()
    assert publish_data["id"] == dep_id
    assert "doi" in publish_data
