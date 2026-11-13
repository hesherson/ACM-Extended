private _rows=[ACE_player] call ACME_fnc_coolerRows;
if (_rows isEqualTo []) exitWith {};
private _sid=uiNamespace getVariable ["ACME_CLR_Id",""];
if ((_rows findIf {(_x select 0)==_sid})<0) then {_sid=(_rows select 0) select 0;};
private _dialog = uiNamespace getVariable ["ACME_CLR_DLG",displayNull];
private _patient = _dialog getVariable ["ACME_CLR_PlacementPatient",objNull];
if (isNull _patient || {ACE_player distance _patient > 4}) exitWith {};
if (["deploy",ACE_player,_sid,objNull,[],_patient] call ACME_fnc_coolerBoxRequest) then {
    _dialog closeDisplay 2;
};
