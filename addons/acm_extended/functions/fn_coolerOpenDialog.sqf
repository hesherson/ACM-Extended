/* Select an actual carrier; the selector exposes separate identical coolers. */
params [["_sid",""]];
private _rows=[ACE_player] call ACME_fnc_coolerRows;
private _hit=_rows findIf {(_x select 0)==_sid || {((_x select 1) select 0)==_sid}};
if (_hit<0) exitWith {};
_sid=(_rows select _hit) select 0;
uiNamespace setVariable ["ACME_CLR_Id",_sid];
private _inv=findDisplay 602;
if (!isNull _inv) then {_inv closeDisplay 2;};
[{
    params ["_sid"];
    if ((([ACE_player] call ACME_fnc_coolerRows) findIf {(_x select 0)==_sid})<0) exitWith {};
    uiNamespace setVariable ["ACME_CLR_Id",_sid];
    createDialog "ACME_CoolerManager_Dialog";
},[_sid]] call CBA_fnc_execNextFrame;
