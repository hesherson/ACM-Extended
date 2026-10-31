private _dlg=uiNamespace getVariable ["ACME_CLR_DLG",displayNull];
if (isNull _dlg) exitWith {};
private _sid=uiNamespace getVariable ["ACME_CLR_Id",""];
private _list=_dlg displayCtrl 87410;
private _selection=lbCurSel _list;
if (_selection<0) exitWith {};
private _index=parseNumber(_list lbData _selection);
private _rendered=_dlg getVariable ["ACME_CLR_RenderState",[]];
if (count _rendered!=2 || {(_rendered select 0)!=_sid}) exitWith {};
private _renderState=_rendered select 1;
if (_index<0 || {_index>=count (_renderState select 2)}) exitWith {};
[ACE_player,_sid,{
    params ["_owner","_sid","_state","_args"];
    _args params ["_index","_renderState"];
    private _expectedState=[_renderState,serverTime] call ACME_fnc_coolerAdvance;
    private _expected=(_expectedState select 2) select _index;
    private _entries=+(_state select 2);
    if (_index>=count _entries || {((_entries select _index) select 0)!=(_expected select 0)} || {abs (((_entries select _index) select 1)-(_expected select 1))>0.001}) exitWith {[]};
    if !([_owner,_entries select _index,true] call ACME_fnc_coolerGiveBag) exitWith {[]};
    _entries deleteAt _index;_state set [2,_entries];
    [false,_state]
},[_index,_renderState]] call ACME_fnc_coolerMutate;
