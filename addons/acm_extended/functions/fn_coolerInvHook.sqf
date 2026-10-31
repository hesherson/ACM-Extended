/* Inventory rows select the carrier type; the manager selects individual IDs. */
params ["_unit"];
if (_unit isNotEqualTo ACE_player) exitWith {};
[{
    private _dlg=findDisplay 602;
    if (isNull _dlg) exitWith {};
    {
        private _ctrl=_dlg displayCtrl _x;
        if (!isNull _ctrl && {isNil {_ctrl getVariable "ACME_clrHook"}}) then {
            _ctrl setVariable ["ACME_clrHook",true];
            _ctrl ctrlAddEventHandler ["LBDblClick",{
                params ["_control","_index"];
                private _class=_control lbData _index;
                private _picture=toLowerANSI(_control lbPicture _index);
                private _rows=[ACE_player] call ACME_fnc_coolerRows;
                private _hit=_rows findIf {
                    private _base=(_x select 1) select 0;
                    _base==_class || {("ACME_CoolerCarrier_"+(_base select [17]))==_class}
                    || {_picture!="" && {toLowerANSI(getText(configFile >> "CfgWeapons" >> _base >> "picture"))==_picture}}
                };
                if (_hit>=0) then {[(_rows select _hit) select 0] call ACME_fnc_coolerOpenDialog;};
            }];
        };
    } forEach [632,633,638,619];
},[]] call CBA_fnc_execNextFrame;
