/* Consume measured solution before dispatch. No fictional fixed-dose charge conversion. */
params ["_medic", "_patient", "_bodyPart", "_index", "_pushMl", ["_siteIdx", -2], ["_pushSec", 3]];
if !(_pushSec isEqualType 0 && {finite _pushSec} && {_pushSec > 0}) then {_pushSec = 3;};
_pushSec = (_pushSec max 1) min 300;
if (isNull _medic || {!local _medic} || {isNull _patient}) exitWith {false};
if (_medic distance _patient > 5 && {isNull objectParent _medic || {objectParent _medic != objectParent _patient}}) exitWith {false};
if (!finite _pushMl || {_pushMl <= 0}) exitWith {false};
if (!([_patient, _bodyPart, 0] call ACM_circulation_fnc_hasIV) && {!([_patient, _bodyPart, 0] call ACM_circulation_fnc_hasIO)}) exitWith {false};
private _selectedPresent = if (_siteIdx >= 0) then {[_patient, _bodyPart, 0, _siteIdx] call ACM_circulation_fnc_hasIV} else {
    _siteIdx != -1 || {[_patient, _bodyPart, 0] call ACM_circulation_fnc_hasIO}
};
if (!_selectedPresent) exitWith {false};
private _store = _medic getVariable ["ACME_narcStore", []];
if (_index < 0 || {_index >= count _store}) exitWith {false};
private _entry = +(_store select _index);
if ((_entry param [6, ""]) != "epiMixB12" || {(_entry param [0, ""]) != "EpinephrineCardiac"}) exitWith {false};
private _drugMl = _entry param [2, 0];
private _nsMl = _entry param [4, 0];
private _total = _drugMl + _nsMl;
if (_drugMl <= 0 || {_nsMl < 0} || {_total <= 0} || {_pushMl > _total + 0.00001}) exitWith {false};
_pushMl = _pushMl min _total;
private _fraction = _pushMl / _total;
private _doseMg = _drugMl * 0.1 * _fraction;
private _refundRow = +_entry;
_refundRow set [2,_drugMl * _fraction];
_refundRow set [4,_nsMl * _fraction];
_refundRow set [3,format ["Push-dose epinephrine 10 mcg/mL (%1 mL)",_pushMl toFixed 1]];
private _remaining = (_total - _pushMl) max 0;
if ((_entry param [13,"",[""]]) == "inventoryB279") exitWith {
    private _request = [_medic,_entry] call ACME_fnc_skInventoryReserve;
    if (_request == "") exitWith {false};
    private _remainingRow = [];
    if (_remaining >= 0.001) then {
        _remainingRow = +_entry;
        _remainingRow set [2,_drugMl * (1 - _fraction)];
        _remainingRow set [4,_nsMl * (1 - _fraction)];
        _remainingRow set [3,format ["Push-dose epinephrine 10 mcg/mL (%1 mL = %2 mcg left)",_remaining toFixed 1,(_remaining*10) toFixed 0]];
    };
    [_medic,_request,ACME_fnc_skInventoryInjectClaim,[_medic,_patient,_bodyPart,[["Epinephrine_IV",_doseMg,true,"B13_MEASURED_EPI",_pushSec]],_siteIdx,_entry,_remainingRow,_refundRow,_request],true] call ACME_fnc_inventoryLedgerClaim;
    true
};
if (_remaining < 0.001) then {_store deleteAt _index;} else {
    _entry set [2, _drugMl * (1 - _fraction)];
    _entry set [4, _nsMl * (1 - _fraction)];
    _entry set [3, format ["Push-dose epinephrine 10 mcg/mL (%1 mL = %2 mcg left)", _remaining toFixed 1, (_remaining * 10) toFixed 0]];
    _store set [_index, _entry];
};
[_medic, _store] call ACME_fnc_narcStoreCommit;
// The solution already carries its diluent. Use the native drug and actual mg, once.
[_medic, _patient, _bodyPart, [["Epinephrine_IV", _doseMg, true, "B13_MEASURED_EPI", _pushSec]], "administer", _siteIdx, [[],[_refundRow],[]]] call ACME_fnc_medicationRequest;
private _label = format ["Epinephrine %1 mcg / %2 mL IV/IO", (_doseMg * 1000) toFixed 0, _pushMl toFixed 1];
[format ["%1 submitted. %2 mL remaining.", _label, _remaining toFixed 1], 3, _medic] call ace_common_fnc_displayTextStructured;
true
