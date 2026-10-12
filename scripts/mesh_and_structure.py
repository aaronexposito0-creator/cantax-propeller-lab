"""Local Gmsh meshing and CalculiX screening; standard-library-only, SI.

Each invocation writes only to a fresh subdirectory of this lab. Mesh/FEM
verification is not physical validation, certification, CFD or fatigue proof.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import csv
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
from runtime_config import executable

ROOT = Path(__file__).resolve().parents[1]
def engine(name):
    return executable(name)

def save_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def within(path):
    p = Path(path).resolve()
    if not p.is_relative_to(ROOT):
        raise ValueError("Path must remain in CantaX_Propeller_Lab: " + str(p))
    return p

def execute(cmd, out, timeout=240):
    result = subprocess.run(list(map(str, cmd)), cwd=out, capture_output=True,
                            text=True, errors="replace", timeout=timeout)
    return result

def parse_dat(path):
    """Parse unambiguous ASCII *NODE PRINT U/RF and *EL PRINT S blocks."""
    blocks = {"displacements": [], "forces": [], "stresses": []}
    mode = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        lower = line.strip().lower()
        if lower.startswith("displacements ("):
            mode = "displacements"
        elif lower.startswith("forces ("):
            mode = "forces"
        elif lower.startswith("stresses ("):
            mode = "stresses"
        elif not lower:
            continue
        elif mode:
            fields = line.split()
            try:
                vals = [float(x.replace("D", "E")) for x in fields]
            except ValueError:
                mode = None
                continue
            required = 8 if mode == "stresses" else 4
            if len(vals) == required:
                blocks[mode].append(vals)
    return blocks

def benchmark(out):
    out.mkdir(parents=True, exist_ok=False)
    inp = """*HEADING
CantaX SI uniaxial cube integration benchmark; synthetic E=200GPa nu=0
*NODE,NSET=NALL
1,0,0,0
2,0.1,0,0
3,0.1,0.1,0
4,0,0.1,0
5,0,0,0.1
6,0.1,0,0.1
7,0.1,0.1,0.1
8,0,0.1,0.1
*ELEMENT,TYPE=C3D8,ELSET=EALL
1,1,2,3,4,5,6,7,8
*NSET,NSET=FIXED
1,4,5,8
*NSET,NSET=LOADED
2,3,6,7
*MATERIAL,NAME=SYNTHETIC
*ELASTIC
200000000000,0
*SOLID SECTION,ELSET=EALL,MATERIAL=SYNTHETIC
*BOUNDARY
FIXED,1,1,0
NALL,2,3,0
*STEP
*STATIC
*CLOAD
2,1,25
3,1,25
6,1,25
7,1,25
*NODE PRINT,NSET=NALL
U
*NODE PRINT,NSET=FIXED,TOTALS=YES
RF
*EL PRINT,ELSET=EALL
S
*NODE FILE
U
*EL FILE
S
*END STEP
"""
    (out / "uniaxial.inp").write_text(inp, encoding="ascii")
    result = {"status": "FAIL", "executable": str(engine("calculix")),
              "expected_stress_Pa": 10000.0, "expected_displacement_m": 5e-9,
              "expected_reaction_N": -100.0, "relative_tolerance": 1e-5,
              "input_sha256": sha(out / "uniaxial.inp"),
              "scope": "Actual solver plus analytic integration check; synthetic material, no physical validation."}
    try:
        proc = execute([engine("calculix"), "-i", "uniaxial"], out)
        log = proc.stdout + proc.stderr
        (out / "solver.log").write_text(log, encoding="utf-8")
        result["exit_code"] = proc.returncode
        version = re.search(r"CalculiX Version\s+([^\r\n]+)", log)
        result["version"] = version.group(1).strip() if version else None
        if proc.returncode != 0 or "*ERROR" in log.upper():
            raise RuntimeError("Solver return/error: inspect solver.log")
        data = parse_dat(out / "uniaxial.dat")
        loaded_u = [row[1] for row in data["displacements"] if int(row[0]) in (2,3,6,7)]
        stresses = [row[2] for row in data["stresses"]]
        reaction = sum(row[1] for row in data["forces"])
        if len(loaded_u) != 4 or len(stresses) != 8:
            raise RuntimeError("Incomplete displacement/integration point stress output")
        u_error = max(abs(v / 5e-9 - 1) for v in loaded_u)
        s_error = max(abs(v / 10000 - 1) for v in stresses)
        r_error = abs(reaction / -100 - 1)
        result.update(displacement_m=loaded_u, stress_xx_Pa=stresses,
                      reaction_N=reaction, relative_errors={"u":u_error,"s":s_error,"reaction":r_error})
        if max(u_error, s_error, r_error) > result["relative_tolerance"]:
            raise RuntimeError("Analytic comparison failed")
        if not (out / "uniaxial.frd").exists():
            raise RuntimeError("Missing FRD output")
        result["status"] = "PASS"
        result["data_sha256"] = sha(out / "uniaxial.dat")
    except Exception as exc:
        result["error"] = str(exc)
    save_json(out / "benchmark_results.json", result)
    return result

def sub(a,b):
    return tuple(a[i]-b[i] for i in range(3))

def cross(a,b):
    return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])

def dot(a,b):
    return sum(a[i]*b[i] for i in range(3))

def read_msh(path):
    lines = path.read_text(encoding="ascii").splitlines()
    if lines[lines.index("$MeshFormat")+1].split()[:2] != ["2.2","0"]:
        raise ValueError("Expected ASCII Gmsh 2.2")
    i = lines.index("$Nodes")
    coords = {}
    for line in lines[i+2:i+2+int(lines[i+1])]:
        f=line.split(); coords[int(f[0])] = tuple(map(float,f[1:4]))
    i = lines.index("$Elements"); tets=[]
    for line in lines[i+2:i+2+int(lines[i+1])]:
        f=list(map(int,line.split()))
        if f[1] == 4:
            tets.append((f[0],tuple(f[3+f[2]:])))
    if not tets:
        raise ValueError("No tetrahedra generated")
    return coords,tets

def analyze_mesh(path, cad_volume_m3):
    coords,tets=read_msh(path)
    volumes=[]; qualities=[]; signs=[]; faces=Counter(); oriented={}
    for _,ids in tets:
        a,b,c,d=[coords[n] for n in ids]
        det=dot(sub(b,a),cross(sub(c,a),sub(d,a)))
        volume=abs(det)/6; volumes.append(volume); signs.append(det)
        l2=sum(dot(sub(coords[ids[i]],coords[ids[j]]),sub(coords[ids[i]],coords[ids[j]]))
               for i in range(4) for j in range(i+1,4))
        qualities.append(12*(3*volume)**(2/3)/l2 if l2>0 else 0)
        for f in ((ids[0],ids[2],ids[1]),(ids[0],ids[1],ids[3]),
                  (ids[1],ids[2],ids[3]),(ids[2],ids[0],ids[3])):
            key=tuple(sorted(f)); faces[key]+=1; oriented[key]=f
    bounds=[[min(v[i] for v in coords.values()),max(v[i] for v in coords.values())] for i in range(3)]
    length=max(b[1]-b[0] for b in bounds)
    degenerate=sum(v <= max(length**3*1e-15,1e-24) for v in volumes)
    volume=math.fsum(volumes)
    error=abs(volume/cad_volume_m3-1)
    qsort=sorted(qualities)
    boundary=[oriented[f] for f,n in faces.items() if n==1]
    result={"status": "PASS" if degenerate==0 and min(signs)>0 and error<=0.05 and max(faces.values())<=2 else "FAIL",
            "mesh":str(path), "sha256":sha(path), "nodes":len(coords),"tetrahedra":len(tets),
            "boundary_triangles":len(boundary),"units":"m; m3",
            "summed_volume_m3":volume,"cad_volume_m3":cad_volume_m3,"relative_volume_error":error,
            "volume_acceptance_tolerance":0.05,"minimum_tet_volume_m3":min(volumes),
            "degenerate_elements":degenerate,"negative_orientation_elements":sum(s<0 for s in signs),
            "minimum_signed_determinant_m3":min(signs),"nonmanifold_faces":sum(n>2 for n in faces.values()),
            "bounding_box_m":bounds,
            "quality":{"metric":"tetrahedron mean ratio 12*(3*V)^(2/3)/sum(edge_length_squared)",
                       "minimum":min(qualities),"p05":qsort[int(0.05*(len(qsort)-1))],
                       "median":qsort[len(qsort)//2],"maximum":max(qualities),
                       "normalization":"1 for equilateral tetrahedron; 0 for zero volume"},
            "scope":"Geometric and element checks only. Size variation is not CFD/FEM solution convergence."}
    result["quality"]["elements_below_0_05"] = sum(q<0.05 for q in qualities)
    result["warnings"] = (["Some tetrahedra have mean ratio below0.05; inspect and refine before solution convergence claims"]
                          if min(qualities)<0.05 else [])
    return result,coords,tets,boundary

def gmsh_path_literal(step):
    """Keep an input filename inside one Gmsh string, never executable .geo text."""
    value=Path(step).as_posix()
    if any(ord(c)<32 for c in value) or '"' in value:
        raise ValueError('STEP path contains a quote/control character unsafe for a Gmsh literal')
    return '"'+value+'"'

def mesh(step,out,size_m,cad_volume_m3):
    step_literal=gmsh_path_literal(step)
    if not math.isfinite(size_m) or size_m<=0 or not math.isfinite(cad_volume_m3) or cad_volume_m3<=0:
        raise ValueError('Mesh size and CAD volume must be positive finite SI values')
    out.mkdir(parents=True,exist_ok=False)
    geo=out/"mesh.geo"
    # OCCTargetUnit is explicit: avoids relying on default STEP import units.
    geo.write_text('SetFactory("OpenCASCADE");\nGeometry.OCCTargetUnit = "M";\n'
                   'Merge '+step_literal+';\n'
                   f'Mesh.MeshSizeMin = {size_m/3:.12g};\nMesh.MeshSizeMax = {size_m:.12g};\n'
                   'Mesh.MeshSizeFromCurvature = 10;\nMesh.ElementOrder = 1;\n'
                   'Mesh.Algorithm3D = 1;\nMesh.Optimize = 1;\n'
                   'Mesh.MshFileVersion = 2.2;\nMesh.Binary = 0;\n',encoding="utf-8")
    path=out/"propeller.msh"
    proc=execute([engine("gmsh"),geo,"-3","-format","msh2","-o",path,"-nopopup","-nt","2"],out,timeout=360)
    (out/"gmsh.log").write_text(proc.stdout+proc.stderr,encoding="utf-8")
    if proc.returncode!=0 or not path.exists():
        raise RuntimeError("Gmsh failed: "+str(out/"gmsh.log"))
    result,coords,tets,boundary=analyze_mesh(path,cad_volume_m3)
    result.update(mesh_size_min_m=size_m/3,mesh_size_max_m=size_m,
                  geometric_unit_target="M",step_sha256=sha(step),command=list(map(str,[engine("gmsh"),geo,"-3","-format","msh2","-o",path,"-nopopup","-nt","2"])))
    save_json(out/"mesh_results.json",result)
    # Boundary faces come from tetra connectivity, not a claim of CFD surface.
    surface_ids=sorted({n for f in boundary for n in f}); indices={n:i for i,n in enumerate(surface_ids)}
    save_json(out/"surface.json",{"units":"m","vertices":[coords[n] for n in surface_ids],
                                 "triangles":[[indices[n] for n in f] for f in boundary],
                                 "mesh_sha256":sha(path)})
    return result,coords,tets,boundary

def von_mises(stress):
    xx,yy,zz,xy,xz,yz=stress
    return math.sqrt(((xx-yy)**2+(yy-zz)**2+(zz-xx)**2)/2+3*(xy*xy+xz*xz+yz*yz))

def preliminary_fem(out,coords,tets,boundary,case,material,sections):
    """Resultant-preserving nodal load screen; loads referred to +Z shaft."""
    out.mkdir(parents=True,exist_ok=False)
    hub_r=case["geometry"]["hub_ratio"]*case["geometry"]["diameter_m"]/2
    fixed={n for n,(x,y,z) in coords.items() if math.hypot(x,y)<=hub_r*1.001}
    weights=defaultdict(float)
    for face in boundary:
        a,b,c=[coords[n] for n in face]
        area=math.sqrt(dot(cross(sub(b,a),sub(c,a)),cross(sub(b,a),sub(c,a))))/2
        for n in face:
            if n not in fixed:
                weights[n]+=area/3
    if not fixed or not weights:
        raise ValueError("No rigid hub constraint or blade load nodes")
    forces={n:[0.0,0.0,0.0] for n in coords}
    section_checks=[]
    for section in sections:
        lo=float(section["r_inner_m"]); hi=float(section["r_outer_m"])
        selected={n:w for n,w in weights.items() if lo<=math.hypot(*coords[n][:2])<hi}
        if not selected:
            target=(lo+hi)/2
            distance=min(abs(math.hypot(*coords[n][:2])-target) for n in weights)
            selected={n:w for n,w in weights.items() if abs(abs(math.hypot(*coords[n][:2])-target)-distance)<1e-10}
        total_w=sum(selected.values())
        mean_x=sum(w*coords[n][0] for n,w in selected.items())/total_w
        mean_y=sum(w*coords[n][1] for n,w in selected.items())/total_w
        cov_xx=sum(w*(coords[n][0]-mean_x)**2 for n,w in selected.items())/total_w
        cov_yy=sum(w*(coords[n][1]-mean_y)**2 for n,w in selected.items())/total_w
        cov_xy=sum(w*(coords[n][0]-mean_x)*(coords[n][1]-mean_y) for n,w in selected.items())/total_w
        determinant=cov_xx*cov_yy-cov_xy*cov_xy
        if determinant<=1e-12*(cov_xx+cov_yy)**2:
            raise ValueError("Annulus surface nodes cannot represent axisymmetric load resultants")
        # Centroid corrections enforce pure axial resultant and zero bending
        # moment despite an irregular surface mesh of a symmetric propeller.
        correction_x=(-mean_x*cov_yy+mean_y*cov_xy)/determinant
        correction_y=(-mean_y*cov_xx+mean_x*cov_xy)/determinant
        polar_w=total_w*(cov_xx+cov_yy)
        thrust=float(section["dT_N"]); torque=float(section["dQ_Nm"])
        factors=[]
        for n,w in selected.items():
            x,y,z=coords[n]
            forces[n][0]+=-torque*w*(y-mean_y)/polar_w
            forces[n][1]+=torque*w*(x-mean_x)/polar_w
            factor=1+correction_x*(x-mean_x)+correction_y*(y-mean_y)
            factors.append(factor)
            forces[n][2]+=thrust*w*factor/total_w
        if min(factors)<0:
            raise ValueError("Annulus centroid correction produces negative axial load weights; refine mesh")
        section_checks.append({"r_inner_m":lo,"r_outer_m":hi,"nodes":len(selected),"thrust_N":thrust,"torque_Nm":torque,
                               "axial_centroid_correction_factor_min":min(factors),"axial_centroid_correction_factor_max":max(factors)})
    hydro_force=[math.fsum(f[i] for f in forces.values()) for i in range(3)]
    hydro_torque=math.fsum(coords[n][0]*f[1]-coords[n][1]*f[0] for n,f in forces.items())
    omega=case["operation"]["rpm"]*2*math.pi/60
    masses=defaultdict(float)
    for _,ids in tets:
        a,b,c,d=[coords[n] for n in ids]
        mass=abs(dot(sub(b,a),cross(sub(c,a),sub(d,a))))/6*material["density_kgm3"]
        for n in ids:
            masses[n]+=mass/4
    for n,m in masses.items():
        x,y,z=coords[n]; forces[n][0]+=m*omega*omega*x; forces[n][1]+=m*omega*omega*y
    total_force=[math.fsum(f[i] for f in forces.values()) for i in range(3)]
    total_moment=[math.fsum(cross(coords[n],f)[i] for n,f in forces.items()) for i in range(3)]
    expected_T=sum(float(s["dT_N"]) for s in sections); expected_Q=sum(float(s["dQ_Nm"]) for s in sections)
    if abs(hydro_force[2]-expected_T)>max(1e-8,abs(expected_T)*1e-10) or abs(hydro_torque-expected_Q)>max(1e-8,abs(expected_Q)*1e-10):
        raise ValueError("Hydrodynamic load transfer does not conserve thrust/torque")
    text=["*HEADING","CantaX PRELIMINARY SI rigid hub / resultant load screen","*NODE,NSET=NALL"]
    text += [f"{n},{p[0]:.12g},{p[1]:.12g},{p[2]:.12g}" for n,p in sorted(coords.items())]
    text += ["*ELEMENT,TYPE=C3D4,ELSET=EALL"]+[str(i)+","+",".join(map(str,ids)) for i,(_,ids) in enumerate(tets,1)]
    text += ["*NSET,NSET=FIXED"]
    fixed_list=sorted(fixed)
    text += [",".join(map(str,fixed_list[i:i+12])) for i in range(0,len(fixed_list),12)]
    text += ["*MATERIAL,NAME=SELECTED","*ELASTIC",f'{material["elastic_modulus_Pa"]:.12g},{material["poisson_ratio"]}',
             "*SOLID SECTION,ELSET=EALL,MATERIAL=SELECTED","*BOUNDARY","FIXED,1,3,0","*STEP","*STATIC","*CLOAD"]
    text += [f"{n},{i+1},{f[i]:.12g}" for n,f in forces.items() for i in range(3) if abs(f[i])>1e-14]
    text += ["*NODE PRINT,NSET=NALL","U","*NODE PRINT,NSET=FIXED,TOTALS=YES","RF", "*EL PRINT,ELSET=EALL","S",
             "*NODE FILE","U","*EL FILE","S","*END STEP"]
    inp=out/"propeller.inp"; inp.write_text("\n".join(text)+"\n",encoding="ascii")
    result={"status":"FAIL","classification":"PRELIMINARY_ELASTIC_ESTIMATE",
            "material_id":material["id"],"material_class":material["property_class"],
            "constraint":"All 3 translations fixed on nodes r<=hub radius, ideal rigid hub; shaft +Z",
            "elements":"C3D4 linear tetrahedra; bending stiffness/peak stress require convergence study",
            "hydro_resultant_force_N":hydro_force,"hydro_resultant_torque_Nm":hydro_torque,
            "load_transfer":"Surface-area weights with per-annulus centroid correction preserve axial thrust, torque, zero lateral force and axial-load bending moment; torque force couples can retain bending resultants due to blade rake",
            "applied_total_force_N":total_force,"applied_total_moment_Nm":total_moment,
            "load_transfer_sections":section_checks,"fixed_nodes":len(fixed),"loaded_surface_nodes":len(weights),
            "centrifugal_load":"Lumped tetra mass times omega²*(x,y,0) on undeformed configuration",
            "mesh_mass_kg":sum(masses.values()),"input_sha256":sha(inp),
            "fatigue":"NO_CALCULADO","corrosion":"NO_CALCULADO","cavitation_damage":"NO_CALCULADO",
            "safety_factor":None,"allowable_stress_Pa":None,"service_approval":"NO_CALCULADO"}
    proc=execute([engine("calculix"),"-i","propeller"],out,timeout=360)
    log=proc.stdout+proc.stderr; (out/"solver.log").write_text(log,encoding="utf-8")
    result["exit_code"]=proc.returncode
    if proc.returncode or "*ERROR" in log.upper():
        result["error"]="Solver error; inspect log"
    else:
        data=parse_dat(out/"propeller.dat")
        if not data["displacements"] or not data["stresses"]:
            result["error"]="No parsed displacement or integration point stress"
        else:
            result["maximum_displacement_m"]=max(math.sqrt(sum(u*u for u in row[1:])) for row in data["displacements"])
            result["maximum_integration_point_von_mises_Pa"]=max(von_mises(row[2:]) for row in data["stresses"])
            reactions=[math.fsum(row[i+1] for row in data["forces"]) for i in range(3)]
            result["reaction_force_N"]=reactions
            result["force_balance_residual_N"]=[reactions[i]+total_force[i] for i in range(3)]
            reaction_moment=[math.fsum(cross(coords[int(row[0])],row[1:])[i] for row in data["forces"]) for i in range(3)]
            result["reaction_moment_Nm"]=reaction_moment
            result["moment_balance_residual_Nm"]=[reaction_moment[i]+total_moment[i] for i in range(3)]
            scale=max(1.0,abs(expected_T),abs(expected_Q)/case["geometry"]["diameter_m"])
            result["force_balance_relative_norm"]=math.sqrt(sum(v*v for v in result["force_balance_residual_N"]))/scale
            moment_scale=max(1.0,abs(expected_T)*case["geometry"]["diameter_m"],abs(expected_Q))
            result["moment_balance_relative_norm"]=math.sqrt(sum(v*v for v in result["moment_balance_residual_Nm"]))/moment_scale
            result["status"]="PRELIMINARY_COMPUTED" if max(result["force_balance_relative_norm"],result["moment_balance_relative_norm"])<1e-3 else "FAIL_BALANCE"
            result["data_sha256"]=sha(out/"propeller.dat")
            # A usable VTU-free CSV for audit, with actual nodal displacement.
            with (out/"displacements.csv").open("w",newline="",encoding="utf-8") as handle:
                writer=csv.writer(handle); writer.writerow(["node","ux_m","uy_m","uz_m"]); writer.writerows(data["displacements"])
    save_json(out/"fem_results.json",result)
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--run-dir",default=os.environ.get("CANTAX_RUN_DIR"))
    parser.add_argument("--case")
    parser.add_argument("--step")
    parser.add_argument("--cad-volume-m3",type=float)
    parser.add_argument("--candidate-id",default="reference")
    parser.add_argument("--sections",help="CSV r_inner_m,r_outer_m,dT_N,dQ_Nm; SI full-propeller annuli")
    parser.add_argument("--benchmark-only",action="store_true")
    parser.add_argument("--fem",action="store_true",help="Enable explicit rigid-hub resultant-load preliminary FEM")
    args=parser.parse_args()
    run=within(args.run_dir) if args.run_dir else ROOT/"runs"/("mesh_development_"+dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    if not run.resolve().is_relative_to((ROOT/'runs').resolve()):
        raise ValueError('Output run must remain inside this checkout runs directory')
    run.mkdir(parents=True,exist_ok=True)
    stage=run/"mesh_structure"; stage.mkdir(exist_ok=False)
    result={"timestamp_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"status":"PARTIAL",
            "programs":{"Gmsh":str(engine("gmsh")),"CalculiX":str(engine("calculix"))},"meshes":[],
            "structure":{"status":"NO_CALCULADO","reason":"No CAD/load data provided"}}
    try:
        result["calculix_benchmark"]=benchmark(stage/"benchmark")
        version=execute([engine("gmsh"),"--version"],stage,timeout=30)
        result["gmsh_version"]=(version.stdout+version.stderr).strip()
        if not args.benchmark_only:
            case_path=within(args.case or run/"case.json")
            case=json.loads(case_path.read_text(encoding="utf-8-sig"))
            if not args.step or not args.cad_volume_m3:
                raise ValueError("Provide --step and --cad-volume-m3 (closed FreeCAD CAD volume)")
            step=within(args.step); diameter=case["geometry"]["diameter_m"]
            coarse=mesh(step,stage/"coarse",diameter/30,args.cad_volume_m3)
            fine=mesh(step,stage/"fine",diameter/45,args.cad_volume_m3)
            result["meshes"]=[coarse[0],fine[0]]
            result["candidate_id"]=args.candidate_id
            result["size_variation"]={"tetrahedra_ratio_fine_coarse":fine[0]["tetrahedra"]/coarse[0]["tetrahedra"],
                                      "volume_difference_m3":fine[0]["summed_volume_m3"]-coarse[0]["summed_volume_m3"],
                                      "scope":"Geometry discretization check only; no structural or CFD solution convergence."}
            result["structure"]={"status":"NO_CALCULADO","reason":"FEM opt-in requires material/annular loads and acknowledged ideal hub/load assumptions"}
            if args.fem and args.sections and result["calculix_benchmark"]["status"]=="PASS":
                material_path=run/"config_snapshot/materials.json"
                if not material_path.exists():material_path=ROOT/"config/materials.json"
                materials=json.loads(material_path.read_text(encoding="utf-8"))["materials"]
                material=next(m for m in materials if m["id"]==case["material"])
                if material["elastic_modulus_Pa"] is None or material["poisson_ratio"] is None:
                    result["structure"]={"status":"NO_CALCULADO","reason":"Missing sourced E or Poisson ratio"}
                elif fine[0]["status"]!="PASS":
                    result["structure"]={"status":"NO_CALCULADO","reason":"Mesh failed acceptance"}
                else:
                    with within(args.sections).open(encoding="utf-8-sig",newline="") as handle:
                        sections=list(csv.DictReader(handle))
                    result["structure"]=preliminary_fem(stage/"fem",fine[1],fine[2],fine[3],case,material,sections)
            result["status"]="PASS" if all(m["status"]=="PASS" for m in result["meshes"]) and result["calculix_benchmark"]["status"]=="PASS" else "PARTIAL"
            if result["structure"]["status"].startswith("FAIL"):
                result["status"]="PARTIAL"
        else:
            result["status"]=result["calculix_benchmark"]["status"]
    except Exception as exc:
        result["error"]=f"{type(exc).__name__}: {exc}"
        result["status"]="FAIL"
    save_json(run/"structure_results.json",result)
    summary={"status":result["status"],"results_json":str(run/"structure_results.json"),
             "calculix_benchmark":result.get("calculix_benchmark",{}).get("status"),
             "gmsh_version":result.get("gmsh_version"),
             "meshes":[{k:m[k] for k in ("status","nodes","tetrahedra","relative_volume_error","degenerate_elements","negative_orientation_elements")} for m in result["meshes"]],
             "structure":{k:v for k,v in result["structure"].items() if k in ("status","maximum_displacement_m","maximum_integration_point_von_mises_Pa","force_balance_relative_norm","moment_balance_relative_norm","error")}}
    if "error" in result: summary["error"]=result["error"]
    print(json.dumps(summary,indent=2,ensure_ascii=True))
    return 0 if result["status"]=="PASS" else 2

if __name__=="__main__":
    raise SystemExit(main())
