/* Read-only pleural context. No patient state, UI, or progression writes.
   [openHoles,totalHoles,ventCapacity,bleedSource0to1,ppvFactor,hasDrain,hasSealOutlet,hasDefinitiveDrain]
   Capacities are gameplay coefficients for ptxStep, not physical flow units. */
params [["_patient", objNull, [objNull]]];
if (isNull _patient) exitWith {[0, 0, 0, 0, 1, false, false, false]};

private _holes = _patient getVariable ["ACME_CS_holeData", []];
if !(_holes isEqualType []) then {_holes = [];};
private _tracked = _patient getVariable ["ACME_CS_penetratingWounds", []];
if !(_tracked isEqualType []) then {_tracked = [];};
private _processed = _patient getVariable ["ACME_CS_processedPenetratingCount", -1];
if !(_processed isEqualType 0 && {finite _processed}) then {_processed = -1;};
if (_processed < 0) then {_processed = if (count _holes > 0) then {count _tracked} else {0};};
if (count _holes == 0) then {_processed = 0;};
_processed = (floor _processed) max 0 min count _tracked;

// Native treatment covers the records that existed when that treatment completed.
// A subsequent injury cannot borrow an earlier seal's aggregate boolean.
private _nativeCount = _patient getVariable ["ACME_ptx_nativeSealCount", -1];
if !(_nativeCount isEqualType 0 && {finite _nativeCount}) then {_nativeCount = -1;};
_nativeCount = (floor _nativeCount) max -1 min count _tracked;
private _nativeHoleCount = _patient getVariable ["ACME_ptx_nativeSealHoleCount", -1];
if !(_nativeHoleCount isEqualType 0 && {finite _nativeHoleCount}) then {_nativeHoleCount = -1;};
_nativeHoleCount = (floor _nativeHoleCount) max -1 min count _holes;

private _total = 0;
private _covered = 0;
{
    if (_x isEqualType [] && {count _x >= 5} && {(_x select 0) in ["front", "back"]}) then {
        _total = _total + 1;
        // Unfound exits still communicate. Discovery only controls what is drawn.
        if ((_x param [4, false, [false]]) || {_forEachIndex < _nativeHoleCount}) then {_covered = _covered + 1;};
    };
} forEach _holes;
private _pending = ((count _tracked) - _processed) max 0;
private _pendingCovered = ((_nativeCount - _processed) max 0) min _pending;
_total = _total + _pending;
_covered = _covered + _pendingCovered;
private _open = (_total - _covered) max 0;

private _occ = _patient getVariable ["ACME_CS_sealOcclusion", 0];
if !(_occ isEqualType 0 && {finite _occ}) then {_occ = 0;};
_occ = _occ max 0 min 1;
private _hasSealOutlet = _covered > 0;
private _ventCapacity = 0.1 * _open;
if (_hasSealOutlet) then {
    // One missed communication prevents the full-seal benefit. Capacities never
    // multiply with the number of icons, including a single entry/exit pair.
    _ventCapacity = _ventCapacity + ((if (_open == 0) then {1.5} else {0.15}) * (1 - _occ));
};

private _state = _patient getVariable ["ACME_ptx_state", []];
if !(_state isEqualType []) then {_state = [];};
private _ncdPatency = _state param [5, 0, [0]];
if !(finite _ncdPatency) then {_ncdPatency = 0;};
_ncdPatency = _ncdPatency max 0 min 1;
private _hasDrain = _ncdPatency > 0;
_ventCapacity = _ventCapacity max (1.4 * _ncdPatency);

// Explicit tract/tube state outranks ACM's single aggregate, which can remain
// latched after a tube is removed or an open tract is sealed. Partial dissection
// (split/kelly) has not yet established a patent pleural outlet.
private _hasSideState = false;
private _hasDefinitiveDrain = false;
{
    private _side = _x;
    private _tract = _patient getVariable [format ["ACME_thora_open_%1", _side], ""];
    private _tube = _patient getVariable [format ["ACME_thora_tube_%1", _side], false];
    private _sealed = _patient getVariable [format ["ACME_thora_sealed_%1", _side], false];
    private _closed = _patient getVariable [format ["ACME_thora_closed_%1", _side], false];
    private _incision = _patient getVariable [format ["ACME_thora_incision_%1", _side], []];
    if !(_tract isEqualType "") then {_tract = "";};
    if !(_tube isEqualType false) then {_tube = false;};
    if !(_sealed isEqualType false) then {_sealed = false;};
    if !(_closed isEqualType false) then {_closed = false;};
    if !(_incision isEqualType []) then {_incision = [];};
    // Backward compatibility for B120-B132 casualties: a sealed tract is closed even if the new explicit
    // closed flag has not been written yet.
    _closed = _closed || {_sealed && {_tract == "sealed"} && {!_tube}};
    _hasSideState = _hasSideState || {_tract != ""} || {_tube} || {_sealed} || {_closed} || {count _incision == 3};
    _hasDefinitiveDrain = _hasDefinitiveDrain || {_tube} || {_tract == "finger" && {!_sealed} && {!_closed}};
} forEach ["left", "right"];
if (!_hasSideState) then {
    private _nativeThora = _patient getVariable ["ACM_breathing_Thoracostomy_State", 0];
    if (_nativeThora isEqualType 0 && {finite _nativeThora}) then {_hasDefinitiveDrain = _nativeThora in [1, 2];};
};
// A chest seal over a completed finger thoracostomy is an occlusive CLOSED tract. It removes the
// surgical drain/vent and does not add one-way vent capacity. The retained internal leak/air state therefore
// determines whether PTX can reaccumulate after the tract is closed.
if (_hasDefinitiveDrain) then {
    _hasDrain = true;
    _ventCapacity = _ventCapacity max 5.0;
};

// ACE open wounds carry [classID,amount,bleeding,...]. Use ongoing external
// bleeding from eligible penetrating chest wounds, not retained pleural blood,
// the whole-body bleed sum, or elapsed time. Clotted/bandaged wounds are absent.
private _injuryMap = missionNamespace getVariable ["ACM_breathing_ChestInjury_Chances", createHashMap];
if !(_injuryMap isEqualType createHashMap) then {_injuryMap = createHashMap;};
private _openWounds = _patient getVariable ["ace_medical_openWounds", createHashMap];
if !(_openWounds isEqualType createHashMap) then {_openWounds = createHashMap;};
private _bodyWounds = _openWounds getOrDefault ["body", []];
if !(_bodyWounds isEqualType []) then {_bodyWounds = [];};
private _bleedSource = 0;
{
    if (_x isEqualType [] && {count _x >= 3}) then {
        private _id = _x param [0, -1, [0]];
        private _amount = _x param [1, 0, [0]];
        private _bleeding = _x param [2, 0, [0]];
        if (finite _id && {finite _amount} && {finite _bleeding} && {_id in _injuryMap}) then {
            _bleedSource = _bleedSource + ((_amount max 0) * (_bleeding max 0));
        };
    };
} forEach _bodyWounds;
_bleedSource = (_bleedSource * 5) max 0 min 1;

// A configured or paused device is not positive-pressure delivery. Actual PIP
// drives the bounded multiplier; effective settings supply only its fallback.
private _ppvFactor = 1;
private _ventDriving = (_patient getVariable ["ACME_vent_connected", false])
    && {_patient getVariable ["ACME_vent_driving", false]};
if (_ventDriving) then {
    private _effective = [_patient] call ACME_fnc_ventEffectiveSettings;
    private _pip = _patient getVariable ["ACME_vent_pip", _effective param [6, 20]];
    if !(_pip isEqualType 0 && {finite _pip}) then {_pip = 20;};
    _ppvFactor = linearConversion [10, 50, _pip, 1, 3, true];
};
private _provider = _patient getVariable ["ACM_breathing_BVM_provider", objNull];
if !(_provider isEqualType objNull) then {_provider = objNull;};
private _lastBreath = _patient getVariable ["ACME_bvm_lastBreathServer", -100];
if !(_lastBreath isEqualType 0 && {finite _lastBreath}) then {_lastBreath = -100;};
private _breathAge = (serverTime - _lastBreath) max 0;
if (alive _provider && {_breathAge >= 0} && {_breathAge <= 12}) then {_ppvFactor = _ppvFactor max 1.5;};

[_open, _total, _ventCapacity, _bleedSource, _ppvFactor max 1 min 3, _hasDrain, _hasSealOutlet, _hasDefinitiveDrain]
