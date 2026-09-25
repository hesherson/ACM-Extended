/* Shared onset-aware procedure support.
   Returns [localLidocaine, systemicKetamineNormalized]. Local lidocaine is queried on the actual body part;
   systemic ketamine/esketamine uses the common route/onset-aware ketamine reader. Analgesia is not hypnosis. */
params ["_patient", ["_bodyPart", "body"]];
if (isNull _patient || {isNil "ace_medical_status_fnc_getMedicationCount"}) exitWith {[0,0]};
_bodyPart = toLowerANSI _bodyPart;
if (_bodyPart == "ej") then {_bodyPart = "head";};
private _parts = ["head","body","leftarm","rightarm","leftleg","rightleg"];
private _pi = _parts find _bodyPart;
private _localLid = 0;
if (_pi >= 0) then {
    private _v = [_patient,"Lidocaine",false,_pi] call ACME_fnc_medicationCountCompat;
    if (_v isEqualType 0 && {finite _v}) then {_localLid = _v max 0;};
};
private _ketNorm = ([_patient] call ACME_fnc_ketamineOnBoard)
    / ((missionNamespace getVariable ["ACME_ket_induceThreshold",7]) max 0.1);
[_localLid, _ketNorm max 0]
