params ["_p"];
private _bag = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Move_IVBagContents", []];
private _id = _bag param [8, ""];
[_p, "bagMove", [_p, ACE_player, _id, "cancel", "", true, -1, missionNamespace getVariable ["ACME_moveEpoch", -1], missionNamespace getVariable ["ACME_moveToken", ""]]] call ACME_fnc_ownerDispatch;
