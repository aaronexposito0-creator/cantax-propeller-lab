"""Independent dimensional identities and guarded public input schema (SI)."""
from __future__ import annotations
import json
import math
import re
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]

def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))

def finite_number(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("Expected finite numeric input: " + field)
    return float(value)

def validate_case(case):
    mapping = read(ROOT / "config/excel_mapping.json")
    for param in mapping["parameters"]:
        container = case[param["group"]] if param["group"] else case
        value = container[param["key"]]
        if param["min"] is not None:
            value = finite_number(value, param["key"])
            if not param["min"] <= value <= param["max"]:
                raise ValueError("Input outside demonstration bounds: " + param["key"])
    if int(case["geometry"]["blades"]) != case["geometry"]["blades"]:
        raise ValueError("Blade count must be an integer")
    materials = read(ROOT / "config/materials.json")["materials"]
    if case["material"] not in {m["id"] for m in materials}:
        raise ValueError("Unknown material ID")
    stations = case["radial_distribution"]
    if len(stations) != 8:
        raise ValueError("The Excel schema requires exactly eight radial stations")
    last = 0
    for station in stations:
        for key in ("r_R", "chord_weight", "pitch_factor", "thickness_factor", "skew_factor", "rake_factor"):
            value = finite_number(station[key], key)
            if value < 0 or (key in {"r_R", "chord_weight", "pitch_factor", "thickness_factor"} and value <= 0):
                raise ValueError("Invalid radial factor: " + key)
        if not last < station["r_R"] <= 1:
            raise ValueError("Radial coordinates must increase strictly within (0,1]")
        last = station["r_R"]
    if stations[-1]["r_R"] != 1 or stations[0]["r_R"] >= case["geometry"]["hub_ratio"]:
        raise ValueError("Last station must be r/R=1 and root must be inside hub")
    return case

def coefficients(rpm, advance_mps, diameter_m, density_kgm3, thrust_N, torque_Nm):
    rpm, advance_mps, diameter_m, density_kgm3, thrust_N, torque_Nm = [
        finite_number(v, name) for v, name in zip(
            (rpm, advance_mps, diameter_m, density_kgm3, thrust_N, torque_Nm),
            ("rpm", "advance", "diameter", "density", "thrust", "torque"))]
    if min(rpm, advance_mps, diameter_m, density_kgm3, thrust_N, torque_Nm) <= 0:
        raise ValueError("Only positive propulsive open-water cases are admitted")
    n = rpm / 60
    power = 2 * math.pi * n * torque_Nm
    return {"J": advance_mps / (n * diameter_m),
            "KT": thrust_N / (density_kgm3 * n**2 * diameter_m**4),
            "KQ": torque_Nm / (density_kgm3 * n**2 * diameter_m**5),
            "P_W": power, "eta0": thrust_N * advance_mps / power}

def ideal_disk_power(thrust_N, advance_mps, diameter_m, density_kgm3):
    """Ideal full-disk axial momentum lower bound; excludes swirl and losses."""
    area = math.pi * diameter_m**2 / 4
    induced = (math.sqrt(advance_mps**2 + 2*thrust_N/(density_kgm3*area)) - advance_mps)/2
    return thrust_N * (advance_mps + induced)

def verify_saved_case(directory):
    directory = Path(directory)
    case = validate_case(read(directory / "case.json"))
    hydro = read(directory / "hydro_results.json")
    baseline = hydro["baseline"]
    if hydro.get("status") != "passed" or baseline.get("valid_domain") is not True:
        raise ValueError("Example does not contain an admitted historical BEM result")
    checks = 0
    maximum_relative_error = 0
    for row in hydro["alternatives"]:
        if not row["valid_domain"]:
            continue
        expected = coefficients(row["rpm"], row["Va_mps"], row["D_m"],
                                case["operation"]["water_density_kgm3"], row["T_N"], row["Q_Nm"])
        for key, value in expected.items():
            actual = finite_number(row[key], key)
            error = abs(actual-value)/max(abs(value), 1e-12)
            maximum_relative_error = max(maximum_relative_error, error)
            if error > 1e-9:
                raise ValueError(f"Saved {row['id']} disagrees with independent {key} identity: {error}")
            checks += 1
        if not 0 < expected["eta0"] < 1:
            raise ValueError("Saved efficiency is outside the propulsive interval")
    lower = ideal_disk_power(baseline["T_N"], baseline["Va_mps"], baseline["D_m"], case["operation"]["water_density_kgm3"])
    if baseline["P_W"] < lower*(1-1e-3):
        raise ValueError("Saved power violates the ideal full-disk momentum bound")
    cad = read(directory / "cad_results.json")
    if cad.get("status") != "verified":
        raise ValueError("Historical CAD status is not verified")
    for model in cad["models"]:
        if not (model.get("status") == "verified" and model["valid"] and model["closed"] and model["solids"] == 1 and model["volume_m3"] > 0):
            raise ValueError("Historical CAD solid check failed")
    return {"status": "PASS", "numeric_identity_checks": checks,
            "maximum_relative_error": maximum_relative_error, "ideal_disk_minimum_power_W": lower,
            "historical_cad_records": len(cad["models"]),
            "scope": "Current consistency check of saved numerical records; native engines were not rerun; no physical validation"}

def preflight_xlsx(path):
    """Reject active/external content before handing any file to Excel."""
    if Path(path).suffix.lower() != ".xlsx":
        raise ValueError("Only macro-free .xlsx is allowed")
    with ZipFile(path) as archive:
        for name in archive.namelist():
            low = name.lower()
            if any(part in low for part in ("vbaproject.bin", "xl/externallinks/", "xl/querytables/", "xl/macrosheets/", "xl/connections.xml")):
                raise ValueError("Workbook contains active or external content")
            if low.startswith("xl/worksheets/") and low.endswith(".xml"):
                # Recalc must never cause a network fetch or execute DDE commands.
                root = ElementTree.fromstring(archive.read(name))
                for node in root.iter():
                    if node.tag.rsplit('}', 1)[-1] != 'f':
                        continue
                    formula = node.text or ''
                    if (re.search(r'(?i)(WEBSERVICE|RTD|STOCKHISTORY|IMAGE|CUBEVALUE|CUBESET|CUBEMEMBER|HYPERLINK|DDE)\s*\(', formula)
                            or any(symbol in formula for symbol in ('|','[',']'))):
                        raise ValueError("Workbook contains an external/active formula")
    return True
