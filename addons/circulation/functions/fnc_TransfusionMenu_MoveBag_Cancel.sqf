params ["_p"];
private _medic = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Medic", objNull];
if (isNull _medic) then {_medic = call ACME_fnc_controlledProvider;};
if (isNull _medic) exitWith {};
private _bag = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Move_IVBagContents", []];
private _id = _bag param [8, ""];
[_p, "bagMove", [_p, _medic, _id, "cancel", "", true, -1, missionNamespace getVariable ["ACME_moveEpoch", -1]]] call ACME_fnc_ownerDispatch;
