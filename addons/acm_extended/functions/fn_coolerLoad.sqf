private _dlg=uiNamespace getVariable ["ACME_CLR_DLG",displayNull];
if (isNull _dlg) exitWith {};
private _sid=uiNamespace getVariable ["ACME_CLR_Id",""];
private _list=_dlg displayCtrl 87411;
private _index=lbCurSel _list;
if (_index<0) exitWith {};
[ACE_player,_sid,_list lbData _index] call ACME_fnc_coolerLoadRequest;
