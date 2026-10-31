/* Read the actual native access and its existing compromise/flow complications.
   No aspiration result is inferred from the selected icon or an animation. */
params ["_patient", "_row"];
private _bp = toLower (_row param [0, ""]);
if (_bp == "ej") then {_bp = "head";};
private _site = [_row param [10, ""]] call ACME_fnc_ivSiteIndex;
[_patient,_bp,0,_site] call ACM_circulation_fnc_hasIV
    && {!(_patient getVariable [format ["ACME_ivCompromised_%1_%2",_bp,_site],false])}
