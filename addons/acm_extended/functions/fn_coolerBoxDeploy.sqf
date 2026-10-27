private _rows=[ACE_player] call ACME_fnc_coolerRows;
if (_rows isEqualTo []) exitWith {};
private _sid=uiNamespace getVariable ["ACME_CLR_Id",""];
if ((_rows findIf {(_x select 0)==_sid})<0) then {_sid=(_rows select 0) select 0;};
["deploy",ACE_player,_sid] call ACME_fnc_coolerBoxRequest;
