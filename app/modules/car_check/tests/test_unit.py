import json
from importlib.machinery import SourceFileLoader
from unittest.mock import patch, MagicMock, mock_open
import os


def load_checker():
    mod_path = os.path.join(os.path.dirname(__file__), '..', 'check_car.py')
    return SourceFileLoader('check_car', mod_path).load_module()


def test_parse_simple_values():
    mod = load_checker()
    text = (
        "Company: TestCo\n"
        "Model: Speedster\n"
        "Engine: I4\n"
        "CC: 1998\n"
        "HP: 250\n"
        "Max Speed: 300 km/h\n"
        "Acceleration(0-100): 3.5 sec\n"
        "Price: $120000\n"
        "Seats: 2\n"
    )
    checker = mod.CarFileChecker(text)
    assert checker.is_valid()
    data = checker.get_parsed_data()
    assert data['company'] == 'TestCo'
    assert data['model'] == 'Speedster'
    assert data['engine'] == 'I4'
    assert isinstance(data['cc'], int) and data['cc'] == 1998
    assert isinstance(data['hp'], int) and data['hp'] == 250
    assert data['max_speed_kmh'] == '300 km/h'
    assert data['acceleration_sec'] == '3.5 sec'
    assert isinstance(data['price'], float) and data['price'] == 120000.0
    assert isinstance(data['seats'], int) and data['seats'] == 2


def test_parse_ranges_and_approx_values():
    mod = load_checker()
    text = (
        "Company: RangeCo\n"
        "Model: Flex\n"
        "Engine: V6\n"
        "CC: 3000\n"
        "HP: 110-320\n"
        "Max Speed: ~330-360 km/h\n"
        "Acceleration(0-100): ~2.5-3.0 sec\n"
    )
    checker = mod.CarFileChecker(text)
    assert checker.is_valid()
    data = checker.get_parsed_data()
    assert data['hp'] == '110-320'
    assert data['max_speed_kmh'] == '~330-360 km/h'
    assert data['acceleration_sec'] == '~2.5-3.0 sec'


def test_missing_required_fields():
    mod = load_checker()
    text = "Model: NoMake\nEngine: I4\n"
    checker = mod.CarFileChecker(text)
    assert not checker.is_valid()
    errs = checker.get_errors()
    assert any('Company' in e or 'marca' in e for e in errs)


def test_battery_and_fuel_and_price_parsing(tmp_path):
    mod = load_checker()
    text = (
        "Company: ElecCo\n"
        "Model: ECar\n"
        "Engine: Electric\n"
        "Batterry capacity: 40-50 kWh\n"
        "Fuel: Electric\n"
        "Price: €35,000\n"
    )
    checker = mod.CarFileChecker(text)
    assert checker.is_valid()
    data = checker.get_parsed_data()
    assert data['battery_capacity'] == '40-50 kWh'
    assert data['fuel'] == 'Electric'
    assert data['price'] == 35000.0


def test_process_car_examples_dir_and_output(tmp_path):
    mod = load_checker()
    d = tmp_path / 'examples'
    d.mkdir()
    (d / 'a.car').write_text('Company: A\nModel: A1\nEngine: I4\nCC: 1000\n')
    (d / 'b.car').write_text('Company: B\nModel: B1\nEngine: I4\nHP: 150\n')
    out_json = tmp_path / 'out.json'
    results = mod.process_car_examples_dir(str(d), output_json=str(out_json))
    assert len(results) == 2
    assert out_json.exists()
    loaded = json.loads(out_json.read_text(encoding='utf-8'))
    assert isinstance(loaded, list) and len(loaded) == 2


def test_empty_file():
    mod = load_checker()
    checker = mod.CarFileChecker("")
    assert not checker.is_valid()
    errs = checker.get_errors()
    assert any('vacío' in e.lower() or 'empty' in e.lower() or 'archivo' in e.lower() for e in errs)


@patch("app.modules.car_check.routes.HubfileService")
def test_check_car_valid_file(mock_hubfile_service, test_client):
    mock_hubfile = MagicMock()
    mock_hubfile.get_path.return_value = "dummy/path/car.car"
    mock_hubfile_service.return_value.get_by_id.return_value = mock_hubfile

    valid_content = (
        "Company: TestCo\n"
        "Model: Speedster\n"
        "Engine: I4\n"
        "CC: 1998\n"
        "HP: 250\n"
    )

    m_open = mock_open(read_data=valid_content)
    with patch("builtins.open", m_open):
        response = test_client.get("/car_check/1")

    assert response.status_code == 200
    data = response.get_json() if hasattr(response, 'get_json') else json.loads(response.data)
    assert data["valid"] is True
    assert data["parsed_data"]["company"] == "TestCo"


@patch("app.modules.car_check.routes.HubfileService")
def test_check_car_invalid_file(mock_hubfile_service, test_client):
    mock_hubfile = MagicMock()
    mock_hubfile.get_path.return_value = "dummy/path/car.car"
    mock_hubfile_service.return_value.get_by_id.return_value = mock_hubfile

    invalid_content = "Model: NoMake\nEngine: I4\n"

    m_open = mock_open(read_data=invalid_content)
    with patch("builtins.open", m_open):
        response = test_client.get("/car_check/1")

    assert response.status_code == 400
    data = response.get_json() if hasattr(response, 'get_json') else json.loads(response.data)
    assert data["valid"] is False
    assert isinstance(data.get("errors"), list) and len(data["errors"]) >= 1


@patch("app.modules.car_check.routes.HubfileService")
def test_check_car_file_not_found(mock_hubfile_service, test_client):
    mock_hubfile_service.return_value.get_by_id.return_value = None
    response = test_client.get("/car_check/999")
    assert response.status_code == 404
    data = response.get_json() if hasattr(response, 'get_json') else json.loads(response.data)
    assert data.get("error") == "Hubfile no encontrado"
