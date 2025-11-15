import logging

from flask import jsonify

from app.modules.car_check import car_check_bp
from app.modules.car_check.check_car import CarFileChecker
from app.modules.hubfile.services import HubfileService

logger = logging.getLogger(__name__)


@car_check_bp.route("/car_check/<int:file_id>", methods=["GET"])
def check_car(file_id):
    """
    Valida un archivo .car
    Comprueba si el archivo CAR es válido y devuelve los errores si los hay.
    """
    try:
        hubFile = HubfileService().get_by_id(file_id)
        if not hubFile:
            return jsonify({"error": "Hubfile no encontrado"}), 404

        file_path = hubFile.get_path()

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                car_content = f.read()

        except Exception as e:
            logger.error(f"Error al leer el archivo CAR: {e}")
            return jsonify({"error": "No se pudo leer el archivo CAR"}), 500

        parse = CarFileChecker(car_content)

        if not parse.is_valid():
            logger.info(f"Archivo CAR inválido: {file_path}, errores: {parse.get_errors()}")
            return jsonify({"valid": False, "errors": parse.get_errors()}), 400

        return jsonify({"valid": True, "parsed_data": parse.get_parsed_data()})

    except Exception as e:

        logger.error(f"Error al procesar el archivo CAR: {e}")
        return jsonify({f" Error al comprobar el archivo con file_id {file_id}: {e}"}), 500
