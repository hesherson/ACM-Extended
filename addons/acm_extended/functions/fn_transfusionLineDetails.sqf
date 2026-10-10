/* Open a read-only snapshot of the exact access selected on the existing body map. */
private _menu = findDisplay 86000;
if (isNull _menu || {!isNull (findDisplay 86200)} || {!isNull (findDisplay 84000)}) exitWith {};
private _patient = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target", objNull];
private _part = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart", ""];
private _iv = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_SelectIV", true];
private _site = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite", -1];
if (isNull _patient || {_part == ""} || {_site < 0}) exitWith {};
uiNamespace setVariable ["ACME_TransfusionDetailsContext", [_patient,_part,_iv,_site,ctrlText (_menu displayCtrl 86002)]];
if (createDialog "ACME_TransfusionDetails_Dialog") then {call ACME_fnc_updateTransfusionLineDetails;};
