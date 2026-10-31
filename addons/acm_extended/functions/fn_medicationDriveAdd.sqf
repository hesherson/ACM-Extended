/* B121 exact mass enters a short delivery queue. Infusions always use their physical flow duration. Manual bolus
   rate is clinically consequential only with Hardcore Medications; normal mode stretches custom toxicity-drive
   inputs to a safe reference window while native dose/kinetics remain unchanged. */
params ["_patient","_class","_amount","_seconds"];
if (isNull _patient || {!local _patient} || {!alive _patient} || {_amount <= 0} || {!finite _amount}) exitWith {};
private _base = (_class splitString "_") select 0;
private _tracked = _base in ["Epinephrine","Norepinephrine","Amiodarone","CalciumChloride","CalciumGluconate","Magnesium","Lidocaine","Esmolol"]
    || {_base in (missionNamespace getVariable ["ACME_infusion_pk",createHashMap])};
if (!_tracked) exitWith {};
private _infusion = missionNamespace getVariable ["ACME_driveIsInfusion",false];
if (_base == "Epinephrine" && {!_infusion}) exitWith {};
_seconds = _seconds max 0.25;
if (!_infusion && {!(missionNamespace getVariable ["ACME_hcEff_medications",false])}) then {
    private _safe = switch (_base) do {
        case "Amiodarone": {600}; case "CalciumChloride": {300}; case "CalciumGluconate": {180};
        case "Magnesium": {300}; case "Lidocaine": {120}; case "Esmolol": {60}; case "Norepinephrine": {60};
        default {_seconds};
    };
    _seconds = _seconds max _safe;
};
private _queue = _patient getVariable ["ACME_medicationDriveQueue",[]];
_queue pushBack [_base,_amount,_seconds,if (_infusion) then {"infusion"} else {"bolus"}];
// Infusion entries are admitted-flow samples, not new interventions: every bag can add one each medical tick.
// Preserve exact owner mass immediately while sharing the one-second snapshot budget with the consumer.
// Manual bolus additions remain immediate so a newly administered dose survives locality migration.
_patient setVariable ["ACME_medicationDriveQueue", _queue, false];
private _driveNow = diag_tickTime;
private _driveLast = _patient getVariable ["ACME_medicationDriveNetAt", -1];
if (!_infusion || {_driveLast < 0} || {(_driveNow - _driveLast) >= 1}) then {
    [_patient, "ACME_medicationDriveQueue", _queue] call ACME_fnc_setVarNet;
    _patient setVariable ["ACME_medicationDriveNetAt", _driveNow, false];
    _patient setVariable ["ACME_medicationDriveFlushToken", [], false];
};
