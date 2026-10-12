function result=simulink_model(caseData,outdir)
% Generates a self-contained SLX with model-workspace lookup and parameters.
mdl='CantaX_Drive'; assert(~bdIsLoaded(mdl),'Name already loaded; refuse collision');
oldGeneration=Simulink.fileGenControl('getConfig');
restoreGeneration=onCleanup(@()Simulink.fileGenControl('setConfig','config',oldGeneration)); %#ok<NASGU>
Simulink.fileGenControl('set','CacheFolder',fullfile(outdir,'simulink_cache'),'CodeGenFolder',fullfile(outdir,'simulink_codegen'),'createDir',true);
rpm0=caseData.operation.rpm; records=struct([]);
for j=1:25
 cc=caseData;cc.operation.rpm=rpm0*(.5+(j-1)*.045);
 [rr,~]=hydro_model(cc,cc.geometry,sprintf('LOOKUP_%02d',j),40);
 if j==1,records=rr;else,records(j)=orderfields(rr,records(1));end
end
valid=[records.valid_domain];
assert(any(valid),'No acceptable torque lookup samples');
% Keep the contiguous accepted branch containing the closest baseline RPM.
[~,ix]=min(abs([records.rpm]-rpm0));assert(valid(ix));
ilo=ix;ihi=ix;while ilo>1&&valid(ilo-1),ilo=ilo-1;end
while ihi<numel(valid)&&valid(ihi+1),ihi=ihi+1;end
accepted=records(ilo:ihi);
omegaKnown=[accepted.rpm]*2*pi/60; qKnown=[accepted.Q_Nm];
% The positive-thrust BEM has no windmill/startup model. Only this explicit
% surrogate below the first valid sample is used to exercise shaft control.
low=linspace(0,omegaKnown(1),21);lowQ=qKnown(1)*(low/omegaKnown(1)).^2;
lookupOmega=[low(1:end-1) omegaKnown];lookupQ=[lowQ(1:end-1) qKnown];
assert(all(diff(lookupOmega)>0));
new_system(mdl); mw=get_param(mdl,'ModelWorkspace');mw.DataSource='Model File';
mw.assignin('load_omega_radps',lookupOmega);mw.assignin('load_torque_Nm',lookupQ);
mw.assignin('shaft_I',caseData.dynamic.shaft_inertia_kgm2);
mw.assignin('control_kp',caseData.dynamic.kp_Nm_per_radps);
mw.assignin('control_ki',caseData.dynamic.ki_Nm_per_rad);
mw.assignin('torque_limit',caseData.dynamic.motor_torque_limit_Nm);
mw.assignin('omega_target',rpm0*2*pi/60);
block=@(library,name,varargin)add_block(library,[mdl '/' name],varargin{:});
block('simulink/Sources/Step','StartReference','Time','.2','Before','0','After','omega_target','Position',[25 30 60 60]);
block('simulink/Sources/Step','RPMStep','Time','8','Before','0','After','.1*omega_target','Position',[25 85 60 115]);
block('simulink/Math Operations/Sum','Reference','Inputs','++','Position',[95 40 120 75]);
block('simulink/Math Operations/Sum','Error','Inputs','+-','Position',[160 40 185 75]);
block('simulink/Math Operations/Gain','Proportional','Gain','control_kp','Position',[220 15 265 45]);
block('simulink/Continuous/Integrator','IntegralError','InitialCondition','0','LimitOutput','on','UpperSaturationLimit','torque_limit/control_ki','LowerSaturationLimit','0','Position',[220 75 250 105]);
block('simulink/Math Operations/Gain','IntegralGain','Gain','control_ki','Position',[275 75 310 105]);
block('simulink/Math Operations/Sum','Control','Inputs','++','Position',[340 30 365 65]);
block('simulink/Discontinuities/Saturation','MotorTorque','UpperLimit','torque_limit','LowerLimit','0','Position',[405 30 450 65]);
block('simulink/Math Operations/Sum','NetTorque','Inputs','+-','Position',[500 40 525 75]);
block('simulink/Math Operations/Gain','InverseInertia','Gain','1/shaft_I','Position',[570 40 620 75]);
block('simulink/Continuous/Integrator','ShaftSpeed','InitialCondition','0','Position',[670 40 700 75]);
block('simulink/Lookup Tables/1-D Lookup Table','PropellerTorqueCurve','BreakpointsForDimension1','load_omega_radps','Table','load_torque_Nm','InterpMethod','Linear point-slope','ExtrapMethod','Clip','Position',[675 170 790 205]);
block('simulink/Sources/Step','LoadMultiplier','Time','12','Before','1','After','1.2','Position',[675 235 720 265]);
block('simulink/Math Operations/Product','PropellerTorque','Position',[825 170 855 205]);
block('simulink/Signal Routing/Mux','TraceMux','Inputs','7','Position',[950 30 980 220]);
block('simulink/Sinks/To Workspace','Trace','VariableName','drive_trace','SaveFormat','Timeseries','Position',[1010 85 1120 120]);
wire=@(a,b)add_line(mdl,a,b,'autorouting','on');
wire('StartReference/1','Reference/1');wire('RPMStep/1','Reference/2');wire('Reference/1','Error/1');wire('ShaftSpeed/1','Error/2');
wire('Error/1','Proportional/1');wire('Error/1','IntegralError/1');wire('IntegralError/1','IntegralGain/1');
wire('Proportional/1','Control/1');wire('IntegralGain/1','Control/2');wire('Control/1','MotorTorque/1');
wire('MotorTorque/1','NetTorque/1');wire('PropellerTorque/1','NetTorque/2');wire('NetTorque/1','InverseInertia/1');wire('InverseInertia/1','ShaftSpeed/1');
wire('ShaftSpeed/1','PropellerTorqueCurve/1');wire('PropellerTorqueCurve/1','PropellerTorque/1');wire('LoadMultiplier/1','PropellerTorque/2');
wire('ShaftSpeed/1','TraceMux/1');wire('MotorTorque/1','TraceMux/2');wire('PropellerTorque/1','TraceMux/3');wire('Reference/1','TraceMux/4');wire('LoadMultiplier/1','TraceMux/5');wire('InverseInertia/1','TraceMux/6');wire('Error/1','TraceMux/7');wire('TraceMux/1','Trace/1');
set_param(mdl,'StopTime',num2str(caseData.dynamic.duration_s),'SolverType','Fixed-step','Solver','ode4','FixedStep','.005','ReturnWorkspaceOutputs','on');
set_param(mdl,'Description','Local demonstrator: analytical BEM torque lookup; startup below accepted RPM explicitly extrapolated Q proportional omega squared. Shaft inertia/control gains are scenario inputs. No dynamic inflow, cavitation, motor electrical or structural model.');
modelFile=fullfile(outdir,[mdl '.slx']);save_system(mdl,modelFile);
simout=sim(mdl);trace=simout.get('drive_trace');tt=trace.Time;data=trace.Data;
close_system(mdl,0);load_system(modelFile);reopened=sim(mdl);reopenedTrace=reopened.get('drive_trace');
reopenError=max(abs(reopenedTrace.Data(:)-data(:)));
omega=data(:,1);Qm=data(:,2);Qp=data(:,3);ref=data(:,4);loadMultiplier=data(:,5);accel=data(:,6);
Pm=omega.*Qm;Pp=omega.*Qp;I=caseData.dynamic.shaft_inertia_kgm2;
energyChange=.5*I*(omega(end)^2-omega(1)^2);netWork=trapz(tt,Pm-Pp);
energyError=abs(netWork-energyChange)/max(abs(energyChange),1);
algebraicResidual=max(abs(I*accel-(Qm-Qp)));
finalError=abs(omega(end)-ref(end))/max(ref(end),eps);
requestedTorque=interp1(lookupOmega,lookupQ,ref(end),'linear')*loadMultiplier(end);
capacityFeasible=requestedTorque<=caseData.dynamic.motor_torque_limit_Nm;
trackingPassed=finalError<.02;
scenarioOutcome='REFERENCE_TRACKED';
if ~capacityFeasible,scenarioOutcome='REFERENCE_CAPACITY_LIMITED';elseif ~trackingPassed,scenarioOutcome='REFERENCE_NOT_SETTLED';end
result=struct('application','Simulink','version',version,'status','passed','model_file',modelFile,...
 'classification','SIMULINK_EXECUTED_WITH_PRELIMINARY_STEADY_BEM_LOOKUP_AND_EXPLICIT_STARTUP_SURROGATE',...
 'shaft_inertia_kgm2',I,'inertia_classification','USER_SCENARIO_NOT_CAD_DERIVED','motor_torque_limit_Nm',caseData.dynamic.motor_torque_limit_Nm,...
 'startup_extrapolation',struct('rule','Q=Qmin*(omega/omegaMin)^2 below accepted positive-thrust BEM branch; ignores windmilling/negative torque at fixed Va','maximum_rpm',omegaKnown(1)*60/(2*pi),'fraction_of_simulation_samples',mean(omega<omegaKnown(1)),...
 'validated',false),...
 'lookup_rpm_range',omegaKnown([1 end])*60/(2*pi),'lookup_results',records,'events',struct('start_time_s',.2,'rpm_step_time_s',8,'rpm_step_fraction',.1,'load_step_time_s',12,'load_step_multiplier',1.2),...
 'final_rpm',omega(end)*60/(2*pi),'final_reference_rpm',ref(end)*60/(2*pi),'final_relative_speed_error',finalError,...
 'requested_steady_torque_Nm',requestedTorque,'motor_capacity_feasible',capacityFeasible,'tracking_checks_passed',trackingPassed,'scenario_outcome',scenarioOutcome,...
 'motor_torque_min_Nm',min(Qm),'motor_torque_max_Nm',max(Qm),'maximum_rpm',max(omega)*60/(2*pi),'max_algebraic_torque_balance_residual_Nm',algebraicResidual,...
 'energy_change_J',energyChange,'net_mechanical_work_J',netWork,'relative_energy_balance_error',energyError,'saved_model_reopen_simulation_max_difference',reopenError,...
 'numerical_checks_passed',algebraicResidual<1e-9 && energyError<.02 && max(omega)<=omegaKnown(end) && max(ref)<=omegaKnown(end) && min(omega)>=-1e-8 && reopenError<1e-10,...
 'limitations',{{'NO_DYNAMIC_INFLOW','NO_MOTOR_ELECTRICAL_OR_GEARBOX_MODEL','LIMITED_INTEGRAL_SIMPLE_PI_CONTROL_NOT_TUNED','STARTUP_IS_EXTRAPOLATED_SCENARIO','INERTIA_AND_EXTRA_LOAD_ARE_SCENARIO_INPUTS'}});
if ~result.numerical_checks_passed,result.status='failed';end
writetable(array2table([tt omega omega*60/(2*pi) Qm Qp Pm Pp ref*60/(2*pi) loadMultiplier accel],...
 'VariableNames',{'time_s','omega_radps','rpm','motor_torque_Nm','propeller_torque_Nm','motor_power_W','propeller_power_W','reference_rpm','load_multiplier','acceleration_radps2'}),fullfile(outdir,'dynamics.csv'));
writetable(array2table([lookupOmega(:)*60/(2*pi) lookupQ(:) double(lookupOmega(:)>=omegaKnown(1))],...
 'VariableNames',{'rpm','torque_Nm','in_accepted_BEM_branch'}),fullfile(outdir,'dynamic_torque_lookup.csv'));
fid=fopen(fullfile(outdir,'dynamics_result.json'),'w');fprintf(fid,'%s\n',jsonencode(result));fclose(fid);
save(fullfile(outdir,'dynamics.mat'),'simout','result');
f=figure('Visible','off','Color','w');tiledlayout(3,1);nexttile;plot(tt,omega*60/(2*pi),tt,ref*60/(2*pi),'--');grid on;legend('RPM','reference');
nexttile;plot(tt,Qm,tt,Qp);grid on;ylabel('Torque Nm');legend('motor','propeller');nexttile;plot(tt,Pm,tt,Pp);grid on;ylabel('Power W');xlabel('Time s');
% Explicit report styling only; the saved model and numerical data are unchanged.
set(findall(f,'Type','axes'),'Color','w','XColor','k','YColor','k','ZColor','k','FontName','Arial','FontSize',10,'GridColor',[.65 .65 .65]);
set(findall(f,'Type','text'),'Color','k','FontName','Arial','FontSize',10);
set(findall(f,'Type','legend'),'Color','w','TextColor','k','FontName','Arial','FontSize',10,'EdgeColor',[.55 .55 .55]);
exportgraphics(f,fullfile(outdir,'dynamics.png'),'Resolution',160);close(f);close_system(mdl,0);
assert(result.numerical_checks_passed,'Dynamic numerical checks failed');disp(jsonencode(result));
end
