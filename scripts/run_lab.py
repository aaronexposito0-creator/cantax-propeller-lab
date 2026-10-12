"""CantaX Propeller Lab: repeatable local engineering pipeline with immutable run folders."""
import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import traceback
import uuid
from runtime_config import executable, require_engines, local_engine_environment
from engineering_checks import preflight_xlsx, validate_case, verify_saved_case
from build_workbook import build as build_workbook

ROOT=Path(__file__).resolve().parents[1]
PYSCRIPT=ROOT/'scripts'
PYTHON=Path(sys.executable)

def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def write(path,data):Path(path).write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')

def refresh_panel(run,source,source_hash,controller_path=None):
    """Keep computed results even when the controller is locked or newly edited."""
    target=Path(controller_path).resolve() if controller_path else ROOT/'CantaX_Propeller_Lab.xlsx'
    if not target.is_relative_to(ROOT):raise ValueError('Controller refresh outside lab is prohibited')
    draft=run/'panel_refresh.xlsx';shutil.copy2(run/'CantaX_Propeller_Resultados.xlsx',draft)
    try:
        if source.resolve()==target.resolve() and hashlib.sha256(target.read_bytes()).hexdigest()!=source_hash:
            return {'status':'DEFERRED_CONTROLLER_CHANGED','message':'El panel cambió durante el cálculo; se conserva tu edición. Abre los resultados de esta ejecución.','preserved_copy':str(draft)}
    except (PermissionError,FileNotFoundError):
        return {'status':'DEFERRED_PANEL_UNAVAILABLE','message':'El panel está bloqueado o fue retirado. Los resultados se conservan.','preserved_copy':str(draft)}
    try:os.replace(draft,target)
    except PermissionError:
        return {'status':'DEFERRED_PANEL_LOCKED','message':'Excel mantiene abierto el panel. Los resultados están guardados; cierra Excel antes de actualizar el panel.','preserved_copy':str(draft)}
    return {'status':'UPDATED','path':str(target)}

class Pipeline:
    def __init__(self,run):
        self.run=run;self.env=local_engine_environment();self.env['CANTAX_RUN_DIR']=str(run)
        self.env['TEMP']=self.env['TMP']=str(run/'temp');(run/'temp').mkdir()
        self.env['MATLAB_PREFDIR']=str(run/'matlab_preferences')
        self.manifest={'run_id':run.name,'started_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'status':'RUNNING','stages':{},'scope':'Local preliminary engineering; no experimental validation'}
        self.save()
    def save(self):write(self.run/'run_manifest.json',self.manifest)
    def stage(self,name,command,timeout=600):
        print('START '+name,flush=True)
        rec={'status':'RUNNING','command':list(map(str,command)),'started_utc':dt.datetime.now(dt.timezone.utc).isoformat()}
        self.manifest['stages'][name]=rec;self.save()
        with (self.run/(name+'.stdout.log')).open('w',encoding='utf-8') as stdout,(self.run/(name+'.stderr.log')).open('w',encoding='utf-8') as stderr:
            proc=subprocess.Popen(rec['command'],cwd=ROOT,env=self.env,stdout=stdout,stderr=stderr,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));rec['owned_launcher_pid']=proc.pid;self.save()
            try:code=proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True,timeout=20)
                rec.update(status='TIMEOUT',exit_code=124);self.save();raise RuntimeError(name+' timed out; inspect owned COM app state before retry')
        rec.update(status='PROCESS_COMPLETED' if code==0 else 'FAILED',exit_code=code,finished_utc=dt.datetime.now(dt.timezone.utc).isoformat());self.save()
        if code:raise RuntimeError(name+f' exited {code}; inspect {name}.stderr.log and result JSON')
        print('DONE '+name,flush=True)
    def accepted(self,name,result,statuses):
        data=read(self.run/result)
        if data.get('status') not in statuses:raise RuntimeError(f'{name}: result status {data.get("status")} not accepted')
        self.manifest['stages'][name]['status']='VERIFIED_EXECUTION';self.manifest['stages'][name]['result']=result;self.save();return data

def family(case,diameter_sweep=False):
    gs=case['geometry'];out=[{'id':'BASE','geometry':dict(gs)}]
    if diameter_sweep:
        for blades in [3,4,5]:
            for dm in [.97,1.03]:
                for pm in [.90,1.10]:
                    g=dict(gs);g.update(blades=blades,diameter_m=round(max(.15,min(.60,gs['diameter_m']*dm)),8),pitch_ratio=round(max(.5,min(1.1,gs['pitch_ratio']*pm)),8))
                    name=f'D{round(g["diameter_m"]*1000):03d}_B{blades}_P{round(g["pitch_ratio"]*100):03d}'
                    out.append({'id':name,'geometry':g})
        return out
    for blades in [3,4,5]:
        for pm in [.875,1.125]:
            for am in [.50/.55,.65/.55]:
                g=dict(gs);g.update(blades=blades,pitch_ratio=round(gs['pitch_ratio']*pm,8),expanded_area_ratio=round(gs['expanded_area_ratio']*am,8))
                if not(.35<=g['expanded_area_ratio']<=.85 and .5<=g['pitch_ratio']<=1.1):raise ValueError('Family sweep exceeds declared initial geometry range; reduce base pitch/EAR')
                name=f'B{blades}_P{round(g["pitch_ratio"]*100):03d}_E{round(g["expanded_area_ratio"]*100):03d}'
                out.append({'id':name,'geometry':g})
    return out

def combine(run,case):
    hydro=read(run/'hydro_results.json');cad=read(run/'cad_results.json');st=read(run/'structure_results.json')
    models={m['id']:m for m in cad['models']};rows=[]
    elastic_status=st.get('structure',{}).get('status','NO_CALCULADO')
    for h in hydro['alternatives']:
        m=models.get(h['id']);g=m['geometry'] if m else {};mass=m['volume_m3']*case['material_density_kgm3'] if m else None
        good=bool(m and m['status']=='verified' and m['valid'] and m['closed'] and m['solids']==1)
        feasible=bool(h['valid_domain'] and good and h['T_N']>=case['operation']['required_thrust_N'] and h['P_W']<=case['operation']['available_power_W'] and mass<=case['objectives']['maximum_mass_kg'])
        row=dict(id=h['id'],blades=g.get('blades'),pitch_ratio=g.get('pitch_ratio'),expanded_area_ratio=g.get('expanded_area_ratio'),diameter_m=g.get('diameter_m'),mass_kg=mass,cad_valid=good,valid_domain=bool(h['valid_domain']),screening_feasible=feasible,screening_rank=None,
                 structure_status=elastic_status if h['id']=='BASE' else 'NO_CALCULADO',thrust_margin_N=(h['T_N']-case['operation']['required_thrust_N']) if h['T_N'] is not None else None)
        for key in ['T_N','Q_Nm','P_W','KT','KQ','eta0','J']:row[key]=h.get(key)
        rows.append(row)
    eligible=sorted((r for r in rows if r['screening_feasible']),key=lambda r:(-r['eta0'],r['P_W'],r['mass_kg']))
    for i,r in enumerate(eligible,1):r['screening_rank']=i
    rows.sort(key=lambda r:(r['screening_rank'] is None,r['screening_rank'] or 1000,r['id']))
    recommendation={'id':eligible[0]['id'] if eligible else None,'scope':'Hydrodynamic/mass screening inside analytical model guards; not a global structural/cavitation ranking',
                    'limitations':['No experimental polar or vessel wake','Nominal pre-clipped strip geometry in BEM','Strength/fatigue/corrosion/cavitation uncalculated; elastic FEM only BASE','Candidate winner needs its own converged structural analysis']}
    curve=[]
    with (run/'hydro_curves.csv').open(newline='',encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            d={k:float(v) if v and math.isfinite(float(v)) else None for k,v in r.items()};d['valid_domain']=bool(d['valid_domain']);curve.append(d)
    ov=read(run/'octave_verification.json');sv=read(run/'scilab_verification.json');dv=read(run/'dynamics_result.json')
    checks=[['Lectura real de Excel','VERIFICADA','COM, unidades y valores del libro guardado'],['FreeCAD','VERIFICADA',f'{len(models)} sólidos distintos; guardar/reabrir FCStd y STEP'],['Gmsh','VERIFICADA','Dos tamaños, volúmenes y calidad; avisos de slivers conservados'],['MATLAB BEM','ESTIMACIÓN CALCULADA','Dominio admitido y refinamiento radial; sin validación experimental'],['Simulink','EJECUTADO','SLX guardado/reabierto, arranque y cambios de RPM/carga'],['Octave','VERIFICADO',ov.get('status','')+'; definiciones y unidades, no validación del BEM'],['Scilab','VERIFICADO',sv.get('status','')+'; formulación angular independiente'],['CalculiX','PRELIMINAR','Benchmark analítico resuelto; elasticidad BASE sin resistencia admisible'],['Cavitación / fatiga / corrosión','NO CALCULADO','Faltan datos y modelos adecuados'],['Clasificación','SCREENING PARCIAL','Eficiencia con restricciones T/P/masa/CAD; estructura fuera del ranking']]
    baseline=next(r for r in rows if r['id']=='BASE')
    result={'case':case,'baseline':baseline,'alternatives':rows,'recommendation':recommendation,'curve_rows':curve,'checks':checks,'structure_status':elastic_status+'; SIN APROBACIÓN','hydro_method':hydro['method'],'dynamics_status':dv.get('scenario_outcome','VER REGISTRO DINÁMICO'),'motor_capacity_feasible':dv.get('motor_capacity_feasible'),'classification':'Calculated preliminary estimates + verified numerical implementation + explicitly pending analyses'}
    write(run/'combined_results.json',result)
    with (run/'comparison.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    return result

def hash_run(run):
    ignored={'temp','matlab_preferences','scilab_preferences','__pycache__'};target=run/'file_manifest.csv'
    files=sorted(p for p in run.rglob('*') if p.is_file() and p!=target and not any(x in ignored for x in p.relative_to(run).parts))
    with target.open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['relative_path','bytes','sha256']);
        for p in files:w.writerow([p.relative_to(run).as_posix(),p.stat().st_size,hashlib.sha256(p.read_bytes()).hexdigest()])

def demo():
    """Check published historical records without invoking an engineering engine."""
    directories=[ROOT/'examples/verified_runs'/name for name in ('baseline','rpm_1000','five_blades','diameter_study')]
    checks={directory.name:verify_saved_case(directory) for directory in directories}
    reference=read(directories[0]/'case.json')
    rpm_case=read(directories[1]/'case.json')
    geometry_case=read(directories[2]/'case.json')
    cad_base=next(m for m in read(directories[0]/'cad_results.json')['models'] if m['id']=='BASE')
    cad_rpm=next(m for m in read(directories[1]/'cad_results.json')['models'] if m['id']=='BASE')
    if reference['geometry']!=rpm_case['geometry'] or abs(cad_base['volume_m3']-cad_rpm['volume_m3'])/cad_base['volume_m3']>1e-4:
        raise ValueError('Historical RPM-only geometry invariant failed')
    if (reference['operation']['rpm'],rpm_case['operation']['rpm'])!=(900,1000):
        raise ValueError('Required historical RPM change is absent')
    if reference['geometry']['blades']!=4 or geometry_case['geometry']['blades']!=5 or geometry_case['geometry']['pitch_ratio']!=.85:
        raise ValueError('Required historical geometry change is absent')
    (ROOT/'runs').mkdir(exist_ok=True)
    run=ROOT/'runs'/('demo_'+dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:8])
    run.mkdir()
    # Copy only allowlisted result data; never import arbitrary executable files.
    source=directories[0]
    for name in ('case.json','hydro_results.json','cad_results.json','structure_results.json','dynamics_result.json','octave_verification.json','scilab_verification.json','hydro_curves.csv'):
        shutil.copy2(source/name,run/name)
    combine(run,reference)
    build_workbook(run/'CantaX_Propeller_Resultados.xlsx',reference,run)
    summary={'status':'PASS','mode':'SAVED_EXAMPLE_CONSISTENCY_ONLY','case_checks':checks,'run_directory':run.name,'workbook':'CantaX_Propeller_Resultados.xlsx','native_engines_executed':False,'formula_evaluation':'Open in Excel to recalculate; openpyxl does not evaluate formulas','scope':'Saved numerical examples are historical execution evidence, not new BEM/CAD/FEM runs or physical validation'}
    write(run/'demo_verification.json',summary)
    hash_run(run)
    print(json.dumps(summary,indent=2));return 0

def main():
    p=argparse.ArgumentParser(description='CantaX local engineering orchestration; use --demo without native engineering engines.')
    mode=p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--demo',action='store_true')
    mode.add_argument('--run',action='store_true')
    mode.add_argument('--create-input',action='store_true')
    mode.add_argument('--check-tools',action='store_true')
    p.add_argument('--workbook',default=str(ROOT/'CantaX_Propeller_Lab.xlsx'));p.add_argument('--diameter',type=float);p.add_argument('--rpm',type=float);p.add_argument('--blades',type=int);p.add_argument('--pitch-ratio',type=float);p.add_argument('--tag',default='case');p.add_argument('--diameter-sweep',action='store_true');p.add_argument('--no-update-panel',action='store_true');args=p.parse_args()
    if args.demo:return demo()
    if args.create_input:
        print(build_workbook(ROOT/'CantaX_Propeller_Lab.xlsx'));return 0
    if args.check_tools:
        print(json.dumps({name:str(executable(name,required=False)) if executable(name,required=False) else 'NOT FOUND' for name in ('powershell','freecad','matlab','octave','scilab','gmsh','calculix','poppler')},indent=2));return 0
    if os.name!='nt':raise RuntimeError('Full native Excel/engineering pipeline requires Windows; --demo is portable')
    engines=require_engines()
    PS,FREECAD,MATLAB,OCTAVE,SCILAB=[engines[name] for name in ('powershell','freecad','matlab','octave','scilab')]
    # Preflight all engines before creating a run or launching licensed software.
    source=Path(args.workbook).resolve()
    if not source.is_relative_to(ROOT) or not source.is_file():raise ValueError('Input workbook must be an existing file within CantaX_Propeller_Lab')
    preflight_xlsx(source)
    tag=''.join(x for x in args.tag if x.isalnum() or x in '-_')[:25]
    (ROOT/'runs').mkdir(exist_ok=True)
    run=ROOT/'runs'/(dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+tag+'_'+uuid.uuid4().hex[:8]);run.mkdir()
    pipe=Pipeline(run)
    try:
        shutil.copy2(source,run/'input.xlsx');source_hash=hashlib.sha256((run/'input.xlsx').read_bytes()).hexdigest()
        pipe.manifest.update(source_workbook=str(source),source_workbook_sha256=source_hash);pipe.save()
        snapshot=run/'config_snapshot';snapshot.mkdir()
        for cfg in (ROOT/'config').glob('*.json'):
            if cfg.name not in {'latest_run.json','executables.local.json','executables.example.json'}:shutil.copy2(cfg,snapshot/cfg.name)
        source_snapshot=run/'source_snapshot';source_snapshot.mkdir()
        for script in PYSCRIPT.iterdir():
            if script.is_file():shutil.copy2(script,source_snapshot/script.name)
        psbase=[PS,'-NoProfile','-NonInteractive','-STA','-File',PYSCRIPT/'excel_io.ps1','-WorkbookPath',run/'input.xlsx','-RunDir',run,'-Mode','Read']
        if args.diameter is not None:psbase+=['-SetDiameter',str(args.diameter)]
        if args.rpm is not None:psbase+=['-SetRPM',str(args.rpm)]
        if args.blades is not None:psbase+=['-SetBlades',str(args.blades)]
        if args.pitch_ratio is not None:psbase+=['-SetPitchRatio',str(args.pitch_ratio)]
        pipe.stage('excel_read',psbase,240);pipe.accepted('excel_read','excel_read_result.json',['PASS','passed','verified'])
        case=validate_case(read(run/'case.json'));write(run/'family.json',family(case,args.diameter_sweep))
        write(run/'source_versions.json',{'script_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(source_snapshot.iterdir()) if p.is_file()},'config_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(snapshot.iterdir()) if p.is_file()},'input_sha256':hashlib.sha256((run/'input.xlsx').read_bytes()).hexdigest(),'original_integrations':'Read/reused only; parent scripts unchanged'})
        pipe.stage('freecad',[FREECAD,'--user-cfg',run/'freecad_user.cfg','--system-cfg',run/'freecad_system.cfg',PYSCRIPT/'generate_cad.py'],600)
        cad=pipe.accepted('freecad','cad_results.json',['verified']);base=next(m for m in cad['models'] if m['id']=='BASE')
        prop_i=base['axial_mass_inertia_per_density_m5']*case['material_density_kgm3']
        if case['dynamic']['shaft_inertia_kgm2']<prop_i:raise ValueError('Input total shaft inertia is smaller than the generated propeller inertia')
        write(run/'inertia_check.json',{'propeller_inertia_kgm2':prop_i,'input_total_inertia_kgm2':case['dynamic']['shaft_inertia_kgm2'],'passed':True,'classification':'Total shaft inertia is a user scenario; CAD contribution is geometrically derived'})
        mscript=str(PYSCRIPT/'run_hydro.m').replace("'","''")
        pipe.stage('matlab_simulink',[MATLAB,'-wait','-nosplash','-logfile',run/'matlab_native.log','-batch',"run('"+mscript+"')"],900)
        hydro=pipe.accepted('matlab_simulink','hydro_results.json',['passed']);dyn=read(run/'dynamics_result.json')
        if dyn.get('status') not in ['passed','PASS']:raise RuntimeError('Simulink result did not pass')
        pipe.stage('gmsh_calculix',[PYTHON,PYSCRIPT/'mesh_and_structure.py','--run-dir',run,'--case',run/'case.json','--step',base['artifacts']['step'],'--cad-volume-m3',str(base['volume_m3']),'--candidate-id','BASE','--fem','--sections',run/'hydro_sections.csv'],900)
        pipe.accepted('gmsh_calculix','structure_results.json',['PASS'])
        with (run/'verification_input.csv').open('w',newline='',encoding='utf-8') as f:
            w=csv.writer(f);w.writerow(['rpm','Va_mps','D_m','rho','T_N','Q_Nm','KT','KQ','P_W','eta0','J'])
            for r in hydro['alternatives']:
                if r['valid_domain']:w.writerow([r['rpm'],r['Va_mps'],r['D_m'],case['operation']['water_density_kgm3'],r['T_N'],r['Q_Nm'],r['KT'],r['KQ'],r['P_W'],r['eta0'],r['J']])
        pipe.stage('octave',[OCTAVE,'--no-gui','--no-history','--no-init-file','--no-site-file','--quiet',PYSCRIPT/'verify_octave.m'],180);pipe.accepted('octave','octave_verification.json',['PASS'])
        scihome=run/'scilab_preferences';scihome.mkdir();pipe.stage('scilab',[SCILAB,'-nb','-nouserstartup','-noatomsautoload','-scihome',scihome,'-f',PYSCRIPT/'verify_scilab.sce'],180);pipe.accepted('scilab','scilab_verification.json',['PASS'])
        combine(run,case)
        pipe.stage('cad_images',[PYTHON,PYSCRIPT/'render_models.py','--run-dir',run],180)
        pipe.stage('results_excel',[PYTHON,PYSCRIPT/'build_workbook.py','--run-dir',run],240)
        pipe.stage('excel_verify',[PS,'-NoProfile','-NonInteractive','-STA','-File',PYSCRIPT/'excel_io.ps1','-WorkbookPath',run/'CantaX_Propeller_Resultados.xlsx','-RunDir',run,'-Mode','Verify'],240);pipe.accepted('excel_verify','excel_result_verification.json',['PASS','passed','verified'])
        pipe.stage('report_pdf',[PYTHON,PYSCRIPT/'report.py','--run-dir',run],240)
        if not args.no_update_panel:
            pipe.manifest['panel_refresh']=refresh_panel(run,source,source_hash)
        pipe.manifest.update(status='COMPLETED',completed_utc=dt.datetime.now(dt.timezone.utc).isoformat());pipe.save();hash_run(run)
        write(ROOT/'config/latest_run.json',{'run_directory':str(run),'status':'COMPLETED','results_workbook':str(run/'CantaX_Propeller_Resultados.xlsx'),'pdf':str(run/'CantaX_Propeller_Informe.pdf')})
        print(json.dumps({'status':'COMPLETED','run_directory':str(run)},ensure_ascii=False),flush=True);return 0
    except Exception as exc:
        pipe.manifest.update(status='FAILED',error=f'{type(exc).__name__}: {exc}',traceback=traceback.format_exc());pipe.save();hash_run(run)
        print(json.dumps({'status':'FAILED','run_directory':str(run),'error':str(exc)},ensure_ascii=False),flush=True);return 1

if __name__=='__main__':raise SystemExit(main())
