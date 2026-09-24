// Side occupancy and item consumption are serialized, not checked against a stale panel.
params ["_patientSide"];
if !(_patientSide in ["left", "right"]) exitWith {};
if !(["ncd", [_patientSide], "ACME_NARSPEAR"] call ACME_fnc_chestSealRequest) exitWith {};

// Show the accepted click immediately. The server remains authoritative and the next
// snapshot removes this prediction if the request is rejected. This prevents a valid
// NCD from looking inert while the request waits for its acknowledgement.
private _snapshot = uiNamespace getVariable ["ACME_CS_netSnapshot", []];
if (_snapshot isEqualType [] && {count _snapshot >= 5}) then {
    private _predicted = +(_snapshot select 4);
    _predicted pushBackUnique _patientSide;
    _snapshot set [4, _predicted];
    uiNamespace setVariable ["ACME_CS_netSnapshot", _snapshot];
};
uiNamespace setVariable ["ACME_CS_SpearHeld", false];
private _medic = uiNamespace getVariable ["ACME_CS_Medic", objNull];
uiNamespace setVariable ["ACME_CS_SpearsLeft", if (isNull _medic) then {0} else {[_medic, "ACME_NARSPEAR"] call ACME_fnc_itemCount}];
// B52: successful NAR SPEAR seating gets exactly one requested NCD gesture.
if (!isNull _medic && {local _medic}) then {[_medic,"ncdSeat",2.0] call ACME_fnc_treatmentGesture;};

playSound "ACME_NARSPEAR_Pierce";
[] call ACME_fnc_chestSealRefreshSpearSlot;
[] call ACME_fnc_chestSealRender;
[] call ACME_fnc_chestSealPrompt;
