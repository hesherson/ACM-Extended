/* Current UI episode plus optional captured dialog session. Pure read, no throttle. */
params [["_captured", []]];
private _p = uiNamespace getVariable ["ACME_IV_Patient", objNull];
private _token = uiNamespace getVariable ["ACME_IV_Session", []];
!isNull _p && {count _token == 3} && {(_token select 0) isEqualTo _p}
    && {(_token select 1) == ([_p] call ACME_fnc_clinicalEpoch)}
    && {_captured isEqualTo [] || {_captured isEqualTo _token}}
    && {_captured isNotEqualTo [] || {[] call ACME_fnc_ivInteractionValid}}
