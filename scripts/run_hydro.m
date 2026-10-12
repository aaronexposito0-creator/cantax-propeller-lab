% New run directory supplied by launcher. Every result is local.
outdir=getenv('CANTAX_RUN_DIR'); assert(~isempty(outdir));
scriptdir=fileparts(mfilename('fullpath')); addpath(scriptdir);
caseData=jsondecode(fileread(fullfile(outdir,'case.json')));
family=jsondecode(fileread(fullfile(outdir,'family.json')));
if isstruct(family) && isscalar(family) && isfield(family,'configurations'), family=family.configurations; end
assert(numel(family)>=3);
report=struct('application','MATLAB','version',version,'release',version('-release'),'status','running',...
 'method','ANNULAR_POSITIVE_THRUST_BEM_ANALYTICAL_LIFT_FRICTION_ONLY_DRAG','classification','PRELIMINARY_ESTIMATES_WITH_NUMERICAL_VERIFICATION_NO_EXPERIMENTAL_VALIDATION');
results=struct([]); sectionTable=[];
for k=1:numel(family)
 [rr,ss]=hydro_model(caseData,family(k).geometry,family(k).id,60);
 if k==1, results=rr; else, results(k)=orderfields(rr,results(1)); end
 if strcmp(family(k).id,'BASE') || k==1, baseline=rr; sectionTable=ss; end
end
report.baseline=baseline; report.alternatives=results;
headers={'r_R','r_m','dr_m','chord_m','beta_deg','phi_deg','alpha_deg','Cl','Cd','Re','Prandtl_F','u_axial_mps','v_tangential_disk_mps','dT_N_all_blades','dQ_Nm_all_blades','normalized_residual','axial_induction_a','tangential_induction_ap','relative_speed_mps'};
sectionCSV=[sectionTable sectionTable(:,2)-sectionTable(:,3)/2 sectionTable(:,2)+sectionTable(:,3)/2 sectionTable(:,14) sectionTable(:,15)];
headers=[headers {'r_inner_m','r_outer_m','dT_N','dQ_Nm'}];
writetable(array2table(sectionCSV,'VariableNames',headers),fullfile(outdir,'hydro_sections.csv'));
[fine,~]=hydro_model(caseData,caseData.geometry,'BASE_REFINED',120);
report.discretization_check=struct('coarse_annuli',60,'fine_annuli',120,'relative_T_difference',abs(fine.T_N-baseline.T_N)/max(abs(fine.T_N),eps),...
 'relative_Q_difference',abs(fine.Q_Nm-baseline.Q_Nm)/max(abs(fine.Q_Nm),eps),'passed',false,'criterion','T and Q change < 1 percent; numerical verification only');
report.discretization_check.passed=report.discretization_check.relative_T_difference<.01 && report.discretization_check.relative_Q_difference<.01;
curves=struct([]); curveRows=[];
for k=1:31
 cc=caseData; cc.operation.advance_mps=(.20+(k-1)*.027)*caseData.operation.rpm/60*caseData.geometry.diameter_m;
 [rr,~]=hydro_model(cc,caseData.geometry,sprintf('OW_%02d',k),60);
 if k==1, curves=rr; else, curves(k)=orderfields(rr,curves(1)); end
 curveRows(k,:)=[rr.rpm rr.Va_mps rr.J rr.T_N rr.Q_Nm rr.P_W rr.KT rr.KQ rr.eta0 double(rr.valid_domain) rr.max_normalized_residual rr.alpha_max_deg];
end
report.curves=curves;
writetable(array2table(curveRows,'VariableNames',{'rpm','Va_mps','J','T_N','Q_Nm','P_W','KT','KQ','eta0','valid_domain','max_residual','max_alpha_deg'}),fullfile(outdir,'hydro_curves.csv'));
sens=struct([]); kk=0;
fields={'diameter_m','rpm','pitch_ratio','advance_mps'};
for j=1:4
 for factor=[.95 1.05]
  cc=caseData; gg=cc.geometry;
  if j==1||j==3, gg.(fields{j})=gg.(fields{j})*factor;
  else, cc.operation.(fields{j})=cc.operation.(fields{j})*factor; end
  kk=kk+1; [rr,~]=hydro_model(cc,gg,sprintf('SENS_%s_%.2f',fields{j},factor),60);
  if kk==1,sens=rr;else,sens(kk)=orderfields(rr,sens(1));end
 end
end
report.sensitivity=sens;
perturb=struct([]); multipliers=[.8 1;1.2 1;1 .5;1 2];
for j=1:4
 [rr,~]=hydro_model(caseData,caseData.geometry,sprintf('CLOSURE_%d',j),60,multipliers(j,1),multipliers(j,2));
 if j==1,perturb=rr;else,perturb(j)=orderfields(rr,perturb(1));end
end
report.closure_sensitivity=struct('lift_drag_multipliers',multipliers,'results',perturb,'interpretation','Scenario spread, not a statistical confidence interval or calibrated uncertainty');
assert(baseline.valid_domain,'Baseline outside declared approximation guards');
assert(report.discretization_check.passed,'Radial refinement failed');
report.status='passed';
fid=fopen(fullfile(outdir,'hydro_results.json'),'w');fprintf(fid,'%s\n',jsonencode(report));fclose(fid);
save(fullfile(outdir,'hydro_results.mat'),'report','caseData','family','sectionTable');
fig=figure('Visible','off','Color','w');
tiledlayout(2,1);nexttile;plot(curveRows(:,3),curveRows(:,7),'o-',curveRows(:,3),10*curveRows(:,8),'s-');grid on;legend('K_T','10 K_Q');ylabel('Preliminary coefficients');
nexttile;plot(curveRows(:,3),curveRows(:,9),'o-');grid on;xlabel('J');ylabel('Estimated eta_0');title('Analytical BEM approximation; invalid points omitted; no experiment data');
% Explicit report styling: installed dark themes must not hide labels on white.
set(findall(fig,'Type','axes'),'Color','w','XColor','k','YColor','k','ZColor','k','FontName','Arial','FontSize',10,'GridColor',[.65 .65 .65]);
set(findall(fig,'Type','text'),'Color','k','FontName','Arial','FontSize',10);
set(findall(fig,'Type','legend'),'Color','w','TextColor','k','FontName','Arial','FontSize',10,'EdgeColor',[.55 .55 .55]);
exportgraphics(fig,fullfile(outdir,'hydro_curves.png'),'Resolution',160);close(fig);
disp(jsonencode(report.baseline));
simulink_model(caseData,outdir);
