/* Commit applied antiseptic at an input boundary, including close/tool/side changes.
 * The owner merges these points with its current trail; a provider snapshot is never a replacement.
 */
params [["_side", "", [""]]];
private _patient = uiNamespace getVariable ["ACME_Thora_Patient", objNull];
if (isNull _patient) exitWith {};
private _epoch = uiNamespace getVariable ["ACME_Thora_PrepEpoch", -1];
if (_epoch != ([_patient] call ACME_fnc_clinicalEpoch)) exitWith {};
private _prepLocal = uiNamespace getVariable ["ACME_Thora_PrepLocal", createHashMap];
if !(_prepLocal isEqualType createHashMap) exitWith {};
private _sides = if (_side == "") then {["left", "right"]} else {[_side]};
{
    private _points = +(_prepLocal getOrDefault [_x, []]);
    private _published = _patient getVariable [format ["ACME_thora_prep_%1", _x], []];
    if (_points findIf {!(_x in _published)} >= 0) then {
        [_patient, "thoraPrepCommit", [_patient, _x, _points, _epoch]] call ACME_fnc_ownerDispatch;
    };
} forEach _sides;
