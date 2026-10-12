"""Render the actual validated FreeCAD tessellation, not synthetic illustrations."""
import argparse
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
FONT=ImageFont.load_default(size=24)
SMALL=ImageFont.load_default(size=18)

def render(vertices,faces,out,label,view='iso',mesh=False):
    v=np.array(vertices,dtype=float); f=np.array(faces,dtype=int)
    if f.min()==1 and f.max()==len(v): f=f-1
    center=(v.max(axis=0)+v.min(axis=0))/2; v=v-center
    if view=='front': direction=np.array([0,0,1.0]); up=np.array([0,1.,0])
    elif view=='side': direction=np.array([0,-1.,0]);up=np.array([0,0,1.])
    else: direction=np.array([1.,-1.3,1.15]);up=np.array([0,0,1.])
    direction=direction/np.linalg.norm(direction);right=np.cross(up,direction);right/=np.linalg.norm(right);vertical=np.cross(direction,right)
    p=np.column_stack([v@right,v@vertical,v@direction]);w,h=1400,1000
    extent=max(np.ptp(p[:,0]),np.ptp(p[:,1]),1e-6);scale=min(w-150,h-190)/extent
    xy=np.column_stack([w/2+p[:,0]*scale,h/2+30-p[:,1]*scale])
    im=Image.new('RGB',(w,h),'#F1F4F7'); draw=ImageDraw.Draw(im)
    light=np.array([-.4,-.3,1.]);light/=np.linalg.norm(light)
    normals=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]);length=np.linalg.norm(normals,axis=1);normals/=np.maximum(length[:,None],1e-30)
    shades=.42+.58*np.abs(normals@light)
    order=np.argsort(p[f,2].mean(axis=1))
    base=np.array([185,143,77]) if not mesh else np.array([90,145,185])
    for i in order:
        color=tuple(int(x) for x in np.minimum(255,base*shades[i]+20))
        poly=[tuple(x) for x in xy[f[i]]]
        draw.polygon(poly,fill=color,outline=('#526B7D' if mesh else None))
    draw.text((45,28),label,font=FONT,fill='#16304B');draw.text((45,h-54),'Geometría CAD real / tessellation SI | '+view,font=SMALL,fill='#54677A')
    length_m=extent/4;pixels=length_m*scale;x0=w-330;y0=h-70
    draw.line([(x0,y0),(x0+pixels,y0)],fill='#16304B',width=3)
    draw.text((x0,y0+9),f'{length_m*1000:.1f} mm',font=SMALL,fill='#16304B')
    im.save(out)

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);args=p.parse_args();run=Path(args.run_dir).resolve()
    if not run.is_relative_to(ROOT):raise ValueError('Run outside lab')
    images=run/'images';images.mkdir(exist_ok=True)
    data=json.loads((run/'cad_results.json').read_text(encoding='utf-8-sig'))
    for m in data['models']:
        if m.get('status')!='verified':continue
        surf=json.loads((run/'cad'/(m['id']+'_surface.json')).read_text())
        verts=surf.get('vertices_m',surf.get('vertices'));faces=surf.get('faces',surf.get('triangles'))
        for view in (['iso','front','side'] if m['id']=='BASE' else ['iso']):
            render(verts,faces,images/(m['id']+'_'+view+'.png'),m['id']+' | FreeCAD '+str(m['geometry']['blades'])+' palas',view)
    mesh=run/'mesh_structure/fine/surface.json'
    if mesh.exists():
        s=json.loads(mesh.read_text());verts=s.get('vertices_m',s.get('vertices'));faces=s.get('faces',s.get('triangles'))
        if verts is not None and faces is not None:render(verts,faces,images/'BASE_mesh.png','BASE | frontera de la malla Gmsh','iso',True)
    (images/'render_provenance.json').write_text(json.dumps({'generator':'Python NumPy/Pillow deterministic projection of actual FreeCAD/Gmsh surface data','inputs':'CAD surface JSON in SI; views are geometry renders, not screenshots of a GUI','files':[p.name for p in images.glob('*.png')]},indent=2),encoding='utf-8')
    print(json.dumps({'images':str(images),'count':len(list(images.glob('*.png')))}))

if __name__=='__main__':main()
