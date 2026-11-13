/* Select an actual carrier; the selector exposes separate identical coolers. */
params [["_sid",""],["_placementPatient",objNull]];
uiNamespace setVariable ["ACME_CLR_Box",objNull];
private _rows=[ACE_player] call ACME_fnc_coolerRows;
private _hit=_rows findIf {(_x select 0)==_sid || {((_x select 1) select 0)==_sid}};
if (_hit<0) exitWith {};
_sid=(_rows select _hit) select 0;
uiNamespace setVariable ["ACME_CLR_Id",_sid];
private _inv=findDisplay 602;
if (!isNull _inv) then {_inv closeDisplay 2;};
[{
    params ["_sid","_placementPatient"];
    if ((([ACE_player] call ACME_fnc_coolerRows) findIf {(_x select 0)==_sid})<0) exitWith {};
    uiNamespace setVariable ["ACME_CLR_Id",_sid];
    if (createDialog "ACME_CoolerManager_Dialog") then {
        (uiNamespace getVariable ["ACME_CLR_DLG",displayNull]) setVariable ["ACME_CLR_PlacementPatient",_placementPatient];
        call ACME_fnc_coolerRefresh;
    };
},[_sid,_placementPatient]] call CBA_fnc_execNextFrame;
