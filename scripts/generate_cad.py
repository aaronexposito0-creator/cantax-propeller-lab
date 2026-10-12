"""Generate real propeller solids using the installed FreeCAD embedded Python.

Input: CANTAX_RUN_DIR/case.json and family.json. Output never overwrites a run.
Dimensions used by OCC/FreeCAD are mm; public JSON quantities are SI.
"""
import json
import math
import os
from pathlib import Path
import sys
import time
import traceback

import FreeCAD as App
import Part
import Mesh


def dump(path, payload):
    Path(path).write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")


def trapezoid(points):
    return sum((b[0] - a[0]) * (a[1] + b[1]) / 2.0 for a, b in zip(points, points[1:]))


def linear_station(stations, x, field):
    if x <= stations[0]["r_R"]:
        return stations[0][field]
    for a, b in zip(stations, stations[1:]):
        if x <= b["r_R"]:
            q = (x - a["r_R"]) / (b["r_R"] - a["r_R"])
            return (1 - q) * a[field] + q * b[field]
    return stations[-1][field]


def validate(geometry, stations):
    for name, value in geometry.items():
        if not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("Geometry field is not a finite number: " + name)
    D = geometry["diameter_m"]
    B = geometry["blades"]
    if not (0.01 <= D <= 10 and int(B) == B and 3 <= B <= 7):
        raise ValueError("CAD demonstration range D=.01..10 m, B=3..7 integer")
    if not (0.4 <= geometry["pitch_ratio"] <= 1.5):
        raise ValueError("CAD demonstration P/D range .4..1.5")
    if not (0.3 <= geometry["expanded_area_ratio"] <= 0.9):
        raise ValueError("CAD demonstration EAR range .3.. .9")
    if not (0.02 <= geometry["thickness_ratio"] <= 0.18):
        raise ValueError("CAD demonstration t/c range .02.. .18")
    if abs(geometry["skew_deg"]) > 30 or abs(geometry["rake_ratio"]) > .1:
        raise ValueError("CAD demonstration abs(skew)<=30 deg, abs(rake/D)<=.1")
    if not (0.12 <= geometry["hub_ratio"] <= .3):
        raise ValueError("CAD demonstration hub/D .12.. .3")
    if not (0 < stations[0]["r_R"] < geometry["hub_ratio"] and stations[-1]["r_R"] == 1):
        raise ValueError("Root must be inside hub radius and last section must be r/R=1")
    for i, station in enumerate(stations):
        if i and station["r_R"] <= stations[i - 1]["r_R"]:
            raise ValueError("Radial stations must increase strictly")
        for field in ["r_R", "chord_weight", "pitch_factor", "thickness_factor", "skew_factor", "rake_factor"]:
            if not math.isfinite(station[field]):
                raise ValueError("Nonfinite radial input " + field)
        if station["chord_weight"] <= 0 or station["pitch_factor"] <= 0 or station["thickness_factor"] <= 0:
            raise ValueError("Positive chord/pitch/thickness radial factors required")


def airfoil_wire(radius_mm, chord_mm, beta, thickness_ratio, skew_mm, rake_mm):
    # Exact polynomial representation: parameter t=sqrt(x), x=t^2.
    # No sampled interpolation; each edge is a degree-8 Bezier polynomial.
    # -.1036 is OUR algebraic closed-TE change, not published NACA -.1015.
    def poles(side):
        u = [-.25*chord_mm, 0, chord_mm, 0, 0, 0, 0, 0, 0]
        v = [0, .2969, -.1260, 0, -.3516, 0, .2843, 0, -.1036]
        v = [side*5*thickness_ratio*chord_mm*q for q in v]
        power = [App.Vector(radius_mm if k == 0 else 0,
                            (skew_mm if k == 0 else 0)+u[k]*math.cos(beta)-v[k]*math.sin(beta),
                            (rake_mm if k == 0 else 0)+u[k]*math.sin(beta)+v[k]*math.cos(beta))
                 for k in range(9)]
        return [sum((power[k]*(math.comb(i,k)/math.comb(8,k)) for k in range(i+1)), App.Vector()) for i in range(9)]
    upper = poles(1)
    lower = list(reversed(poles(-1)))
    lower[0] = upper[-1]
    lower[-1] = upper[0]
    top = Part.BezierCurve()
    bottom = Part.BezierCurve()
    top.setPoles(upper)
    bottom.setPoles(lower)
    wire = Part.Wire([top.toShape(), bottom.toShape()])
    if not wire.isClosed() or not wire.isValid():
        raise ValueError("Airfoil section wire not valid and closed")
    return wire


def strip_clip_estimate(geometry, stations, chord_scale_m):
    """Approximate posttip-clipping EAR; interpolation is not exact OCC loft."""
    R = geometry["diameter_m"] / 2
    lo = stations[0]["r_R"]
    n = 2000
    values = []
    for i in range(n + 1):
        rr = lo + (1.0 - lo) * i / n
        r = R * rr
        c = chord_scale_m * linear_station(stations, rr, "chord_weight")
        beta = math.atan(geometry["pitch_ratio"] * geometry["diameter_m"] *
                         linear_station(stations, rr, "pitch_factor") / (2*math.pi*r))
        skew = r * math.tan(math.radians(geometry["skew_deg"]) * linear_station(stations, rr, "skew_factor"))
        ylimit = math.sqrt(max(0, R*R-r*r))
        umin = max(-.25*c, (-ylimit-skew)/math.cos(beta))
        umax = min(.75*c, (ylimit-skew)/math.cos(beta))
        values.append((r, max(0, umax-umin)))
    area = geometry["blades"] * trapezoid(values)
    return {"clipped_expanded_area_strip_estimate_m2": area,
            "clipped_EAR_strip_estimate": area / (math.pi * R * R),
            "strip_estimate_method": "2000 intervals, linear radial recipe, mid-thickness chord clipped by reference cylinder; excludes thickness, hub occlusion and OCC loft interpolation"}


def properties(shape):
    bb = shape.BoundBox
    # STEP import may wrap one closed solid in a Compound: Compound.isClosed
    # then describes the wrapper flag, not whether all its solid shells close.
    return {"valid": bool(shape.isValid()), "closed": bool(shape.Solids) and all(s.isClosed() for s in shape.Solids),
            "shape_type": shape.ShapeType, "wrapper_closed_flag": bool(shape.isClosed()),
            "solids": len(shape.Solids), "volume_m3": float(shape.Volume) * 1e-9,
            "area_m2": float(shape.Area) * 1e-6,
            "bounding_box_m": {"xmin": bb.XMin*.001, "xmax": bb.XMax*.001,
                               "ymin": bb.YMin*.001, "ymax": bb.YMax*.001,
                               "zmin": bb.ZMin*.001, "zmax": bb.ZMax*.001}}


def build(run, case, item):
    ident = item["id"]
    if not ident or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in ident):
        raise ValueError("Unsafe geometry ID")
    paths = {kind: run / "cad" / (ident + suffix) for kind, suffix in [
        ("fcstd", ".FCStd"), ("step", ".step"), ("stl", ".stl"), ("surface", "_surface.json")]}
    if any(p.exists() for p in paths.values()):
        raise FileExistsError("Refusing to overwrite an existing CAD geometry: " + ident)
    geom = dict(case["geometry"])
    geom.update(item["geometry"])
    stations = case["radial_distribution"]
    validate(geom, stations)
    D_m = geom["diameter_m"]
    D_mm = 1000 * D_m
    R_mm = D_mm/2
    B = int(geom["blades"])
    int_w_dr = trapezoid([(s["r_R"]*D_m/2, s["chord_weight"]) for s in stations])
    nominal_area = geom["expanded_area_ratio"] * math.pi * D_m * D_m / 4
    chord_scale_m = nominal_area / (B * int_w_dr)
    wires = []
    rows = []
    for station in stations:
        r_mm = station["r_R"]*R_mm
        c_mm = 1000*chord_scale_m*station["chord_weight"]
        beta = math.atan(geom["pitch_ratio"]*D_mm*station["pitch_factor"]/(2*math.pi*r_mm))
        skew_mm = r_mm*math.tan(math.radians(geom["skew_deg"])*station["skew_factor"])
        rake_mm = geom["rake_ratio"]*D_mm*station["rake_factor"]
        thickness = geom["thickness_ratio"]*station["thickness_factor"]
        wires.append(airfoil_wire(r_mm, c_mm, beta, thickness, skew_mm, rake_mm))
        rows.append({"r_R": station["r_R"], "r_m": r_mm*.001, "chord_m": c_mm*.001,
                     "beta_deg": math.degrees(beta), "t_c": thickness,
                     "skew_m": skew_mm*.001, "rake_m": rake_mm*.001})
    raw_blade = Part.makeLoft(wires, True, False)
    if not raw_blade.isValid() or not raw_blade.isClosed() or len(raw_blade.Solids) != 1:
        raise ValueError("Untrimmed loft is not one valid closed solid")
    clip = Part.makeCylinder(R_mm, 4*D_mm, App.Vector(0, 0, -2*D_mm))
    blade = raw_blade.common(clip).removeSplitter()
    if not blade.isValid() or not blade.isClosed() or len(blade.Solids) != 1:
        raise ValueError("Trimmed loft is not one valid closed solid")
    hub_radius = geom["hub_ratio"]*D_mm/2
    hub_length = .20*D_mm
    hub = Part.makeCylinder(hub_radius, hub_length, App.Vector(0,0,-hub_length/2))
    blades = []
    fused = hub
    for i in range(B):
        other = blade.copy()
        other.rotate(App.Vector(0,0,0), App.Vector(0,0,1), i*360.0/B)
        intersection = hub.common(other)
        if intersection.Volume <= 1e-6:
            raise ValueError("Blade does not intersect hub")
        blades.append(other)
        fused = fused.fuse(other)
    fused = fused.removeSplitter()
    before_sum = hub.Volume + B*blade.Volume
    # Pairwise overlap outside the hub would merge blades before their roots.
    outside_overlap = 0.0
    for i, a in enumerate(blades):
        for b in blades[i+1:]:
            ov = a.common(b)
            if not ov.isNull() and ov.Volume > 0:
                outside_overlap += ov.cut(hub).Volume
    if outside_overlap > max(1e-4, fused.Volume*1e-8):
        raise ValueError("Adjacent blades overlap outside the hub, mm3=" + str(outside_overlap))
    props = properties(fused)
    if not props["valid"] or not props["closed"] or props["solids"] != 1 or props["volume_m3"] <= 0:
        raise ValueError("Final propeller is not one positive-volume valid closed solid")
    # removeSplitter() may return a one-solid compound. Use its actual Solid
    # for mass-property API access and unambiguous document/export topology.
    fused = fused.Solids[0]
    props = properties(fused)
    doc = None
    reopened = None
    try:
        doc = App.newDocument("Propeller_" + ident)
        obj = doc.addObject("PartDesign::Feature", "Propeller")
        obj.Label = "CantaX " + ident + " — parameterized loft recipe"
        obj.Shape = fused
        obj.addProperty("App::PropertyLength", "ReferenceDiameter", "CantaXInputs").ReferenceDiameter = D_mm
        obj.addProperty("App::PropertyInteger", "BladeCount", "CantaXInputs").BladeCount = B
        for name, key in [("PitchDiameterRatio", "pitch_ratio"), ("NominalExpandedAreaRatio", "expanded_area_ratio"),
                          ("ThicknessChordRatio", "thickness_ratio"), ("SkewDegrees", "skew_deg"),
                          ("RakeDiameterRatio", "rake_ratio"), ("HubDiameterRatio", "hub_ratio")]:
            obj.addProperty("App::PropertyFloat", name, "CantaXInputs")
            setattr(obj, name, geom[key])
        obj.addProperty("App::PropertyString", "RadialRecipeJSON", "CantaXInputs").RadialRecipeJSON = json.dumps(stations)
        obj.addProperty("App::PropertyString", "Regeneration", "CantaXInputs").Regeneration = "Edit Excel inputs and run launch.ps1; scripts/generate_cad.py regenerates a new run. This feature stores its final BRep and recipe, not an embedded live Python proxy."
        doc.recompute()
        doc.saveAs(str(paths["fcstd"]))
        Part.export([obj], str(paths["step"]))
        name = doc.Name
        App.closeDocument(name)
        doc = None
        reopened = App.openDocument(str(paths["fcstd"]))
        fcshape = reopened.getObject("Propeller").Shape
        fcprops = properties(fcshape)
        App.closeDocument(reopened.Name)
        reopened = None
        step_shape = Part.Shape()
        step_shape.read(str(paths["step"]))
        stepprops = properties(step_shape)
        roundtrips = []
        for kind, check in [("FCStd", fcprops), ("STEP", stepprops)]:
            error = abs(check["volume_m3"]-props["volume_m3"])/props["volume_m3"]
            bbox_error = max(abs(check["bounding_box_m"][k]-props["bounding_box_m"][k]) for k in props["bounding_box_m"])
            volume_tol = 1e-4
            bbox_tol = D_m*1e-5
            passed = check["valid"] and check["closed"] and check["solids"] == 1 and error <= volume_tol and bbox_error <= bbox_tol
            roundtrips.append({"format": kind, "passed": passed, "relative_volume_error": error,
                              "volume_relative_tolerance": volume_tol, "maximum_bounding_box_coordinate_error_m": bbox_error,
                              "bounding_box_tolerance_m": bbox_tol, **check})
            if not passed:
                raise ValueError(kind + " roundtrip validation failed: " + json.dumps(roundtrips[-1]))
        vertices, faces = fused.tessellate(max(.08, D_mm/1000))
        max_radius_mm = max(math.hypot(v.x, v.y) for v in vertices)
        if max_radius_mm > R_mm*(1+1e-6):
            raise ValueError("Tessellated CAD vertices exceed nominal tip cylinder")
        surface = {"source": str(paths["fcstd"]), "generator": "FreeCAD Part.Shape.tessellate of actual validated final BRep", "units": "m",
                   "deflection_mm": max(.08, D_mm/1000),
                   "vertices": [[v.x*.001, v.y*.001, v.z*.001] for v in vertices],
                   "faces": [list(f) for f in faces]}
        dump(paths["surface"], surface)
        Mesh.Mesh((vertices, faces)).write(str(paths["stl"]))
        # Volume moments from FreeCAD are mm5 (unit-density integral dV*r2).
        matrix = fused.MatrixOfInertia
        com = fused.CenterOfMass
        axial_unitdensity = (matrix.A33 + fused.Volume*(com.x*com.x + com.y*com.y))*1e-15
        result = {"id": ident, "status": "verified", "application": "FreeCAD", "geometry": geom, **props,
                  "nominal_expanded_blade_area_m2": nominal_area, "radial_sections": rows,
                  "tessellation_max_radius_m": max_radius_mm*.001,
                  "tip_envelope_check_passed": True,
                  "blade_unclipped_volume_m3": raw_blade.Volume*1e-9,
                  "blade_clipped_volume_m3": blade.Volume*1e-9,
                  "tip_clipped_volume_fraction": 1 - blade.Volume/raw_blade.Volume,
                  "blade_clipped_surface_area_m2": blade.Area*1e-6,
                  "blade_overlap_outside_hub_m3": outside_overlap*1e-9,
                  "hub_blade_intersection_volume_m3": (before_sum-fused.Volume)*1e-9,
                  "center_of_mass_m": [com.x*.001, com.y*.001, com.z*.001],
                  "axial_mass_inertia_per_density_m5": axial_unitdensity,
                  "roundtrip_checks": roundtrips, "unit_mapping": {"CAD": "mm", "public_outputs": "SI", "volume_multiplier": 1e-9, "area_multiplier": 1e-6, "mass_moment_multiplier": 1e-15},
                  "artifacts": {kind: str(path) for kind, path in paths.items()},
                  **strip_clip_estimate(geom, stations, chord_scale_m)}
        density = case.get("material_density_kgm3")
        if density is not None:
            result["material_density_kgm3"] = density
            result["mass_kg"] = density*result["volume_m3"]
            result["axial_mass_inertia_kgm2"] = density*axial_unitdensity
        return result
    finally:
        for owned in [doc, reopened]:
            if owned is not None and App.getDocument(owned.Name):
                App.closeDocument(owned.Name)


def main():
    run = Path(os.environ["CANTAX_RUN_DIR"]).resolve()
    root = Path(__file__).resolve().parents[1]
    if not run.is_relative_to(root / "runs"):
        raise ValueError("CANTAX_RUN_DIR must be inside this lab's runs directory")
    output = run / "cad_results.json"
    if output.exists():
        raise FileExistsError("Refusing to overwrite CAD results")
    (run / "cad").mkdir(parents=True, exist_ok=True)
    case = json.loads((run / "case.json").read_text(encoding="utf-8-sig"))
    family = json.loads((run / "family.json").read_text(encoding="utf-8-sig"))
    report = {"application": "FreeCAD", "version": list(App.Version()), "status": "failed",
              "axis": "+Z propeller shaft", "length_units_internal": "mm", "length_units_json": "m",
              "models": [], "verified_count": 0}
    began = time.monotonic()
    for item in family:
        stamp = time.monotonic()
        print("CANTAX_CAD_START " + item["id"], flush=True)
        try:
            record = build(run, case, item)
            report["verified_count"] += 1
        except BaseException as exc:
            record = {"id": item["id"], "status": "failed", "geometry": item["geometry"],
                      "error": repr(exc), "traceback": traceback.format_exc()}
            dump(run / "cad" / (item["id"] + "_error.json"), record)
        record["elapsed_s"] = time.monotonic()-stamp
        report["models"].append(record)
        print("CANTAX_CAD_RESULT " + json.dumps({"id": record["id"], "status": record["status"], "elapsed_s": record["elapsed_s"], "error": record.get("error")}), flush=True)
        report["elapsed_s"] = time.monotonic()-began
        # Results are incrementally preserved for a launcher timeout or interruption.
        report["status"] = "verified" if report["verified_count"] == len(family) else "partial" if report["verified_count"] else "failed"
        dump(output, report)
    return 0 if report["verified_count"] == len(family) else 1


try:
    sys.exit(main())
except BaseException as exc:
    if isinstance(exc, SystemExit):
        raise
    print(traceback.format_exc(), flush=True)
    sys.exit(1)
