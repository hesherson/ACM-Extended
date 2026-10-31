// register vesicant bruising and local pain only when the medication is delivered through a peripheral iv site.
// B14 exact-site callers include proximal IVs; a proximal peripheral IV is not a central line. IO leakage is not modeled.
// this function never applies limb damage, bleeding, ACE trauma or necrosis.
params ["_patient", "_bodyPart", "_classname", ["_dose", 0], ["_threshold", 0], ["_painScale", 1], ["_tier", "vesicant"], ["_antidote", "hyaluronidase"], ["_bruiseFromStage", 0], ["_accessSite", -2]];
// the system toggle, read live, so unticking extravasation in addon options stops this system immediately and
// completely with no mission restart.
if !(missionNamespace getVariable ["ACME_sys_vesicant", true]) exitWith {};
if (isNull _patient || {!local _patient}) exitWith {};
if (!(missionNamespace getVariable ["ACME_vesicant_enabled", true])) exitWith {};
if (_dose <= 0 || {_threshold <= 0}) exitWith {};
// Do not turn a head PO/IN/BUC medication into an IV injury even through a direct caller.
if !([_classname] call ACME_fnc_vesicantRouteAllows) exitWith {};

private _bp = toLowerANSI _bodyPart;
private _hasPeripheral = false;

if (_accessSite < 0 && {!isNil "ACM_circulation_fnc_hasIV"}) then {
    if (_bp == "head") then {
        // ej access is treated as peripheral for vesicant bruising and pain.
        {
            if ([_patient, _bp, 0, _x] call ACM_circulation_fnc_hasIV) exitWith { _hasPeripheral = true; };
        } forEach [0, 1];
    } else {
        if (_bp in ["leftarm", "rightarm", "leftleg", "rightleg"]) then {
            // ACM iv position 0 is the upper site. only middle and lower peripheral sites count.
            {
                if ([_patient, _bp, 0, _x] call ACM_circulation_fnc_hasIV) exitWith { _hasPeripheral = true; };
            } forEach [1, 2];
        };
    };
};

// B14 owner settlement has already proven the exact IV and leaked amount.
if (_accessSite in [0,1,2]) then {_hasPeripheral = true;};
if (!_hasPeripheral) exitWith {};

private _now = CBA_missionTime;
private _key = if (_accessSite >= 0) then {
    format ["ACME_vesExposure_%1_%2_site%3",_bp,_classname,_accessSite]
} else {format ["ACME_vesExposure_%1_%2",_bp,_classname]};
private _cur = _patient getVariable [_key, [0, -1, -1, -1, 0]];
private _total = _cur param [0, 0];
private _startT = _cur param [1, -1];
private _lastStage = _cur param [2, -1];
private _lastDoseT = _cur param [3, -1];
private _painApplied = _cur param [4, 0];

if (_startT < 0 || {_lastDoseT >= 0 && {(_now - _lastDoseT) > (missionNamespace getVariable ["ACME_vesicant_stopResetSec", 30])}}) then {
    _startT = _now;
};
_total = _total + _dose;
_lastDoseT = _now;

private _ratio = _total / _threshold;
private _elapsed = _now - _startT;
private _stage = -1;
if (_ratio >= 1) then { _stage = 0; };
if (_ratio >= 1.35 || {_ratio >= 1 && {_elapsed >= (missionNamespace getVariable ["ACME_vesicant_moderateExposureSec", 120])}}) then { _stage = 1; };
if (_ratio >= 1.7) then { _stage = 2; };
if (_ratio >= (missionNamespace getVariable ["ACME_vesicant_extensiveDoseMult", 2.0]) || {_ratio >= 1 && {_elapsed >= (missionNamespace getVariable ["ACME_vesicant_extensiveExposureSec", 300])}}) then { _stage = 3; };

if (_stage > _lastStage) then {
    // the irritants, amiodarone, magnesium and esmolol, are pain-forward: they only produce a visible bruise from
    // _bruiseFromStage up, so a moderate irritant exposure hurts without marking and extensive bruising needs a very
    // high dose. true vesicants bruise from stage 0.
    if (_stage >= _bruiseFromStage) then {
        private _wounds = _patient getVariable ["ace_medical_openWounds", createHashMap];
        private _woundsOnPart = _wounds getOrDefault [_bp, []];
        private _bruiseID = [20, 21, 22, 22] select (_stage min 3);
        private _found = false;
        {
            _x params ["_id", "_amount", "_bleed", "_damage"];
            if (_id == _bruiseID && {_bleed <= 0}) exitWith {
                _x set [1, _amount + 1];
                _found = true;
            };
        } forEach _woundsOnPart;
        if (!_found) then {
            _woundsOnPart pushBack [_bruiseID, 1, 0, 0];
        };
        _wounds set [_bp, _woundsOnPart];
        [_patient, [["openWounds", _wounds, true]]] call ACM_core_fnc_setAceMedicalState;
    };

    if (!isNil "ace_medical_treatment_fnc_addToTriageCard") then {
        private _label = ["Bruising", "Moderate bruising", "Extensive bruising", "Extensive bruising"] select (_stage min 3);
        if (_stage < _bruiseFromStage) then { _label = "Local irritation / pain"; };
        [_patient, format ["%1 from %2 (%3 peripheral IV)", _label, _classname, _bp]] call ace_medical_treatment_fnc_addToTriageCard;
    };
};

// the state is [total, startt, stage, the high-water mark, lastdoset, painapplied, painscale, threshold, tier,
// antidote, bruisefromstage].
_patient setVariable [_key, [_total, _startT, _stage max _lastStage, _lastDoseT, _painApplied, _painScale, _threshold, _tier, _antidote, _bruiseFromStage], true];

private _records = _patient getVariable ["ACME_vesicant_records", []];
private _rec = [_key, _bp, _classname];
_records pushBackUnique _rec;
[_patient, "records", _records] call ACME_fnc_vesicantRegistryCommit;

if (isNil "ACME_vesicant_patients") then { ACME_vesicant_patients = []; };
ACME_vesicant_patients pushBackUnique _patient;
