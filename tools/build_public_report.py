"""Build an English publication report from reviewed saved numerical examples.

No native calculation is performed. PDF fonts are standard, unembedded fonts.
"""
from pathlib import Path
import json
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate,Paragraph,Table,TableStyle,Image,PageBreak,Spacer

ROOT=Path(__file__).resolve().parents[1]
WIDTH=A4[0]-84
NAVY=colors.HexColor('#132C40');TEAL=colors.HexColor('#007E87');PALE=colors.HexColor('#eef4f6')
def read(case,name):return json.loads((ROOT/'examples/verified_runs'/case/name).read_text(encoding='utf-8'))
def n(value,digits=3):return 'NOT CALCULATED' if value is None else (f'{value:.2e}' if value and abs(value)<.0005 else f'{value:.{digits}f}')

def build():
    output=ROOT/'docs/cantax-technical-report.pdf'
    if output.exists():raise FileExistsError('Preserve the previous report before rebuilding')
    hydro=read('baseline','hydro_results.json');cad=read('baseline','cad_results.json');structure=read('baseline','structure_results.json')
    study=read('diameter_study','combined_results.json');base=hydro['baseline'];mesh=structure['meshes'];elastic=structure['structure']
    styles={'title':ParagraphStyle('t',fontName='Helvetica-Bold',fontSize=28,leading=32,textColor=NAVY,spaceAfter=14),'h1':ParagraphStyle('h1',fontName='Helvetica-Bold',fontSize=20,leading=24,textColor=NAVY,spaceAfter=12),'h2':ParagraphStyle('h2',fontName='Helvetica-Bold',fontSize=11,leading=14,textColor=TEAL,spaceBefore=9,spaceAfter=5),'body':ParagraphStyle('b',fontName='Helvetica',fontSize=9,leading=13,textColor=NAVY,spaceAfter=8),'small':ParagraphStyle('s',fontName='Helvetica',fontSize=7.7,leading=10.5,textColor=NAVY,spaceAfter=6),'head':ParagraphStyle('th',fontName='Helvetica-Bold',fontSize=7.5,leading=10,textColor=colors.white),'cell':ParagraphStyle('tc',fontName='Helvetica',fontSize=7.5,leading=10,textColor=NAVY)}
    story=[]
    def text(value,style='body'):story.append(Paragraph(value,styles[style]))
    def page(title):
        if story:story.append(PageBreak())
        text(title,'h1')
    def table(headers,rows,widths=None):
        values=[[Paragraph(escape(str(v)),styles['head']) for v in headers]]+[[Paragraph(escape(str(v)),styles['cell']) for v in row] for row in rows]
        tb=Table(values,colWidths=widths or [WIDTH/len(headers)]*len(headers),repeatRows=1,hAlign='LEFT')
        tb.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),NAVY),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,PALE]),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]));story.extend([tb,Spacer(1,8)])
    def picture(path,width=WIDTH,height=250):
        from PIL import Image as PI
        with PI.open(ROOT/path) as im:w,h=im.size
        scale=min(width/w,height/h);story.append(Image(str(ROOT/path),w*scale,h*scale));story.append(Spacer(1,9))

    text('CantaX<br/>Propeller Lab','title');text('Parametric Marine Propeller Engineering','h2')
    text('V1.0 publication report | 12 October 2026','small');picture('media/hero.png',height=300)
    text('A repeatable Excel-to-CAD-to-calculation-to-report workflow, developed with AI assistance and documented numerical checks. This report uses real saved synthetic engineering outputs. Author review and physical validation remain necessary before engineering decisions.')
    table(['Integration verified','Preliminary models','Not implemented/validated'],[['Native CAD and file reopen; Excel input/recalculation; native solver execution','Analytical BEM, shaft-control scenario, BASE linear elasticity','Validated 3D CFD, cavitation, fatigue, corrosion, allowable stress and service certification']])
    text('Independent use requires the documented local programs and licenses. No vendor application, installer, runtime or font file is distributed.','small')

    page('01 | Calculated results and input changes')
    text('All three cases use D=0.300 m, Va=2 m/s, seawater density 1025 kg/m3 and reference bronze density 7640 kg/m3. Figures are model estimates; decimal precision permits reproducibility checks, not a claim of physical accuracy.')
    rows=[]
    for label in ['baseline','rpm_1000','five_blades']:
        c=read(label,'case.json');h=read(label,'hydro_results.json')['baseline'];m=next(x for x in read(label,'cad_results.json')['models'] if x['id']=='BASE')
        rows.append([label,c['geometry']['blades'],n(c['geometry']['pitch_ratio'],2),int(c['operation']['rpm']),n(h['T_N'],2),n(h['Q_Nm'],3),n(h['P_W'],2),n(h['eta0'],4),n(m['mass_kg'],4)])
    table(['Case','B','P/D','RPM','T N','Q Nm','P W','eta','kg'],rows,[82,20,34,42,65,63,72,65,WIDTH-443])
    text('RPM change: the geometry signature and CAD volume remain identical at 0.0003564570746956503 m3. Geometry change: B=5 and P/D=0.85 at 900 RPM gives 0.000319203190234742 m3. CAD, STEP, mesh and numerical artifact hashes differ; mass/volume decrease by 10.4512%.','small')
    picture('media/propeller-comparison.png',height=240)
    text('At fixed nominal expanded area ratio, increasing blade count reduces individual chord. A lower mass does not establish a stronger or more efficient propeller.','small')

    page('02 | Analytical BEM and physical plausibility')
    text('The axial blade-element/momentum model solves annular induced velocities with Prandtl tip/hub corrections. Symmetric thin-airfoil lift Cl=2*pi*alpha and Cd=2*Cf from ITTC-1957 friction are explicit analytical closures. No measured section polars, pressure/separation drag, transition, roughness, wake, cavitation or free-surface validation are supplied.')
    table(['Definition','Equation / baseline value'],[['Rotation','n=RPM/60; omega=2*pi*n'],['Advance ratio','J=Va/(n*D) = '+n(base['J'],9)],['Thrust coefficient','KT=T/(rho*n^2*D^4) = '+n(base['KT'],9)],['Torque coefficient','KQ=Q/(rho*n^2*D^5) = '+n(base['KQ'],9)],['Power / efficiency','P=omega*Q; eta=T*Va/P = '+n(base['eta0'],9)]],[143,WIDTH-143])
    text('An optimistic full ideal actuator disk gives induced velocity 0.848720617 m/s and minimum power 998.046 W for the stated thrust. The estimate 1277.563 W exceeds this lower bound; its efficiency is below the ideal 0.70207. This elementary coherence check does not calibrate the propeller model.')
    text('Radial refinement from 60 to 120 annuli changes T by 0.02384% and Q by 0.02732%. Guarded positive-thrust outputs are withheld outside the declared domain. Numerical convergence of these equations is distinct from physical validation.','small')
    picture('media/hydro-curves.png',height=265)

    page('03 | CAD, geometry and mesh evidence')
    text('FreeCAD Python creates original section curves, radial lofts, rotated blades and a fused hub, then clips the tip envelope. Geometry is parameterized by the input/scripts. The saved FCStd examples are editable generated solids, not a native feature-tree configurator. FCStd and STEP are reopened and checked for validity, closedness, solid count, bounding box and volume.')
    m=next(x for x in cad['models'] if x['id']=='BASE')
    table(['BASE quantity','Calculated value'],[['Closed solid','Valid / closed / one solid'],['Volume',n(m['volume_m3'],12)+' m3'],['Reference mass',n(m['mass_kg'],6)+' kg'],['Nominal EAR',n(m['geometry']['expanded_area_ratio'],3)],['Clipped strip EAR estimate',n(m['clipped_EAR_strip_estimate'],6)],['Axial CAD inertia',n(m['axial_mass_inertia_kgm2'],7)+' kg m2']],[210,WIDTH-210])
    text('CAD uses millimetres internally; published lengths/areas/volumes convert to m/m2/m3. BEM uses nominal radial strips rather than the exact clipped 3D blade. Skew, rake, thickness and tip clipping are geometrically present but not resolved as 3D flow effects.','small')
    table(['Mesh','Tetrahedra','Volume error','Inverted / degenerate','q < 0.05'],[[i+1,x['tetrahedra'],n(x['relative_volume_error']*100,3)+'%',str(x['negative_orientation_elements'])+' / '+str(x['degenerate_elements']),x['quality']['elements_below_0_05']] for i,x in enumerate(mesh)])
    picture('media/mesh.png',height=270)

    page('04 | Preliminary linear elastic analysis')
    text('CalculiX 2.22 first solves a synthetic uniaxial cube benchmark: 100 N, expected stress 10000 Pa, displacement 5e-9 m and reaction -100 N. The solver output agrees within the stated tolerance. This verifies one analytic elastic problem, not a propeller design.')
    text('For BASE, Gmsh tetrahedra feed C3D4 linear isotropic elasticity with an ideal rigid hub constraint. Annular BEM thrust/torque become conservative equivalent nodal loads, with centrifugal loading from mesh mass and RPM. The distribution is not a computed suction/pressure field.')
    table(['BASE elastic result','Value / interpretation'],[['Material','NAB C95800: public typical density 7640 kg/m3, E=113.7635 GPa, nu=0.32'],['Maximum displacement',n(elastic['maximum_displacement_m']*1e6,3)+' micrometres'],['Integration-point von Mises',n(elastic['maximum_integration_point_von_mises_Pa']/1e6,3)+' MPa'],['Relative force residual',n(elastic['force_balance_relative_norm'])],['Relative moment residual',n(elastic['moment_balance_relative_norm'])],['Strength/fatigue/corrosion/service','NOT CALCULATED; no allowable stress or certified safety factor']],[204,WIDTH-204])
    text('Three low-quality slivers per BASE mesh remain recorded. Two mesh sizes demonstrate geometric volume variation only; they do not establish convergence of displacement or stress. Hub fillets, real supports, manufacturing route, fatigue loads and admissibles are required before structural approval.')
    text('Material properties are a small set of attributed reference facts, not supplier certification or a redistributed material database. 316L and 6061 options retain absent constitutive/service properties as NOT CALCULATED.','small')

    page('05 | Simulink scenario and motor limits')
    text('An actual Simulink SLX stores its model workspace, steady BEM torque lookup and scenario parameters. It simulates startup, a +10% RPM reference step and a +20% load step. Saving, reopening and resimulating gives maximum trace difference zero. Inertia, PI gains, torque cap and extra load are explicit user scenarios.')
    rows=[]
    for label in ['baseline','rpm_1000','five_blades']:
        d=read(label,'dynamics_result.json');rows.append([label,n(d['final_reference_rpm'],1),n(d['final_rpm'],2),n(d['requested_steady_torque_Nm'],3),str(d['motor_capacity_feasible']),n(100*d['relative_energy_balance_error'],4)+'%'])
    table(['Case','Final ref RPM','Final RPM','Requested Nm','Motor feasible','Energy error'],rows)
    text('The 1000-RPM case requests 27.605 Nm against a 25-Nm motor cap after the load step, ending at 1057.54 RPM instead of 1100. The five-blade case also exceeds steady motor capacity. The software preserves these unfavorable outcomes rather than forcing tracking to pass.','small')
    picture('media/dynamics.png',height=350)
    text('Below the accepted positive-thrust branch, startup uses an explicit Q proportional to omega-squared surrogate. It does not model windmilling, dynamic inflow, motor electrics, gearbox dynamics, ventilation or torsional response.','small')

    page('06 | Thirteen-configuration screening')
    text('The study contains BASE plus 12 combinations: D=0.291/0.309 m, B=3/4/5 and P/D=0.72/0.88. All use the same reference operating inputs and EAR=0.55. Each row has its own CAD and calculated BEM results.')
    table(['ID','D m','B','P/D','T N','P W','eta','kg','Rank'],[[a['id'],n(a['diameter_m'],3),a['blades'],n(a['pitch_ratio'],2),n(a['T_N'],1),n(a['P_W'],1),n(a['eta0'],4),n(a['mass_kg'],3),a['screening_rank'] or '-'] for a in study['alternatives']],[112,48,20,40,65,70,55,60,WIDTH-470])
    text('The ranking sorts efficiency for candidates satisfying the declared thrust/power/mass/CAD guards. D291_B3_P072 is first in this sample: 215.74 N, 753.54 W, eta=0.572596 and mass=2.907484 kg. Its elastic analysis is NOT CALCULATED.')
    text('Cavitation, allowable stress, fatigue, corrosion, manufacturing and vessel integration are outside the ranking. Neither global optimality nor a recommendation for fabrication is claimed.','small')

    page('07 | Reproducibility and release boundaries')
    text('The release includes original source, configurable application adapters, selected sanitized JSON/CSV results, generated CAD examples, real figures and this report. Raw private logs, source-machine paths, tokens, proprietary application binaries, runtimes, installers, font files and third-party publications are excluded.')
    table(['Verification','What it establishes'],[['12 Python unit tests','Definitions/input guards, workbook structure and process/environment safety'],['Saved demonstration','Four real historical cases; 260 numerical identities; 52 historical solid records'],['Public-distribution native run','Fresh Excel input -> FreeCAD -> MATLAB/Simulink -> Gmsh/CalculiX -> Octave/Scilab -> native Excel -> PDF'],['PDF generation','ReportLab standard fonts and page tracking; pypdf removed; optional external Poppler rendering'],['Human engineering review','Required before decisions; numerical/visual checks do not certify performance']],[160,WIDTH-160])
    text('The full workflow requires Windows, Excel and MATLAB/Simulink licenses plus installed FreeCAD, Gmsh, CalculiX, Octave and Scilab. The saved-example demonstration requires only the Python dependencies. No AI API is used at runtime. MATLAB may contact its licensing service.','small')
    text('Primary model/material references: ITTC open-water/friction procedures; thin-airfoil theory; Prandtl BEM corrections; Copper Development Association C95800; Outokumpu 316L; Hydro 6061. Full source links and limits are in docs/BEM.md, docs/STRUCTURAL_ANALYSIS.md and config/hydro_references.json. No upstream PDF or vendor documentation is included.','small')
    text('Next steps: section polars and open-water experiments; CFD/cavitation validation; converged structural models and real admissibles; uncertainty-aware constrained selection; independent packaging and license review. V1.0 remains a preliminary engineering demonstrator.','small')
    text('<link href="https://github.com/aaronexposito0-creator/cantax-propeller-lab" color="#007E87">Repository: aaronexposito0-creator/cantax-propeller-lab</link>','small')
    pages=[0]
    def footer(canvas,doc):
        pages[0]=max(pages[0],doc.page);canvas.saveState();canvas.setStrokeColor(TEAL);canvas.line(42,39,A4[0]-42,39);canvas.setFont('Helvetica',7);canvas.setFillColor(NAVY);canvas.drawString(42,26,'CantaX | Calculated preliminary estimates; no service certification');canvas.drawRightString(A4[0]-42,26,str(doc.page));canvas.restoreState()
    doc=SimpleDocTemplate(str(output),pagesize=A4,rightMargin=42,leftMargin=42,topMargin=42,bottomMargin=52,title='CantaX Propeller Lab - Technical Publication Report',author='CantaX contributors')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    if pages[0]!=8:raise RuntimeError('Unexpected report pagination: '+str(pages[0]))
    print(json.dumps({'pages':pages[0],'output':output.relative_to(ROOT).as_posix(),'calculations_executed':False,'font_programs_embedded':False}))

if __name__=='__main__':build()
