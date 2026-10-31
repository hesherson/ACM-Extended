params ["_m","_p","_token","_ok","_message"];
if (isNull _m || {!local _m}) exitWith {};
private _pending=_m getVariable ["ACME_fbtkPending",[]];
if (count _pending<5 || {(_pending select 0) isNotEqualTo _p} || {(_pending select 1)!=_token}) exitWith {};
_m setVariable ["ACME_fbtkPending",[]];
[_pending select 2,!_ok] call ACME_fnc_treatmentSupplyRefund;
if (_message!="") then {[_message,3,_m] call ace_common_fnc_displayTextStructured;};
private _d=_pending select 4;
if (!isNull _d && {_d isEqualTo findDisplay 86000} && {(missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target",objNull]) isEqualTo _p}) then {
    [] call ACM_circulation_fnc_TransfusionMenu_UpdateBagList;
    [false] call ACM_circulation_fnc_TransfusionMenu_SwitchTargetInventory;
    [] call ACME_fnc_updateTransfusionControls;
};
