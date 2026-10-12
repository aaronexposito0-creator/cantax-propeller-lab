param(
    [Parameter(Mandatory=$true)][string]$WorkbookPath,
    [Parameter(Mandatory=$true)][string]$RunDir,
    [ValidateSet('Read','Verify')][string]$Mode='Read',
    [Nullable[double]]$SetDiameter=$null,
    [Nullable[double]]$SetRPM=$null,
    [Nullable[int]]$SetBlades=$null,
    [Nullable[double]]$SetPitchRatio=$null
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$labRoot=[IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$runPath=[IO.Path]::GetFullPath($RunDir)
$runsRoot=Join-Path $labRoot 'runs'
if(-not $runPath.StartsWith($runsRoot+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'RunDir must be a new execution directory inside this lab/runs.'}
[void](New-Item -ItemType Directory -Path $runPath -Force)
$resultFile=Join-Path $runPath $(if($Mode -eq 'Read'){'excel_read_result.json'}else{'excel_result_verification.json'})
if(Test-Path -LiteralPath $resultFile){throw 'Refusing to overwrite an existing Excel test record.'}
if($Mode -eq 'Read' -and (Test-Path -LiteralPath (Join-Path $runPath 'case.json'))){throw 'Refusing to overwrite existing case.json; select a fresh run.'}
$requestedEdits=@(
    @{argument='SetDiameter';key='diameter_m';value=$SetDiameter},
    @{argument='SetRPM';key='rpm';value=$SetRPM},
    @{argument='SetBlades';key='blades';value=$SetBlades},
    @{argument='SetPitchRatio';key='pitch_ratio';value=$SetPitchRatio}
)
$requestedEdits=@($requestedEdits | Where-Object {$null -ne $_.value})
$hasEdits=$requestedEdits.Count -gt 0
if($Mode -ne 'Read' -and $hasEdits){throw 'Parameter edits are only permitted in Mode Read.'}
$report=[ordered]@{application='Microsoft Excel';api='COM Excel.Application';mode=$Mode;status='failed';started_utc=[DateTime]::UtcNow.ToString('o');owned_instance=$false;tests=@();formula_errors=@();units='SI'}
$app=$null; $book=$null; $control=$null; $radial=$null; $owned=$false
$case=$null

function Release-Com([object]$value){
    if($null -ne $value -and [Runtime.InteropServices.Marshal]::IsComObject($value)){
        # COM can return the same RCW for an already-owned worksheet. A final
        # release would invalidate the caller's Control/Radial references.
        [void][Runtime.InteropServices.Marshal]::ReleaseComObject($value)
    }
}
function Write-Json([string]$path,[object]$payload){
    $payload | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $path -Encoding utf8
}
function Read-Cell([object]$sheet,[string]$address,[string]$property='Value2'){
    $cell=$null
    try{$cell=$sheet.Range($address); return $cell.$property}
    finally{Release-Com $cell}
}
function Require-Number([object]$value,[string]$context){
    if($null -eq $value -or $value -is [string] -or $value -is [bool]){throw "Missing or nonnumeric typed Excel value at $context"}
    $num=[double]$value
    if([double]::IsNaN($num) -or [double]::IsInfinity($num)){throw "Nonfinite number at $context"}
    return $num
}
function Get-SharedReadHash([string]$path){
    $stream=$null;$sha=$null
    try{
        # Permit an existing native Excel writer without requesting any write
        # access ourselves. This hashes the saved on-disk file, not its unsaved UI.
        $stream=[IO.FileStream]::new($path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite)
        $sha=[Security.Cryptography.SHA256]::Create()
        return [Convert]::ToHexString($sha.ComputeHash($stream)).ToLowerInvariant()
    }finally{if($null -ne $sha){$sha.Dispose()};if($null -ne $stream){$stream.Dispose()}}
}
function Validate-Xlsx([string]$path){
    if([IO.Path]::GetExtension($path) -ine '.xlsx'){throw 'Only macro-free .xlsx files are supported.'}
    $zip=$null;$stream=$null
    try{
        $stream=[IO.FileStream]::new($path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite)
        $zip=[IO.Compression.ZipArchive]::new($stream,[IO.Compression.ZipArchiveMode]::Read,$false)
        foreach($entry in $zip.Entries){
            if($entry.FullName -match '^xl/(externalLinks/|queryTables/|macrosheets/|connections\.xml|vbaProject\.bin)'){
                throw 'Workbook has external data connections, query tables or VBA; rejected before native Excel opening.'
            }
            if($entry.FullName -match '^xl/worksheets/[^/]+\.xml$'){
                $reader=$null
                try{
                    $reader=[IO.StreamReader]::new($entry.Open())
                    [xml]$xml=$reader.ReadToEnd()
                    foreach($node in $xml.SelectNodes('//*[local-name()="f"]')){
                        if($node.InnerText -match '(?i)(WEBSERVICE|RTD|STOCKHISTORY|IMAGE|CUBEVALUE|CUBESET|CUBEMEMBER|HYPERLINK|DDE)\s*\(' -or $node.InnerText -match '[\[\]|]'){
                            throw 'Workbook contains a formula that may fetch remote/linked data; rejected before native recalculation.'
                        }
                    }
                }finally{if($null -ne $reader){$reader.Dispose()}}
            }
        }
    } finally{if($null -ne $zip){$zip.Dispose()};if($null -ne $stream){$stream.Dispose()}}
}
function Read-Input([object]$ctrl,[object]$rad,[object]$mapping,[hashtable]$configuration){
    $inputs=@()
    foreach($parameter in $mapping.parameters){
        $address=[string]$parameter.cell
        $row=[int]($address -replace '[^0-9]','')
        $unit=[string](Read-Cell $ctrl "C$row")
        if($unit -cne [string]$parameter.unit){throw "Unit mismatch at Control!C${row}: expected '$($parameter.unit)', read '$unit'. No silent conversion is allowed."}
        $raw=Read-Cell $ctrl $address
        if($parameter.key -eq 'material'){
            if($null -eq $raw -or [string]::IsNullOrWhiteSpace([string]$raw)){throw 'Missing material ID at Control!B24.'}
            $value=[string]$raw
        }else{
            $value=Require-Number $raw "Control!$address"
            if($value -lt [double]$parameter.min -or $value -gt [double]$parameter.max){throw "Value outside admissible range at Control!${address}: $value; allowed [$($parameter.min),$($parameter.max)]."}
            if($parameter.key -eq 'blades'){
                if($value -ne [Math]::Round($value)){throw 'Blade count must be an integer.'}
                $value=[int]$value
            }
        }
        if([string]::IsNullOrWhiteSpace([string]$parameter.group)){$configuration[$parameter.key]=$value}
        else{$configuration[$parameter.group][$parameter.key]=$value}
        $state=[string](Read-Cell $ctrl "F$row")
        if($parameter.key -eq 'material'){
            if($state -notin @('REVISAR MATERIAL','CHECK MATERIAL')){throw "Unexpected material validation status '$state'."}
        }elseif($state -ne 'OK'){throw "Native Excel validation failed at F${row}: '$state'."}
        $inputs+=@{sheet='Control';cell=$address;key=$parameter.key;value=$value;unit=$unit;native_validation=$state}
    }
    $fields=@('r_R','chord_weight','pitch_factor','thickness_factor','skew_factor','rake_factor')
    $radialRows=@()
    for($r=6;$r -le 13;$r++){
        $station=@{}
        for($c=0;$c -lt 6;$c++){
            $address=([string][char](65+$c))+$r
            $value=Require-Number (Read-Cell $rad $address) "Radial!$address"
            if($value -lt 0){throw "Negative radial factor at Radial!$address"}
            if($c -ge 1 -and $c -le 3 -and $value -le 0){throw "Chord, pitch and thickness factors must be positive at Radial!$address"}
            $station[$fields[$c]]=$value
        }
        if($station.r_R -le 0 -or $station.r_R -gt 1){throw "Radial coordinate r/R must be in (0,1] at row $r"}
        if($radialRows.Count -gt 0 -and $station.r_R -le $radialRows[-1].r_R){throw 'Radial coordinates must increase strictly.'}
        $radialRows+=$station
    }
    if([Math]::Abs($radialRows[-1].r_R-1) -gt 1e-12){throw 'Last radial station must equal r/R=1.'}
    if($radialRows[0].r_R -ge $configuration.geometry.hub_ratio){throw 'First radial station must intersect the hub (r/R < hub/D).'}
    $configuration.radial_distribution=$radialRows
    return @{inputs=$inputs;radial=$radialRows}
}
function Check-FormulaErrors([object]$workbook){
    $errors=@(); $sheets=@(); $chartCount=0; $validationCount=0
    for($i=1;$i -le $workbook.Worksheets.Count;$i++){
        $sh=$null; $used=$null; $bad=$null; $validated=$null
        try{
            $sh=$workbook.Worksheets.Item($i)
            $sheets+=[string]$sh.Name
            $charts=$null
            try{$charts=$sh.ChartObjects();$chartCount+=[int]$charts.Count}finally{Release-Com $charts}
            $used=$sh.UsedRange
            foreach($cellType in @(-4123,2)){
                try{$bad=$used.SpecialCells($cellType,16)}catch{$bad=$null}
                if($null -ne $bad){
                    foreach($cell in $bad.Cells){
                        try{$errors+=@{sheet=[string]$sh.Name;cell=[string]$cell.Address($false,$false);value=[string]$cell.Text;formula=[string]$cell.Formula}}finally{Release-Com $cell}
                    }
                    Release-Com $bad; $bad=$null
                }
            }
            try{$validated=$sh.Cells.SpecialCells(-4174);$validationCount+=[int]$validated.CountLarge}catch{$validated=$null}
        }finally{Release-Com $bad;Release-Com $validated;Release-Com $used;Release-Com $sh}
    }
    return @{formula_errors=$errors;sheet_names=$sheets;chart_count=$chartCount;validated_cell_count=$validationCount}
}

try{
    $mapping=Get-Content -Raw -LiteralPath (Join-Path $labRoot 'config\excel_mapping.json') | ConvertFrom-Json
    $plannedEdits=@()
    foreach($requested in $requestedEdits){
        $parameter=@($mapping.parameters | Where-Object {$_.key -ceq $requested.key})
        if($parameter.Count -ne 1){throw "Parameter '$($requested.key)' must have exactly one entry in config/excel_mapping.json."}
        $value=Require-Number $requested.value $requested.argument
        if($value -lt [double]$parameter[0].min -or $value -gt [double]$parameter[0].max){throw "$($requested.argument) outside mapped range [$($parameter[0].min),$($parameter[0].max)]."}
        if($requested.key -eq 'blades' -and $value -ne [Math]::Round($value)){throw 'SetBlades must be an integer.'}
        $plannedEdits+=@{key=$requested.key;cell=[string]$parameter[0].cell;unit=[string]$parameter[0].unit;requested_value=$value}
    }
    $sourcePath=(Resolve-Path -LiteralPath $WorkbookPath).Path
    Validate-Xlsx $sourcePath
    $report.source_workbook_path=$sourcePath
    $report.source_workbook_sha256=Get-SharedReadHash $sourcePath
    if($Mode -eq 'Read'){
        $inputPath=Join-Path $runPath 'input.xlsx'
        if(-not $sourcePath.Equals($inputPath,[StringComparison]::OrdinalIgnoreCase)){
            if(Test-Path -LiteralPath $inputPath){throw 'Refusing to overwrite existing run/input.xlsx.'}
            Copy-Item -LiteralPath $sourcePath -Destination $inputPath
        }
        $openPath=$inputPath
    }else{
        $openPath=$sourcePath
        if(-not $openPath.StartsWith($runPath+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'Verify only accepts a workbook already inside this run.'}
    }
    Validate-Xlsx $openPath
    $existing=@(Get-Process -Name EXCEL -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id)
    $report.preexisting_excel_pids=$existing
    $comType=[type]::GetTypeFromProgID('Excel.Application')
    if($null -eq $comType){throw 'Excel.Application is not registered.'}
    $app=[Activator]::CreateInstance($comType)
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class CantaXExcelWindow {
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);
}
'@
    [uint32]$ownedPid=0
    [void][CantaXExcelWindow]::GetWindowThreadProcessId([IntPtr]$app.Hwnd,[ref]$ownedPid)
    if($ownedPid -eq 0 -or $existing -contains $ownedPid){throw 'Could not establish a new, private Excel PID; refused to change application settings or workbooks.'}
    $owned=$true; $report.owned_instance=$true; $report.owned_excel_pid=$ownedPid
    $app.Visible=$false; $app.DisplayAlerts=$false; $app.EnableEvents=$false; $app.AutomationSecurity=3; $app.AskToUpdateLinks=$false
    $report.version=[string]$app.Version; $report.build=[string]$app.Build
    $report.execution_security=@{new_private_process=$true;automation_security=3;macro_policy='ForceDisable for owned instance only';update_links=0;events_enabled=$false;global_office_changes=$false;network_data_connections=$false}
    $readOnly=-not $hasEdits
    $book=$app.Workbooks.Open($openPath,0,$readOnly)
    if([int]$book.Connections.Count -ne 0){throw 'Workbook connections found despite OOXML preflight; refusing further processing.'}
    $report.opened_workbook=$openPath; $report.opened_read_only=[bool]$book.ReadOnly
    $control=$book.Worksheets.Item('Control'); $radial=$book.Worksheets.Item('Radial')
    if($hasEdits){
        if(-not $openPath.Equals((Join-Path $runPath 'input.xlsx'),[StringComparison]::OrdinalIgnoreCase)){throw 'Parameter edits may only target this run/input.xlsx.'}
        foreach($change in $plannedEdits){
            $change.previous_value=Require-Number (Read-Cell $control $change.cell) "Control!$($change.cell) before edit"
            $cell=$null
            try{$cell=$control.Range($change.cell);$cell.Value2=[double]$change.requested_value}finally{Release-Com $cell}
        }
        $app.CalculateFull()
        $book.Save()
        Release-Com $control; $control=$null;Release-Com $radial; $radial=$null
        $book.Close($false);Release-Com $book;$book=$null
        $book=$app.Workbooks.Open($openPath,0,$true)
        $report.saved_reopened_read_only=[bool]$book.ReadOnly
        $control=$book.Worksheets.Item('Control');$radial=$book.Worksheets.Item('Radial')
        $changes=@()
        foreach($change in $plannedEdits){
            $readback=Require-Number (Read-Cell $control $change.cell) "Control!$($change.cell) saved readback"
            if([Math]::Abs($readback-$change.requested_value) -gt 1e-12){throw "Saved workbook parameter readback does not match $($change.key)."}
            $change.sheet='Control';$change.saved_readback_value=$readback;$change.passed=$true;$change.only_run_copy_modified=$true
            $changes+=$change
            if($change.key -eq 'diameter_m'){
                # Retain the first-version diameter evidence for older callers.
                $report.parameter_change=@{sheet='Control';cell=$change.cell;previous_m=$change.previous_value;requested_m=$change.requested_value;saved_readback_m=$readback;passed=$true;only_run_copy_modified=$true}
            }
        }
        $report.parameter_changes=$changes
        $report.tests+=@{name='Native Excel parameter changes, save, close and readonly reopen';passed=$true;changed_cell_count=$changes.Count}
    }
    $app.CalculateFull()
    $panel=$null
    try{
        $panel=$book.Worksheets.Item('Panel')
        $report.panel_freshness=[string](Read-Cell $panel 'B16')
        $report.panel_freshness_formula=[string](Read-Cell $panel 'B16' 'Formula')
    }finally{Release-Com $panel}
    $case=Get-Content -Raw -LiteralPath (Join-Path $labRoot 'config\default_case.json') | ConvertFrom-Json -AsHashtable
    $read=Read-Input $control $radial $mapping $case
    $materials=Get-Content -Raw -LiteralPath (Join-Path $labRoot 'config\materials.json') | ConvertFrom-Json -AsHashtable
    $selected=@($materials.materials | Where-Object {$_.id -ceq $case.material})
    if($selected.Count -ne 1){throw "Material ID '$($case.material)' is absent or duplicated in sourced config/materials.json."}
    $density=Require-Number $selected[0].density_kgm3 'selected material density'
    if($density -le 0){throw 'Selected material density must be positive.'}
    $case.material_density_kgm3=$density
    $case.selected_material_properties=$selected[0]
    $scan=Check-FormulaErrors $book
    $report.formula_errors=$scan.formula_errors; $report.sheet_names=$scan.sheet_names; $report.chart_count=$scan.chart_count; $report.validated_cell_count=$scan.validated_cell_count
    if($report.formula_errors.Count -gt 0){throw 'Unexpected native Excel formula/constant error cells found.'}
    $integral=0.0
    for($i=0;$i -lt $case.radial_distribution.Count-1;$i++){
        $a=$case.radial_distribution[$i];$b=$case.radial_distribution[$i+1]
        $integral+=($b.r_R-$a.r_R)*($a.chord_weight+$b.chord_weight)/2*$case.geometry.diameter_m/2
    }
    $nativeIntegral=Require-Number (Read-Cell $radial 'J6') 'Radial!J6 integral'
    $expected=$case.radial_distribution[0].chord_weight*$case.geometry.expanded_area_ratio*[Math]::PI*[Math]::Pow($case.geometry.diameter_m,2)/(4*$case.geometry.blades*$integral)
    $native=Require-Number (Read-Cell $radial 'G6') 'Radial!G6 chord'
    $formula=[string](Read-Cell $radial 'G6' 'Formula')
    $absoluteTolerance=1e-10
    if(-not $formula.StartsWith('=') -or [Math]::Abs($expected-$native) -gt $absoluteTolerance -or [Math]::Abs($nativeIntegral-$integral) -gt $absoluteTolerance){throw 'Native radial normalization formula disagrees with independent input integration.'}
    $report.normalization_check=@{sheet='Radial';cell='G6';formula=$formula;native_chord_m=$native;independent_chord_m=$expected;absolute_difference_m=[Math]::Abs($native-$expected);native_integral_m=$nativeIntegral;independent_integral_m=$integral;absolute_tolerance=1e-10;passed=$true}
    $report.tests+=@{name='Typed Excel inputs, SI units, bounds and radial distribution';passed=$true;input_count=$read.inputs.Count;radial_count=$read.radial.Count}
    $report.tests+=@{name='CalculateFull and independent chord normalization comparison';passed=$true}
    $report.tests+=@{name='Native Excel workbook error scan';passed=$true;error_cells=0}
    $report.input_cells=$read.inputs; $report.radial_values=$read.radial
    $report.input_workbook_sha256=Get-SharedReadHash $openPath
    if($Mode -eq 'Read'){
        $case.excel_provenance=@{application='Microsoft Excel';version=$report.version;build=$report.build;read_utc=[DateTime]::UtcNow.ToString('o');source_workbook_path=$report.source_workbook_path;source_workbook_sha256=$report.source_workbook_sha256;run_input_workbook_path=$openPath;run_input_workbook_sha256=$report.input_workbook_sha256;actual_native_COM_read=$true;native_formula_check=$report.normalization_check}
        Write-Json (Join-Path $runPath 'case.json') $case
        $report.case_json=Join-Path $runPath 'case.json'
    }
    $report.status='verified'
}catch{
    $report.error=$_.Exception.Message
    $report.error_details=$_.ToString()
    $report.error_stacktrace=$_.ScriptStackTrace
}finally{
    if($null -ne $book -and $owned){try{$book.Close($false)}catch{$report.cleanup_error=$_.Exception.Message}}
    Release-Com $control;Release-Com $radial;Release-Com $book
    if($null -ne $app -and $owned){try{$app.Quit()}catch{$report.cleanup_error=$_.Exception.Message}}
    Release-Com $app
    [GC]::Collect();[GC]::WaitForPendingFinalizers();[GC]::Collect();[GC]::WaitForPendingFinalizers()
    $report.finished_utc=[DateTime]::UtcNow.ToString('o')
    Write-Json $resultFile $report
    $report | ConvertTo-Json -Depth 30
}
if($report.status -ne 'verified'){exit 1}
