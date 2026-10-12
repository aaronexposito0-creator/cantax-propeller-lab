function [result, sections] = hydro_model(caseData, geometry, id, count, liftScale, dragScale)
% Preliminary positive-thrust BEM. SI throughout; no measured foil polars.
if nargin<4, count=60; end
if nargin<5, liftScale=1; end
if nargin<6, dragScale=1; end
D=geometry.diameter_m; R=D/2; B=geometry.blades;
V=caseData.operation.advance_mps; rpm=caseData.operation.rpm;
rho=caseData.operation.water_density_kgm3; nu=caseData.operation.water_kinematic_viscosity_m2s;
n=rpm/60; omega=2*pi*n;
rd=caseData.radial_distribution; stations=[rd.r_R]; weights=[rd.chord_weight];
normArea=trapz(stations*R,weights);
chordScale=geometry.expanded_area_ratio*pi*D^2/(4*B*normArea);
lo=max([geometry.hub_ratio+0.02,0.22,stations(1)]); hi=0.99;
edges=linspace(lo,hi,count+1); rr=(edges(1:end-1)+edges(2:end))/2;
r=rr*R; dr=diff(edges)*R;
c=interp1(stations,weights,rr,'linear')*chordScale;
pf=interp1(stations,[rd.pitch_factor],rr,'linear');
beta=atan(geometry.pitch_ratio*D*pf./(2*pi*r));
sections=zeros(count,19);
opts=optimset('Display','off','TolX',1e-10,'TolFun',1e-14,'MaxIter',400,'MaxFunEvals',1200);
seed=[.08 .02];
for j=1:count
    args={r(j),c(j),beta(j),R,geometry.hub_ratio*R,B,V,omega,rho,nu,liftScale,dragScale};
    [x,~,~]=fminsearch(@(x) objective(x,args),seed,opts);
    [res,ann]=annulus(x,args);
    if max(abs(res))>1e-6
        [xx,~,~]=fminsearch(@(x) objective(x,args),[.15 .05],opts);
        [res2,ann2]=annulus(xx,args);
        if norm(res2)<norm(res), x=xx; res=res2; ann=ann2; end
    end
    seed=x;
    sections(j,:)=[rr(j),r(j),dr(j),c(j),rad2deg(beta(j)),ann.phi_deg,ann.alpha_deg,ann.Cl,ann.Cd,ann.Re,ann.F,ann.u,ann.v,ann.T*dr(j),ann.Q*dr(j),max(abs(res)),ann.a,ann.ap,ann.W];
end
rawT=sum(sections(:,14)); rawQ=sum(sections(:,15)); rawP=omega*rawQ;
rawEta=rawT*V/rawP;
flags={};
converged=all(sections(:,16)<1e-5) && all(isfinite(sections),'all');
if ~converged, flags{end+1}='ANNULUS_RESIDUAL_OR_NONFINITE'; end
if n<=0 || V<=0, flags{end+1}='POSITIVE_RPM_AND_ADVANCE_REQUIRED'; end
if any(sections(:,7)<0) || any(sections(:,7)>10), flags{end+1}='ALPHA_OUTSIDE_0_TO_10_DEG'; end
if any(sections(:,17)<0) || any(sections(:,17)>2), flags{end+1}='AXIAL_INDUCTION_OUTSIDE_0_TO_2'; end
if any(sections(:,18)<0) || any(sections(:,18)>.5), flags{end+1}='TANGENTIAL_INDUCTION_OUTSIDE_0_TO_0_5'; end
if any(sections(:,10)<2e4), flags{end+1}='RE_BELOW_NUMERICAL_FRICTION_GUARD_20000'; end
if rawT<=0 || rawQ<=0 || rawEta<0 || rawEta>=1, flags{end+1}='NONPROPULSIVE_OR_ENERGY_CHECK_FAILED'; end
if geometry.thickness_ratio*max([rd.thickness_factor])>.12, flags{end+1}='THICKNESS_ABOVE_THIN_FOIL_SCENARIO_GUARD'; end
valid=isempty(flags);
result=struct('id',id,'B',B,'D_m',D,'pitch_ratio',geometry.pitch_ratio,'EAR',geometry.expanded_area_ratio,'rpm',rpm,'Va_mps',V,'rho_kgm3',rho,'J',V/(n*D),...
 'T_N',rawT,'Q_Nm',rawQ,'P_W',rawP,'KT',rawT/(rho*n^2*D^4),'KQ',rawQ/(rho*n^2*D^5),'eta0',rawEta,...
 'valid_domain',valid,'converged',converged,'domain_flags',{flags},'classification','PRELIMINARY_MODEL_ESTIMATE_NOT_PHYSICALLY_VALIDATED',...
 'raw_estimates_excluded',struct('T_N',rawT,'Q_Nm',rawQ,'P_W',rawP,'eta0',rawEta),...
 'alpha_min_deg',min(sections(:,7)),'alpha_max_deg',max(sections(:,7)),'Re_min',min(sections(:,10)),'Re_max',max(sections(:,10)),...
 'max_normalized_residual',max(sections(:,16)),'annuli',count,'active_radial_interval_r_R',[lo hi],...
 'geometric_chord_EAR',geometry.expanded_area_ratio,'hydro_active_area_ratio',sum(c.*dr)*B/(pi*D^2/4),...
 'warnings',{{'ANALYTICAL_LIFT_NO_MEASURED_SECTION_POLARS','FRICTION_ONLY_DRAG_OMITS_PRESSURE_SEPARATION_ROUGHNESS','LOW_RE_TRANSITION_NOT_RESOLVED','SKEW_RAKE_THICKNESS_NOT_HYDRO_RESOLVED','NO_CAVITATION_OR_VENTILATION_VALIDATION'}});
if valid, result.raw_estimates_excluded=[]; else
    result.T_N=NaN;result.Q_Nm=NaN;result.P_W=NaN;result.KT=NaN;result.KQ=NaN;result.eta0=NaN;
end
end

function f=objective(x,args)
[res,~]=annulus(x,args);
penalty=100*(min(x(1),0)^2+min(x(2),0)^2+max(x(2)-.95,0)^2);
f=sum(res.^2)+penalty;
if ~isfinite(f), f=1e20; end
end

function [res, a]=annulus(x,args)
[r,c,beta,R,Rhub,B,V,omega,rho,nu,liftScale,dragScale]=deal(args{:});
u=x(1)*(V+omega*r); v=x(2)*omega*r;
vx=V+u; vt=omega*r-v; W=hypot(vx,vt); phi=atan2(vx,vt); alpha=beta-phi;
Re=max(W*c/nu,101); Cf=.075/(log10(Re)-2)^2;
Cl=liftScale*2*pi*alpha; Cd=dragScale*2*Cf;
Ftip=2/pi*acos(exp(-B/2*(R-r)/(r*max(abs(sin(phi)),1e-8))));
Fhub=2/pi*acos(exp(-B/2*(r-Rhub)/(Rhub*max(abs(sin(phi)),1e-8))));
F=max(Ftip*Fhub,1e-8);
T=.5*rho*W^2*B*c*(Cl*cos(phi)-Cd*sin(phi));
Q=.5*rho*W^2*B*c*r*(Cl*sin(phi)+Cd*cos(phi));
Tm=4*pi*rho*r*F*u*(V+u); Qm=4*pi*rho*r^2*F*v*(V+u);
scale=max(.5*rho*(V^2+(omega*r)^2)*B*c,1);
res=[(T-Tm)/scale,(Q-Qm)/(scale*r)];
a=struct('T',T,'Q',Q,'W',W,'phi_deg',rad2deg(phi),'alpha_deg',rad2deg(alpha),'Cl',Cl,'Cd',Cd,'Re',Re,'F',F,'u',u,'v',v,'a',u/V,'ap',v/(omega*r));
end
