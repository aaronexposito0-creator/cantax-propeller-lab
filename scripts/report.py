"""Create a local engineering PDF from an already executed CantaX run.

Uses installed ReportLab/Pillow and optional configured Poppler. Refuses overwrite.
No network calls, PDF templates, invented results or Office security changes.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, math, subprocess
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image as PILImage, ImageOps, ImageDraw
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from runtime_config import executable
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether

BASE=Path(__file__).resolve().parents[1]
NAVY=colors.HexColor('#132C40');TEAL=colors.HexColor('#007E87');GRAY=colors.HexColor('#4B5F6B');PALE=colors.HexColor('#EEF4F6');GOLD=colors.HexColor('#F5EBCB')
WIDTH=A4[0]-84

def read_json(path, default=None):
    return json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else ({} if default is None else default)

def number(value, digits=3):
    try:
        v=float(value)
        if not math.isfinite(v): return 'NO CALCULADO'
        # Preserve nonzero residuals that fixed-point rounding would hide.
        if v and abs(v)<.5*10**(-digits): return f'{v:.2e}'
        return f'{v:,.{digits}f}'.replace(',', ' ')
    except (ValueError,TypeError): return 'NO CALCULADO'

def flag(value): return 'Sí' if value is True else ('No' if value is False else 'Pendiente')

def scaled(value,factor=100,digits=4):
    return number(float(value)*factor,digits) if value is not None else 'NO CALCULADO'

def recommendation_limits(value):
    translations={
        'No experimental polar or vessel wake':'Faltan polares experimentales y la estela del buque.',
        'Nominal pre-clipped strip geometry in BEM':'El BEM utiliza la geometría nominal anterior al recorte CAD.',
        'Strength/fatigue/corrosion/cavitation uncalculated; elastic FEM only BASE':'Resistencia, fatiga, corrosión y cavitación pendientes; solo BASE tiene cálculo elástico preliminar.',
        'Candidate winner needs its own converged structural analysis':'La alternativa seleccionada necesita su propio estudio estructural con convergencia.',
    }
    values=value if isinstance(value,list) else [value]
    return ' '.join(translations.get(str(v),str(v)) for v in values if v is not None)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-dir',required=True);args=parser.parse_args()
    run=Path(args.run_dir).resolve()
    if not run.is_relative_to((BASE/'runs').resolve()): raise ValueError('Output must be a new run inside this laboratory')
    out=run/'CantaX_Propeller_Informe.pdf'
    if out.exists(): raise FileExistsError(f'Refusing to overwrite {out}')
    combined=read_json(run/'combined_results.json');case=read_json(run/'case.json')
    if not combined or not case: raise ValueError('Executed combined_results.json and case.json are required')
    hydro=read_json(run/'hydro_results.json');cad=read_json(run/'cad_results.json');struct=read_json(run/'structure_results.json');dynamic=read_json(run/'dynamics_result.json')
    octave=read_json(run/'octave_verification.json');scilab=read_json(run/'scilab_verification.json')
    material_source=run/'config_snapshot/materials.json'
    reference_source=run/'config_snapshot/hydro_references.json'
    if not material_source.exists():material_source=BASE/'config/materials.json'
    if not reference_source.exists():reference_source=BASE/'config/hydro_references.json'
    materials=read_json(material_source);refs=read_json(reference_source)
    alternatives=combined.get('alternatives',[]);models=cad.get('models',[])
    b=hydro.get('baseline',{});cb=next((m for m in models if m.get('id')=='BASE'), models[0] if models else {})
    recommendation=combined.get('recommendation',{});g=case.get('geometry',{});op=case.get('operation',{})
    styles={
        'title':ParagraphStyle('Title',fontName='Helvetica-Bold',fontSize=29,leading=33,textColor=NAVY,spaceAfter=14),
        'h1':ParagraphStyle('H1',fontName='Helvetica-Bold',fontSize=20,leading=25,textColor=NAVY,spaceAfter=13),
        'h2':ParagraphStyle('H2',fontName='Helvetica-Bold',fontSize=11.4,leading=15,textColor=TEAL,spaceBefore=10,spaceAfter=6),
        'body':ParagraphStyle('Body',fontName='Helvetica',fontSize=9.2,leading=13.2,textColor=NAVY,spaceAfter=8),
        'small':ParagraphStyle('Small',fontName='Helvetica',fontSize=7.8,leading=10.8,textColor=GRAY,spaceAfter=6),
        'cell':ParagraphStyle('Cell',fontName='Helvetica',fontSize=7.7,leading=10,textColor=NAVY),
        'header':ParagraphStyle('Header',fontName='Helvetica-Bold',fontSize=7.7,leading=10,textColor=colors.white),
        'equation':ParagraphStyle('Equation',fontName='Helvetica',fontSize=9,leading=14,textColor=NAVY,backColor=PALE,borderPadding=7,spaceAfter=9),
    }
    story=[]
    def p(text,style='body'): return Paragraph(str(text),styles[style])
    def text(text,style='body'): story.append(p(text,style))
    def heading(title):text(title,'h2')
    def page(title):
        if story:story.append(PageBreak())
        text(title,'h1')
    def table(headers,rows,widths=None):
        widths=widths or [WIDTH/len(headers)]*len(headers)
        data=[[p(escape(str(h)),'header') for h in headers]]
        data.extend([[p(escape(str(v)),'cell') for v in row] for row in rows])
        tb=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
        tb.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),NAVY),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,PALE]),('LINEBELOW',(0,0),(-1,0),.7,TEAL),('LINEBELOW',(0,-1),(-1,-1),.5,colors.HexColor('#CCDAE0'))]))
        story.extend([tb,Spacer(1,8)])
    def picture(path,maxw=WIDTH,maxh=300):
        if not path.exists():return p('Imagen no disponible: '+escape(path.name),'small')
        with PILImage.open(path) as im:w,h=im.size
        scale=min(maxw/w,maxh/h);return Image(str(path),width=w*scale,height=h*scale,hAlign='CENTER')
    def image(path,caption,maxh=300):
        story.extend([picture(path,maxh=maxh),Spacer(1,5),p(caption,'small')])
    def link(url,title):return f'<link href="{escape(url)}" color="#007E87">{escape(title)}</link>'
    def slim_check(record):
        return f"{record.get('status','NO EJECUTADO')}; {record.get('numeric_checks','-')} comprobaciones; tolerancia relativa {record.get('relative_tolerance','-')}"

    # 1. Executive result and scope.
    text('CantaX<br/>Propeller Lab','title');text('V1.0 | Informe de ejecución local','h2')
    text('CAD paramétrico, BEM preliminar, dinámica del eje y comprobación numérica independiente.','body')
    text('Ejecución: '+escape(run.name)+'<br/>Fecha de generación UTC: '+datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M'),'small')
    heading('Resultado que acredita esta ejecución')
    text(f"Se registran {len(models)} geometrías CAD y {len(alternatives)} alternativas evaluadas. Los estados de cada programa proceden de sus archivos de salida reales. La clasificación distingue resultados verificados de integración, estimaciones de modelos y análisis pendientes.")
    table(['Caso BASE','Valor','Naturaleza'],[
        ['J',number(b.get('J'),6),'Definición adimensional'],['Empuje / par',number(b.get('T_N'))+' N / '+number(b.get('Q_Nm'))+' Nm','Estimación BEM'],['Potencia al eje',number(b.get('P_W'),2)+' W','P = omega Q'],['Eficiencia eta0',number(b.get('eta0'),4),'Estimación sin ensayo'],['Masa CAD',number(combined.get('baseline',{}).get('mass_kg'))+' kg','Volumen CAD x densidad típica'],['Dominio declarado BEM',flag(b.get('valid_domain')),'Guardas de aproximación; no certificación']], [126,174,WIDTH-300])
    heading('Selección condicional')
    selected_id=recommendation.get('id')
    scope=recommendation.get('scope','No existe una selección respaldada en esta ejecución.')
    if scope=='Hydrodynamic/mass screening inside analytical model guards; not a global structural/cavitation ranking':
        scope='Cribado hidrodinámico y de masa dentro de las guardas del modelo analítico. La estructura y la cavitación permanecen fuera de esta ordenación.'
    text('<b>'+escape(str(selected_id if selected_id is not None else 'SIN CANDIDATO'))+':</b> '+escape(str(scope)))
    text(escape(recommendation_limits(recommendation.get('limitations','La selección es un cribado del modelo: no acredita restricciones estructurales ni servicio naval.'))),'small')
    heading('Alcance de interpretación')
    text('No hay ensayos de aguas libres ni polares medidas de los perfiles. El BEM usa sustentación analítica y fricción aproximada; la dinámica hereda esas hipótesis. El mallado acredita geometría y elementos. El cálculo elástico, cuando existe, es preliminar y no aporta un factor de seguridad certificado. La revisión y decisiones de ingeniería corresponden al responsable humano.')
    text('Preparación y automatización asistidas por IA. Los resultados numéricos identifican el programa que los calculó.','small')

    # 2. Input contract.
    page('01 | Entradas y unidades')
    text('El caso es un escenario de demostración explícito, no datos medidos de un buque. Los valores se leen de Excel y se conservan como case.json. Densidad, viscosidad y presión de vapor son entradas; la salinidad no activa un modelo termofísico implícito.')
    table(['Geometría','Entrada','Operación','Entrada'],[
        ['Diámetro',number(g.get('diameter_m'))+' m','RPM',number(op.get('rpm'),1)],['Número de palas',g.get('blades','-'),'Velocidad de avance',number(op.get('advance_mps'))+' m/s'],['P/D',number(g.get('pitch_ratio')),'Densidad',number(op.get('water_density_kgm3'),1)+' kg/m3'],['EAR nominal',number(g.get('expanded_area_ratio')),'Viscosidad cinemática',number(op.get('water_kinematic_viscosity_m2s'))+' m2/s'],['Espesor/cuerda nominal',number(g.get('thickness_ratio')),'Potencia disponible',number(op.get('available_power_W'),1)+' W'],['Skew / rake',number(g.get('skew_deg'),1)+' deg / '+number(g.get('rake_ratio')),'Empuje requerido',number(op.get('required_thrust_N'),1)+' N'],['Núcleo / D',number(g.get('hub_ratio')),'Profundidad del eje',number(op.get('shaft_depth_m'))+' m'],['Material',case.get('material','-'),'Salinidad',number(op.get('salinity_ppt'),1)+' ppt']],[112,120,128,WIDTH-360])
    heading('Distribuciones radiales parametrizadas')
    radial=case.get('radial_distribution',[])
    table(['r/R','Peso cuerda','Factor paso','Factor espesor','Factor skew','Factor rake'],[[number(r.get(k),3) for k in ['r_R','chord_weight','pitch_factor','thickness_factor','skew_factor','rake_factor']] for r in radial])
    heading('Contrato de entradas')
    text('Unidades SI en JSON y cálculos; FreeCAD usa mm internamente y registra la conversión. La distribución de cuerda se normaliza con el EAR nominal. El lanzador crea un directorio nuevo, valida rangos y datos obligatorios, registra errores y preserva entradas/salidas anteriores. El libro XLSX no necesita macros y no se cambia la seguridad de Office.')
    text('Las propiedades de materiales son referencias públicas, separadas de propiedades certificadas de una colada o producto. Ningún valor de tensión admisible o límite de fatiga se presupone.','small')

    # 3. CAD evidence.
    page('02 | Geometría CAD real')
    image(run/'images/BASE_iso.png','BASE: render de teselación del sólido generado por FreeCAD. No es una captura de su interfaz ni un render CFD.',maxh=300)
    pair=Table([[picture(run/'images/BASE_front.png',WIDTH/2-6,155),picture(run/'images/BASE_side.png',WIDTH/2-6,155)]],colWidths=[WIDTH/2]*2)
    story.extend([pair,Spacer(1,5),p('Vistas axial y lateral derivadas de la misma geometría CAD. Eje del propulsor +Z.','small')])
    table(['Comprobación BASE','Resultado'],[['Sólido válido / cerrado',flag(cb.get('valid'))+' / '+flag(cb.get('closed'))],['Volumen exacto CAD',number(cb.get('volume_m3'),9)+' m3'],['Recorte de volumen de pala en punta',scaled(cb.get('tip_clipped_volume_fraction'))+' %'],['EAR estimado después del recorte',number(cb.get('clipped_EAR_strip_estimate'),6)],['Reapertura FCStd / STEP','Ver roundtrip_checks en cad_results.json']], [240,WIDTH-240])
    text('Se loftan perfiles simétricos con espesor, paso, cuerda, skew y rake variables, se une el núcleo y se recorta a radio D/2. El coeficiente de borde de salida se modifica algebraicamente para cerrarlo: no se atribuyen polares medidas a esa variante geométrica. El BEM utiliza la cuerda nominal anterior al recorte, por lo que el modelo de cargas no reproduce exactamente la superficie CAD.','small')

    # 4. Family and conditional screening.
    page('03 | Familia y comparación')
    text('Cada fila recoge el número de palas, diámetro, paso y área expandida de su alternativa. Las restantes distribuciones proceden del caso. La tabla presenta los resultados disponibles con su estado; las eficiencias son estimaciones del mismo cierre analítico.')
    table(['ID','B','D m','P/D','EAR','T N','Q Nm','P W','eta0','Masa kg','#'],[[a.get('id','-'),a.get('blades',a.get('B','-')),number(a.get('diameter_m'),3),number(a.get('pitch_ratio'),2),number(a.get('expanded_area_ratio',a.get('EAR')),2),number(a.get('T_N'),1),number(a.get('Q_Nm'),2),number(a.get('P_W'),0),number(a.get('eta0'),3),number(a.get('mass_kg'),3),str(a.get('screening_rank') or '-')] for a in alternatives], [89,20,42,35,35,47,46,49,44,58,WIDTH-465])
    heading('Qué significa la ordenación')
    text('El rango de cribado puede utilizar eficiencia, empuje requerido, potencia disponible, masa y validez geométrica realmente calculadas. No representa una clasificación global estructural ni de servicio: no se sustituye una restricción pendiente por “cumple”. Consultar screening_feasible y las limitaciones de la recomendación en combined_results.json.')
    ids=[a.get('id') for a in alternatives if a.get('id')!='BASE']
    selected=[ids[i] for i in [0,len(ids)//2,len(ids)-1] if ids] if ids else []
    if selected:
        gallery=Table([[picture(run/f'images/{ident}_iso.png',WIDTH/3-7,140) for ident in selected]],colWidths=[WIDTH/3]*3)
        story.extend([gallery,p('Geometrías generadas: '+' | '.join(selected)+'. Renders de teselación CAD.','small')])
    text('La fuente íntegra conserva un registro por alternativa: validez CAD, volumen, reapertura, dominio BEM y resultados. Las restricciones de fatiga, corrosión, cavitación y admisibles permanecen pendientes.','small')

    # 5. Numerical method.
    page('04 | Modelo hidrodinámico')
    text('BEM axial de empuje positivo con dos velocidades inducidas por anillo. Va + u es la velocidad axial en el disco; omega r - v es la tangencial relativa. El v del código representa la mitad del giro inducido en la estela lejana. Se igualan las fuerzas de elemento de pala a los balances de cantidad de movimiento [R1].')
    text('W = sqrt[(Va + u)^2 + (omega r - v)^2]<br/>phi = atan2(Va + u, omega r - v); alpha = beta - phi<br/>dT/dr = 0.5 rho W^2 B c (Cl cos phi - Cd sin phi)<br/>dQ/dr = 0.5 rho W^2 B c r (Cl sin phi + Cd cos phi)<br/>dT/dr = 4 pi rho r F u (Va + u)<br/>dQ/dr = 4 pi rho r^2 F v (Va + u)','equation')
    heading('Cierre y fuentes')
    text('Cl = 2 pi alpha, aproximación de perfil delgado simétrico [R2]. Cd = 2 Cf con Cf = 0.075/(log10 Re - 2)^2 [R3]; usar esa línea de casco para las dos caras de un perfil es una hipótesis explícita de fricción, sin drag de presión, rugosidad ni separación. Re = W c / nu. Los factores de punta y núcleo de Prandtl multiplican el balance de momento [R4]. No se usan polares medidas ni curvas de serie sistemática.')
    text('J = Va/(n D); KT = T/(rho n^2 D^4); KQ = Q/(rho n^2 D^5)<br/>P = omega Q; eta0 = T Va/P = J KT/(2 pi KQ)','equation')
    heading('Guardas y verificación')
    table(['Control','Criterio / valor BASE'],[['Intervalo activo r/R',str(b.get('active_radial_interval_r_R','-'))],['Guardas de aproximación','0 <= alpha <= 10 deg; 0 <= u/Va <= 2; 0 <= v/(omega r) <= 0.5'],['Condiciones adicionales','Va y RPM > 0; Re >= 20000; espesor/c <= 0.12; T,Q > 0; eta0 < 1'],['Residuo normalizado máximo',number(b.get('max_normalized_residual'))],['Refinamiento radial T / Q',scaled(hydro.get('discretization_check',{}).get('relative_T_difference'),digits=5)+'% / '+scaled(hydro.get('discretization_check',{}).get('relative_Q_difference'),digits=5)+'%']], [145,WIDTH-145])
    text('Re >= 20000 es una guarda numérica, no prueba de régimen turbulento. “Dominio válido” significa cumplimiento de estas guardas, no validación física. Los puntos rechazados tienen métricas null y raw_estimates_excluded separado.','small')

    # 6. Real hydrodynamic curves.
    page('05 | Curvas y sensibilidad')
    image(run/'hydro_curves.png','Curvas calculadas por MATLAB para la geometría BASE. Los huecos corresponden a puntos rechazados. No son ensayos.',maxh=345)
    heading('Dependencia del caso y del cierre')
    text('Se perturbó ±5% diámetro, RPM, relación paso/diámetro y velocidad de avance, manteniendo el resto de entradas. Los resultados por perturbación están en hydro_results.json. Además se varió la pendiente Cl x0.8/x1.2 y el Cd x0.5/x2.0. Ese abanico revela sensibilidad a las hipótesis; no es un intervalo estadístico de confianza.')
    closure=hydro.get('closure_sensitivity',{}).get('results',[])
    table(['Escenario de cierre','T N','Q Nm','P W','eta0','Guardas'],[[r.get('id','-'),number(r.get('T_N'),2),number(r.get('Q_Nm'),3),number(r.get('P_W'),1),number(r.get('eta0'),4),flag(r.get('valid_domain'))] for r in closure])
    text('La incertidumbre física requiere polares/CFD contrastados o ensayos de aguas libres y estudio de Reynolds. No se evalúan estela de casco, inflow inclinado, superficie libre, cavitación, ventilación, roughness ni deformación. Skew/rake y el recorte CAD de punta no están resueltos hidrodinámicamente.','small')

    # 7. Real Simulink.
    page('06 | Dinámica Simulink')
    image(run/'dynamics.png','CantaX_Drive.slx: ejecución local real de arranque, incremento de consigna y cambio de carga.',maxh=330)
    text('I domega/dt = Qmotor - Qprop. Se utiliza un regulador PI con integral limitada y par saturado. El lookup lineal de carga viene de la rama estacionaria BEM aceptada. Inercia, ganancias y aumento de carga son entradas de escenario; no medidas del sistema mecánico ni un modelo eléctrico del motor.')
    sx=dynamic.get('startup_extrapolation',{})
    table(['Control','Resultado / escenario'],[['Eventos','Arranque 0.2 s; RPM +10% a 8 s; carga x1.2 a 12 s'],['Inercia / límite de par',number(dynamic.get('shaft_inertia_kgm2'))+' kg m2 / '+number(dynamic.get('motor_torque_limit_Nm'),1)+' Nm'],['Final / consigna',number(dynamic.get('final_rpm'),3)+' / '+number(dynamic.get('final_reference_rpm'),3)+' RPM'],['Balance de energía',scaled(dynamic.get('relative_energy_balance_error'),digits=5)+' %'],['Reapertura y segunda simulación',number(dynamic.get('saved_model_reopen_simulation_max_difference'))+' diferencia máxima'],['Arranque extrapolado',number(sx.get('maximum_rpm'),1)+' RPM; '+scaled(sx.get('fraction_of_simulation_samples'),digits=3)+' % de muestras']], [175,WIDTH-175])
    text('Prestación de seguimiento: '+escape(str(dynamic.get('scenario_outcome','Ver registro dinámico')))+'. Par estacionario solicitado '+number(dynamic.get('requested_steady_torque_Nm'),3)+' Nm; capacidad del motor: '+flag(dynamic.get('motor_capacity_feasible'))+'. Un balance numérico aprobado no significa que el motor pueda alcanzar la consigna.','small')
    text('Bajo la menor RPM aceptada se introduce Q = Qmin (omega/omega_min)^2 para demostrar el control. Es extrapolación de escenario: ignora windmilling y posible par negativo con Va positiva. No acredita una predicción naval de arranque. No se modela inflow dinámico, transmisión, motor eléctrico ni cargas estructurales transitorias.','small')

    # 8. Mesh + elastic scope.
    page('07 | Malla y cálculo elástico')
    meshes=struct.get('meshes',[]);elastic=struct.get('structure',{});benchmark=struct.get('calculix_benchmark',{})
    text('Gmsh discretiza el CAD exportado en metros. Se comprueban orientación, volumen, degeneración y razón media tetraédrica. Cambiar tamaño de malla y comparar su volumen es una comprobación geométrica; no demuestra convergencia CFD ni convergencia de tensión FEM.')
    table(['Malla','Nodos','Tetras','Error volumen','Calidad mín. / p05','Degenerados'],[[str(i+1),m.get('nodes','-'),m.get('tetrahedra','-'),scaled(m.get('relative_volume_error'))+' %',number(m.get('quality',{}).get('minimum'),4)+' / '+number(m.get('quality',{}).get('p05'),4),m.get('degenerate_elements','-')] for i,m in enumerate(meshes)], [35,64,67,105,150,WIDTH-421])
    heading('CalculiX: evidencia y transferencia de cargas')
    text('Caso analítico pequeño: '+escape(str(benchmark.get('status','NO EJECUTADO')))+'. Se compara desplazamiento, tensión y reacción contra soluciones prescritas. La versión y hashes del input/salida están en el registro. Este benchmark prueba la ejecución del solver, no las propiedades reales de la hélice.')
    text('El modelo elástico de hélice, si calculado, usa tetraedros lineales C3D4 y núcleo rígido con traslaciones fijadas. Se transfieren empuje y par por anillo a nodos superficiales conservando resultantes, y cargas centrífugas de masas tetraédricas. Son cargas coherentes con el BEM aproximado, sin presión superficial validada.')
    table(['Resultado elástico','Valor / alcance'],[['Estado',elastic.get('status','NO CALCULADO')],['Candidato',struct.get('candidate_id','BASE')],['Desplazamiento máximo',number(elastic.get('maximum_displacement_m'),8)+' m'],['Von Mises máximo en integración',number((elastic.get('maximum_integration_point_von_mises_Pa') or 0)/1e6,4)+' MPa' if elastic.get('maximum_integration_point_von_mises_Pa') is not None else 'NO CALCULADO'],['Balance relativo fuerza / momento',number(elastic.get('force_balance_relative_norm'))+' / '+number(elastic.get('moment_balance_relative_norm'))],['Fatiga / corrosión / factor de seguridad','NO CALCULADO / NO CALCULADO / NO CALCULADO']], [230,WIDTH-230])
    text('La rigidez en flexión y los picos locales de tensión requieren estudio de convergencia y condiciones de apoyo/carga realistas. Una tensión preliminar no se compara con un admisible inventado ni autoriza fabricación. Las alternativas sin FEM no tienen restricciones estructurales verificadas.','small')

    # 9. Materials.
    page('08 | Materiales y servicio')
    text('Las propiedades siguientes proceden de referencias públicas y corresponden a condiciones/productos indicados por sus fuentes. Se conservan valores originales, conversiones y enlaces. No equivalen a un certificado de fabricación o aceptación de clase.')
    matrows=[]
    material_classes={
        'PUBLIC_TYPICAL_NOT_CERTIFIED':'Referencia típica',
        'PUBLIC_MANUFACTURER_REFERENCE_NOT_CERTIFIED':'Referencia de fabricante',
    }
    for m in materials.get('materials',[]):
        mass=cb['volume_m3']*m['density_kgm3'] if cb.get('volume_m3') is not None and m.get('density_kgm3') is not None else None
        elastic_modulus=number(m['elastic_modulus_Pa']/1e9,3) if m.get('elastic_modulus_Pa') is not None else '-'
        poisson_ratio=number(m['poisson_ratio'],3) if m.get('poisson_ratio') is not None else '-'
        property_class=m.get('property_class','-')
        matrows.append([m['id'],number(m.get('density_kgm3'),2),elastic_modulus,poisson_ratio,number(mass,3),material_classes.get(property_class,str(property_class).replace('_',' '))])
    table(['Material','rho kg/m3','E GPa','nu','Masa BASE kg','Referencia'],matrows,[87,78,70,50,82,WIDTH-367])
    text('Un guion indica una propiedad no disponible; no representa cero. Las referencias típicas o de fabricante no certifican el material ni completan datos de servicio ausentes.','small')
    for i,m in enumerate(materials.get('materials',[]),1):
        heading(m.get('label',m['id']));text(escape(m.get('service_basis','Datos de servicio pendientes.')))
        text('Conversión: '+escape(m.get('conversion','-')),'small')
        for url in m.get('source_urls',[]):text(link(url,f'M{i}: fuente primaria - '+url.split('/')[2]),'small')
    heading('Análisis pendientes antes de diseño final')
    text('Datos certificados de resistencia y ductilidad por lote, fabricación/tratamiento, curva de fatiga en agua de mar, corrosión y erosión por cavitación. Definir presión de succión, cavitación, vibración, shaft attachment y condiciones de apoyo. Los compuestos permanecen NO CALCULADO: faltan rigidez ortótropa, orientaciones y criterios de resistencia adecuados.')
    text('La comparación de masa por densidad es calculable para todos los materiales con densidad disponible. El cálculo elástico solo es admisible para materiales que aporten E y nu; las propiedades ausentes no se rellenan automáticamente.','small')

    # 10. Independent evidence and provenance.
    page('09 | Verificación y procedencia')
    table(['Motor / integración','Estado','Alcance real'],[['FreeCAD',cad.get('status','NO EJECUTADO'),'Sólidos, exportación y reapertura'],['MATLAB',hydro.get('status','NO EJECUTADO'),'BEM, curvas, residuos y refinamiento'],['Simulink',dynamic.get('status','NO EJECUTADO'),'SLX real y simulación tras reapertura'],['Gmsh',struct.get('status','NO EJECUTADO'),'Volumen y calidad de malla'],['CalculiX',benchmark.get('status','NO EJECUTADO'),'Caso analítico y elasticidad preliminar'],['Octave',octave.get('status','NO EJECUTADO'),'Relaciones fundamentales independientes'],['Scilab',scilab.get('status','NO EJECUTADO'),'Balance/definiciones independientes'],['Excel COM','Ver registros del lanzador','Lectura de entradas y resultados XLSX']], [104,116,WIDTH-220])
    heading('Comprobaciones independientes')
    text('Octave: '+escape(slim_check(octave))+'.<br/>Scilab: '+escape(slim_check(scilab))+'.')
    text('Se recalculan magnitudes adimensionales, potencia/par, conversiones y balances fundamentales con formulaciones independientes. Son comprobaciones de coherencia y unidades, no una segunda validación física del BEM. El registro conserva diferencias, tolerancias y número de filas comprobadas.')
    checks=combined.get('checks',[])
    if checks:table(['Etapa','Estado','Criterio / evidencia'],[[str(v) for v in row[:3]] for row in checks], [110,90,WIDTH-200])
    heading('Versiones y límites de conexión')
    text('FreeCAD '+escape('.'.join(str(x) for x in cad.get('version',[])[:3]))+'; MATLAB '+escape(hydro.get('version','-'))+'; Octave '+escape(octave.get('version','-'))+'; Scilab '+escape(str(scilab.get('version','-')))+'. CalculiX '+escape(benchmark.get('version','-'))+'.','small')
    text('Las herramientas leen/escriben localmente. Esta instalación MATLAB puede consultar servicios MathWorks para licencias al iniciar; los scripts no suben archivos del proyecto. Inventor, ParaView y DWSIM no son motores acreditados de este flujo.','small')

    # 11. Reproducibility inventory and primary sources.
    page('10 | Archivos, reproducción y fuentes')
    inventory=[p.relative_to(run).as_posix() for p in run.rglob('*') if p.is_file() and 'temp/' not in p.relative_to(run).as_posix() and 'matlab_preferences/' not in p.relative_to(run).as_posix() and 'report_previews/' not in p.relative_to(run).as_posix()]
    table(['Producto','Motor / fuente','Archivo o conjunto'],[['Entradas congeladas','Excel COM + lanzador','case.json; family.json; registros de lectura'],['Geometría editable','FreeCAD','cad/*.FCStd; STEP; cad_results.json'],['Imágenes CAD','Python / teselación CAD','images/*.png; provenance de render'],['Hidrodinámica','MATLAB','hydro_results.json; sections/curves CSV; MAT/PNG'],['Dinámica','Simulink','CantaX_Drive.slx; dynamics.csv; JSON/MAT/PNG'],['Malla / elasticidad','Gmsh / CalculiX','mesh_structure/; structure_results.json'],['Comprobaciones','Octave / Scilab','*_verification.json; logs específicos'],['Resultados / informe','Excel COM / ReportLab','XLSX; combined_results.json; este PDF']], [99,143,WIDTH-242])
    text(f'Inventario detectado antes de generar este informe: {len(inventory)} archivos. El manifest del lanzador y sus hashes son la referencia íntegra. Los resultados pertenecen a {escape(run.name)}; una nueva ejecución genera un directorio diferente.','small')
    text('Reproducción: editar entradas en el XLSX de control, guardar/cerrar Excel y usar el lanzador local documentado. No hacen falta nuevas respuestas de ChatGPT para una corrida ordinaria. Los fallos se detienen/registran y no sustituyen resultados por valores supuestos.','small')
    heading('Referencias de modelos')
    for i,r in enumerate(refs.get('sources',[])[:6],1):
        text(link(r['url'],f'R{i}. '+r['title'])+'<br/>'+escape(r.get('use','')),'small')
    text('Fuentes de material: enlaces M1-M3 de la página de materiales. Se consultaron documentación y referencias públicas el 12-10-2026. No se enviaron datos privados en las búsquedas. Método completo y límites: docs/BEM.md y docs/STRUCTURAL_ANALYSIS.md de esta distribución pública.','small')

    page_counter=[0]
    def footer(canvas,doc):
        page_counter[0]=max(page_counter[0],doc.page)
        canvas.saveState();canvas.setStrokeColor(TEAL);canvas.setLineWidth(.8);canvas.line(42,39,A4[0]-42,39)
        canvas.setFont('Helvetica',7);canvas.setFillColor(GRAY);canvas.drawString(42,26,'CantaX Propeller Lab | Estimaciones preliminares y evidencia local');canvas.drawRightString(A4[0]-42,26,f'{doc.page}');canvas.restoreState()
    doc=SimpleDocTemplate(str(out),pagesize=A4,rightMargin=42,leftMargin=42,topMargin=43,bottomMargin=52,title='CantaX Propeller Lab - Informe técnico',author='CantaX / automatización asistida por IA')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    page_count=page_counter[0]
    if not 8<=page_count<=12:raise RuntimeError(f'Unexpected page count: {page_count}')
    poppler=executable('poppler',required=False)
    proof={'status':'GENERATED_REQUIRES_VISUAL_QA','application':'ReportLab','pdf':str(out),'pages':page_count,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'rendered_pages':0,'sources_read':[str(run/name) for name in ['combined_results.json','case.json','hydro_results.json','cad_results.json','structure_results.json','dynamics_result.json','octave_verification.json','scilab_verification.json']]+[str(material_source),str(reference_source)],'input_inventory':inventory}
    if poppler is None:
        proof['render_note']='Poppler unavailable; render and inspect this generated PDF before external presentation.'
        (run/'report_result.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({k:proof[k] for k in ['status','pdf','pages','rendered_pages']},ensure_ascii=False));return 0
    preview=run/'report_previews';preview.mkdir(exist_ok=False)
    cmd=[str(poppler),'-r','105','-png',str(out),str(preview/'page')]
    result=subprocess.run(cmd,capture_output=True,text=True,timeout=180)
    (preview/'render.log').write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
    if result.returncode:raise RuntimeError('Poppler failed: '+result.stderr)
    pages=sorted(preview.glob('page-*.png'))
    if len(pages)!=page_count:raise RuntimeError('Not every PDF page rendered')
    thumbs=[]
    for file in pages:
        with PILImage.open(file) as im:
            thumb=ImageOps.contain(im.convert('RGB'),(298,422));card=PILImage.new('RGB',(322,459),'#dce5e9');card.paste(thumb,((322-thumb.width)//2,14));ImageDraw.Draw(card).text((12,441),file.stem,fill='#132c40');thumbs.append(card)
    cols=3;rows=math.ceil(len(thumbs)/cols);montage=PILImage.new('RGB',(cols*322,rows*459),'#cad6dc')
    for i,im in enumerate(thumbs):montage.paste(im,((i%cols)*322,(i//cols)*459))
    montage.save(preview/'montage.png')
    proof.update(status='GENERATED_RENDERED_REQUIRES_VISUAL_QA',rendered_pages=len(pages),preview_montage=str(preview/'montage.png'))
    (run/'report_result.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:proof[k] for k in ['status','pdf','pages','rendered_pages','preview_montage']},ensure_ascii=False));return 0

if __name__=='__main__':raise SystemExit(main())
