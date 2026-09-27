/* B13: validate the complete draw before taking anything; conserve open vial mL.
   Components are source mL, not mg. No clinical mixing compatibility is implied. */
params ["_medic", "_components", ["_container", ""], ["_consumeContainer", false], ["_reserve", false], ["_patient", objNull]];
private _failure = if (_reserve) then {[]} else {false};
if (isNull _medic || {!local _medic} || {!alive _medic} || {!(_components isEqualType [])} || {_components isEqualTo []}) exitWith {_failure};
if (isNull _patient) then {_patient = uiNamespace getVariable ["ACME_SK_Patient",_medic];};
if (isNull _patient) then {_patient = _medic;};
// The same explicit Self/Patient/Vehicle source owns the displayed vial limits
// and the debit. Never substitute the medic's vial after drawing from a patient.
private _holder = [_medic] call ACME_fnc_vialHolder;
if (isNull _holder) exitWith {_failure};
private _display = findDisplay 84000;
private _boundHolder = if (isNull _display) then {uiNamespace getVariable ["ACME_SK_VialHolder",objNull]} else {_display getVariable ["ACME_SK_VialHolder",objNull]};
if (!isNull _boundHolder && {!(_holder isEqualTo _boundHolder)}) exitWith {_failure};
// Prevent a scheduled caller yielding between complete validation and debit.
private _result = _failure;
isNil {
private _need = createHashMap;
private _valid = true;
private _taken = [];
{
    if (!(_x isEqualType []) || {count _x != 2}) then {_valid = false;} else {
        _x params ["_source", "_ml"];
        if (!(_source isEqualType "") || {!(_ml isEqualType 0)} || {!finite _ml} || {_ml <= 0}) then {_valid = false;} else {
            private _cfg = configFile >> "ACM_Medication" >> "Concentration" >> _source;
            if (getNumber (_cfg >> "concentration") <= 0 || {getNumber (_cfg >> "volume") <= 0}) then {_valid = false;} else {
                _need set [_source, (_need getOrDefault [_source, 0]) + _ml];
            };
        };
    };
} forEach _components;
if (!_valid || {_container != "" && {([_medic, _patient, _container] call ACME_fnc_treatmentSupplyCount) < 1}}) exitWith {false};
{if (([_holder, _x] call ACME_fnc_infusionVialVolume) + 0.000001 < (_need get _x)) then {_valid = false;};} forEach (keys _need);
if (!_valid) exitWith {false};
{
    if !([_holder, _x, _need get _x, _medic] call ACME_fnc_vialTake) exitWith {_valid = false;};
    _taken pushBack [_x, _need get _x];
} forEach (keys _need);
if (!_valid) exitWith {
    // Unexpected late debit failure restores exact solution, including repeated draws.
    {[_holder, _x select 0, _x select 1, _medic] call ACME_fnc_vialRefund;} forEach _taken;
    false
};
private _items = [];
if (_consumeContainer && {_container != ""}) then {
    private _itemReceipt = [_medic,_patient,[_container]] call ACME_fnc_treatmentSupplyTake;
    if (_itemReceipt isEqualTo []) then {_valid = false;} else {_items pushBack _itemReceipt;};
};
if (!_valid) exitWith {
    {[_holder, _x select 0, _x select 1, _medic] call ACME_fnc_vialRefund;} forEach _taken;
    false
};
if (_reserve) then {
    private _serial = (missionNamespace getVariable ["ACME_medicationSourceSerial",0]) + 1;
    missionNamespace setVariable ["ACME_medicationSourceSerial",_serial];
    private _id = format ["source:%1:%2:%3",clientOwner,floor (serverTime * 1000),_serial];
    _result = [_medic,_items,[_holder,_taken],_id];
    private _pending = missionNamespace getVariable ["ACME_medicationSourceReceipts",createHashMap];
    _pending set [_id,+_result];
    missionNamespace setVariable ["ACME_medicationSourceReceipts",_pending];
} else {
    {[_x,false] call ACME_fnc_treatmentSupplyRefund;} forEach _items;
    _result = true;
};
false
};
_result
