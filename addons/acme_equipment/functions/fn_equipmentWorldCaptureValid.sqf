/* Revalidate immediately before committing the coordinated mission checkpoint. */
params ["_save"];
if (canSuspend) exitWith {private _result = false;isNil {_result = [_save] call ACME_fnc_equipmentWorldCaptureValid;};_result};
if (!isServer || {isRemoteExecuted} || {!([_save] call ACME_fnc_equipmentWorldSchema)}) exitWith {false};
private _current = call ACME_fnc_equipmentWorldSnapshot;
_current isNotEqualTo [] && {_current isEqualTo _save}
