import re
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
import os


CANONICAL_KEYS = {
    "make": "company",
    "company": "company",
    "model": "model",
    "engine": "engine",
    "cc": "cc",
    "hp": "hp",
    "max speed": "max_speed_kmh",
    "maxspeed": "max_speed_kmh",
    "top speed": "max_speed_kmh",
    "acceleration(0-100)": "acceleration_sec",
    "acceleration": "acceleration_sec",
    "0-100": "acceleration_sec",
    "price": "price",
    "cost": "price",
    "seats": "seats",
    "year": "year",
    "batterry capacity": "battery_capacity",
    "battery capacity": "battery_capacity",
    "fuel": "fuel",
}


class CarFileChecker:
    """Parses and validates a simple key:value car spec file used in `car_examples`.

    Usage:
        checker = CarFileChecker(text)
        valid = checker.is_valid()
        data = checker.get_parsed_data()
        errors = checker.get_errors()
    """

    def __init__(self, text_content: str):
        self.text = text_content or ""
        self.parsed_data: Dict[str, Any] = {
            "company": None,
            "model": None,
            "engine": None,
            "cc": None,
            "hp": None,
            "max_speed_kmh": None,
            "acceleration_sec": None,
            "price": None,
            "seats": None,
            "year": None,
            "battery_capacity": None,
            "fuel": None,
            "raw": {},
        }
        self.errors: List[str] = []
        self._parse()
        self._validate()

    def _parse(self):
        lines = self.text.strip().splitlines()
        if not lines:
            self.errors.append("El archivo está vacío.")
            return

        kv_regex = re.compile(r"^\s*([^:]+):\s*(.*)$")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            m = kv_regex.match(line)
            if not m:
                # allow dash-list items or ignore
                continue
            key_raw = m.group(1).strip()
            value_raw = m.group(2).strip()
            key_norm = key_raw.lower()
            canon = CANONICAL_KEYS.get(key_norm)
            # store raw
            self.parsed_data["raw"][key_raw] = value_raw
            if canon:
                # delegate parsing for numeric fields
                if canon == "cc":
                    self.parsed_data[canon] = self._parse_int(value_raw, field="cc")
                elif canon == "hp":
                    self.parsed_data[canon] = self._parse_int(value_raw, field="hp")
                elif canon == "max_speed_kmh":
                    self.parsed_data[canon] = self._parse_speed(value_raw)
                elif canon == "acceleration_sec":
                    self.parsed_data[canon] = self._parse_acceleration(value_raw)
                elif canon == "price":
                    self.parsed_data[canon] = self._parse_price(value_raw)
                elif canon == "seats":
                    self.parsed_data[canon] = self._parse_int(value_raw, field="seats")
                elif canon == "year":
                    self.parsed_data[canon] = self._parse_int(value_raw, field="year")
                elif canon == "weight_kg":
                    self.parsed_data[canon] = self._parse_float(value_raw, field="weight_kg")
                else:
                    # text fields
                    self.parsed_data[canon] = value_raw
            else:
                # unknown key: keep as note in raw
                pass

    def _parse_int(self, s: str, field: str) -> Optional[int]:
        # Accept textual values (ranges, approximations). Return int when the
        # field clearly contains a single integer, otherwise return the
        # original string so callers can keep the raw text and we don't emit
        # an error.
        s_strip = (s or "").strip()
        if s_strip == "":
            return None
        # if looks like a range or contains letters or tildes, keep raw
        if re.search(r"[-~–/]|[a-zA-Z]", s_strip):
            return s_strip
        cleaned = re.sub(r"[^0-9+-]", "", s_strip)
        if cleaned == "":
            return s_strip
        try:
            return int(cleaned)
        except Exception:
            return s_strip

    def _parse_float(self, s: str, field: str) -> Optional[float]:
        try:
            cleaned = re.sub(r"[^0-9+\-.]", "", s)
            if cleaned == "":
                self.errors.append(f"Campo {field} vacío o no numérico: '{s}'")
                return None
            return float(cleaned)
        except Exception:
            self.errors.append(f"No se pudo parsear float para {field}: '{s}'")
            return None

    def _parse_speed(self, s: str) -> Optional[float]:
        # expect values like '250 km/h' or '250km/h' or '250'
        s_strip = (s or "").strip()
        if s_strip == "":
            return None
        # if range/approx or text, keep raw string
        if re.search(r"[-~–/]|[a-zA-Z]", s_strip):
            return s_strip
        cleaned = re.sub(r"[^0-9+\-.]", "", s_strip)
        if cleaned == "":
            return s_strip
        try:
            return float(cleaned)
        except Exception:
            return s_strip

    def _parse_acceleration(self, s: str) -> Optional[float]:
        # expect '4.1 sec' or '4.1s' or '4.1'
        s_strip = (s or "").strip()
        if s_strip == "":
            return None
        if re.search(r"[-~–/]|[a-zA-Z]", s_strip):
            return s_strip
        cleaned = re.sub(r"[^0-9+\-.]", "", s_strip)
        if cleaned == "":
            return s_strip
        try:
            return float(cleaned)
        except Exception:
            return s_strip

    def _parse_price(self, s: str) -> Optional[float]:
        # remove currency symbols and commas
        s_strip = (s or "").strip()
        if s_strip == "":
            return None
        # accept textual price (currency, ranges)
        if re.search(r"[-~–/]|[a-zA-Z]", s_strip):
            # try to extract a single numeric value if present
            cleaned = re.sub(r"[,€$£\s]", "", s_strip)
            cleaned = re.sub(r"[^0-9+\-.]", "", cleaned)
            if cleaned == "":
                return s_strip
            try:
                return float(cleaned)
            except Exception:
                return s_strip
        cleaned = re.sub(r"[,€$£\s]", "", s_strip)
        cleaned = re.sub(r"[^0-9+\-.]", "", cleaned)
        if cleaned == "":
            return s_strip
        try:
            return float(cleaned)
        except Exception:
            return s_strip

    def _validate(self):
        # required fields
        if not self.parsed_data.get("company"):
            self.errors.append("Falta 'Company' (marca).")
        if not self.parsed_data.get("model"):
            self.errors.append("Falta 'Model'.")
        if not self.parsed_data.get("engine"):
            self.errors.append("Falta 'Engine'.")

        # numeric validations
        # Numeric validations only when parsed values are numbers. If the
        # parsed field contains a textual value (ranges, approximations), we
        # accept it and do not add a validation error.
        cc = self.parsed_data.get("cc")
        if isinstance(cc, int):
            if not (50 <= cc <= 10000):
                self.errors.append(f"Valor de CC improbable: {cc}")

        hp = self.parsed_data.get("hp")
        if isinstance(hp, int):
            if not (1 <= hp <= 3000):
                self.errors.append(f"Valor de HP improbable: {hp}")

        seats = self.parsed_data.get("seats")
        if isinstance(seats, int):
            if not (1 <= seats <= 9):
                self.errors.append(f"Valor de Seats improbable: {seats}")

        year = self.parsed_data.get("year")
        if isinstance(year, int):
            current_year = datetime.utcnow().year
            if not (1886 <= year <= current_year + 1):
                self.errors.append(f"Valor de Year improbable: {year}")

        max_speed = self.parsed_data.get("max_speed_kmh")
        if isinstance(max_speed, (int, float)):
            if not (1 <= float(max_speed) <= 500):
                self.errors.append(f"Valor de Max Speed improbable: {max_speed}")

        accel = self.parsed_data.get("acceleration_sec")
        if isinstance(accel, (int, float)):
            if not (0.5 <= float(accel) <= 60):
                self.errors.append(f"Valor de Acceleration improbable: {accel}")

    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def get_parsed_data(self) -> Dict[str, Any]:
        return self.parsed_data

    def get_errors(self) -> List[str]:
        return self.errors


def process_car_examples_dir(dir_path: str, output_json: Optional[str] = None) -> List[Dict[str, Any]]:
    """Process all .car files in a directory, return list of results and optionally write JSON."""
    results = []
    if not os.path.isdir(dir_path):
        raise FileNotFoundError(f"Directorio no encontrado: {dir_path}")
    for fname in sorted(os.listdir(dir_path)):
        if not fname.lower().endswith(".car"):
            continue
        fpath = os.path.join(dir_path, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            results.append({"file": fname, "error": str(e)})
            continue
        checker = CarFileChecker(text)
        results.append({
            "file": fname,
            "valid": checker.is_valid(),
            "data": checker.get_parsed_data(),
            "errors": checker.get_errors(),
        })
    if output_json:
        try:
            with open(output_json, "w", encoding="utf-8") as out:
                json.dump(results, out, ensure_ascii=False, indent=2)
        except Exception as e:
            # writing JSON failed; include a small result entry
            results.append({"file": "<output>", "error": f"Failed writing output: {e}"})
    return results
