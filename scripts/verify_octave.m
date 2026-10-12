% Definition checks, independently from the MATLAB blade-element solver.
% CSV: rpm,Va_mps,D_m,rho,T_N,Q_Nm,KT,KQ,P_W,eta0,J
outdir = getenv('CANTAX_RUN_DIR');
if isempty(outdir), error('CANTAX_RUN_DIR is required'); endif
outfile = fullfile(outdir,'octave_verification.json');
if exist(outfile,'file') == 2, error('Refusing to overwrite verification result'); endif
result = struct('application','GNU Octave','version',version(),'status','FAIL', ...
  'scope','Independent SI/definition/energy consistency checks; no BEM physical validation', ...
  'relative_tolerance',1e-8,'absolute_tolerance',1e-10);
try
  source = fullfile(outdir,'verification_input.csv');
  fid=fopen(source,'r'); if fid<0, error('Missing verification_input.csv'); endif
  header=strtrim(fgetl(fid)); fclose(fid);
  assert(strcmp(header,'rpm,Va_mps,D_m,rho,T_N,Q_Nm,KT,KQ,P_W,eta0,J'));
  a=dlmread(source,',',1,0);
  assert(columns(a)==11 && rows(a)>=1 && all(isfinite(a(:))));
  assert(all(a(:,1)>0) && all(a(:,3)>0) && all(a(:,4)>0) && all(a(:,6)>0));
  % Octave uses shaft revolutions per second throughout its definitions.
  n=a(:,1)/60; va=a(:,2); diameter=a(:,3); rho=a(:,4);
  thrust=a(:,5); torque=a(:,6);
  advance_ratio=va./(n.*diameter);
  kt=thrust./(rho.*n.^2.*diameter.^4);
  kq=torque./(rho.*n.^2.*diameter.^5);
  power=2*pi*n.*torque;
  efficiency=thrust.*va./power;
  torque_from_power=a(:,9)./(2*pi*n);
  reference=[a(:,11),a(:,7),a(:,8),a(:,9),a(:,10),a(:,6)];
  recalculated=[advance_ratio,kt,kq,power,efficiency,torque_from_power];
  difference=abs(recalculated-reference);
  permitted=result.absolute_tolerance+result.relative_tolerance*abs(reference);
  scaled=difference./permitted;
  relative=difference./max(abs(reference),result.absolute_tolerance);
  result.rows_checked=rows(a); result.numeric_checks=rows(a)*6+2;
  result.maximum_absolute_difference=max(difference(:));
  result.worst_relative_difference=max(relative(:));
  result.worst_relative_difference_decimal=sprintf('%.17g',result.worst_relative_difference);
  result.worst_tolerance_fraction=max(scaled(:));
  maxima=max(scaled,[],1);
  result.tolerance_fraction=struct('J',maxima(1),'KT',maxima(2),'KQ',maxima(3), ...
    'P_W',maxima(4),'eta0',maxima(5),'Q_from_P',maxima(6));
  % SI / millimetre geometry conversion and rpm/rad/s round trip.
  result.unit_volume_1mm3_m3=(1/1000)^3;
  result.unit_volume_expected_m3=1e-9;
  result.rpm_roundtrip_max_abs_error=max(abs((2*pi*n)/(2*pi)*60-a(:,1)));
  assert(abs(result.unit_volume_1mm3_m3-1e-9)<1e-20);
  assert(result.rpm_roundtrip_max_abs_error<=1e-10);
  assert(result.worst_tolerance_fraction<=1);
  dlmwrite(fullfile(outdir,'octave_definition_values.csv'),recalculated,'precision',17);
  result.status='PASS';
catch err
  result.error=err.message;
end_try_catch
encoded=jsonencode(result);
% Octave 11.3 jsonencode rounds some values below epsilon to zero. Preserve
% the actual measured worst error with a formatted JSON numeric literal.
if isfield(result,'worst_relative_difference_decimal')
  encoded=regexprep(encoded,'"worst_relative_difference":[^,}]+', ...
    ['"worst_relative_difference":' result.worst_relative_difference_decimal]);
endif
fid=fopen(outfile,'w'); fprintf(fid,'%s\n',encoded); fclose(fid);
disp(encoded);
if isfield(result,'worst_relative_difference')
  fprintf('Worst relative difference (17 digits): %.17g\n', result.worst_relative_difference);
endif
if !strcmp(result.status,'PASS'), exit(1); endif
exit(0);
