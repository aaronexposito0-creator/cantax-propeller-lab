// Definition checks independent of the MATLAB blade-element implementation.
// Scilab uses angular velocity throughout, unlike Octave's revolutions/s.
outdir=getenv("CANTAX_RUN_DIR");
if outdir=="" then disp("CANTAX_RUN_DIR is required"); exit(1); end
outfile=outdir+"/scilab_verification.json";
if isfile(outfile) then disp("Refusing to overwrite verification result"); exit(1); end
result=struct("application","Scilab","version",getversion(),"status","FAIL", ..
 "scope","Independent angular-velocity SI/definition/energy checks; no BEM physical validation", ..
 "relative_tolerance",1d-8,"absolute_tolerance",1d-10);
try
    source=outdir+"/verification_input.csv";
    header=mgetl(source,1);
    if stripblanks(header)<>"rpm,Va_mps,D_m,rho,T_N,Q_Nm,KT,KQ,P_W,eta0,J" then
        error("Unexpected CSV schema");
    end
    a=csvRead(source,",",".","double",[],[],[],1);
    if size(a,2)<>11 | size(a,1)<1 | or(isnan(a)) | or(isinf(a)) then
        error("Missing/nonfinite verification input");
    end
    if or(a(:,1)<=0) | or(a(:,3)<=0) | or(a(:,4)<=0) | or(a(:,6)<=0) then
        error("rpm/D/rho/Q must be positive");
    end
    omega=a(:,1)*%pi/30;
    advance_ratio=2*%pi*a(:,2)./(omega.*a(:,3));
    kt=4*%pi^2*a(:,5)./(a(:,4).*omega.^2.*a(:,3).^4);
    kq=4*%pi^2*a(:,6)./(a(:,4).*omega.^2.*a(:,3).^5);
    power=omega.*a(:,6);
    efficiency=a(:,5).*a(:,2)./(omega.*a(:,6));
    torque_from_power=a(:,9)./omega;
    reference=[a(:,11),a(:,7),a(:,8),a(:,9),a(:,10),a(:,6)];
    recalculated=[advance_ratio,kt,kq,power,efficiency,torque_from_power];
    difference=abs(recalculated-reference);
    permitted=result.absolute_tolerance+result.relative_tolerance*abs(reference);
    scaled=difference./permitted;
    relative=difference./max(abs(reference),result.absolute_tolerance*ones(reference));
    result.rows_checked=size(a,1);
    result.numeric_checks=size(a,1)*6+2;
    result.maximum_absolute_difference=max(difference);
    result.worst_relative_difference=max(relative);
    result.worst_tolerance_fraction=max(scaled);
    maxima=max(scaled,"r");
    result.tolerance_fraction=struct("J",maxima(1),"KT",maxima(2),"KQ",maxima(3), ..
      "P_W",maxima(4),"eta0",maxima(5),"Q_from_P",maxima(6));
    result.unit_volume_1mm3_m3=10^(-9);
    result.unit_volume_expected_m3=1d-9;
    result.rpm_roundtrip_max_abs_error=max(abs(omega*30/%pi-a(:,1)));
    if abs(result.unit_volume_1mm3_m3-1d-9)>1d-20 then error("Volume units failed"); end
    if result.rpm_roundtrip_max_abs_error>1d-10 then error("RPM units failed"); end
    if result.worst_tolerance_fraction>1 then error("Definition comparison exceeds tolerance"); end
    csvWrite(recalculated,outdir+"/scilab_definition_values.csv",",",".","%.17g");
    result.status="PASS";
catch
    result.error=lasterror();
end
mputl(toJSON(result),outfile);
disp(toJSON(result));
if result.status<>"PASS" then exit(1); end
exit(0);
