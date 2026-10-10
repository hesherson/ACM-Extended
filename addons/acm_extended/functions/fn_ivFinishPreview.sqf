/* Full-size instrument preview with gradual contact-point attraction. */
params ["_ctrl","_tool","_cursor"];
if (isNull _ctrl || {count _cursor!=2}) exitWith {};
private _d=uiNamespace getVariable ["ACME_IV_DLG",displayNull];
private _buttons=(_d getVariable ["ACME_IV_FinishTray",[]]) apply {_x select 3};
{_buttons pushBack (_d displayCtrl _x);} forEach [86532,86537,86543,86547,86551,86559,86555];
private _overTray=(_buttons findIf {
    private _r=ctrlPosition _x;
    (ctrlShown _x) && {(_cursor select 0)>=(_r select 0)} && {(_cursor select 0)<=(_r select 0)+(_r select 2)}
        && {(_cursor select 1)>=(_r select 1)} && {(_cursor select 1)<=(_r select 1)+(_r select 3)}
})>=0;
if (_overTray) exitWith {_ctrl ctrlShow false;};
private _target=[_cursor select 0,_cursor select 1,_tool] call ACME_fnc_ivFinishTarget;
private _texture=if (_tool=="lock") then {"\acm_extended\ui\iv\field\lock_ca.paa"} else {format ["\acm_extended\ui\iv\finish\cursor_%1_ca.paa",_tool]};
if ((ctrlText _ctrl)!=_texture) then {_ctrl ctrlSetText _texture;};
if (_target isNotEqualTo []) then {
    private _row=_target select 0;private _state=_row param [15,[]];
    private _field=_tool=="lock" || {_tool=="dressing" && {_state param [4,false]}};
    private _paintRow=_row;
    if (_field) then {
        if (_tool=="dressing") then {
            _ctrl ctrlSetText format ["\acm_extended\ui\iv\field\dressing_%1_ca.paa",["lock","field"] select ((_state param [5,0])>0)];
        };
    } else {
        private _direct=(_state param [4,false]) && {!(_state param [0,false])} && {_tool in ["line","flush"]};
        if (_direct && {_tool=="flush"}) then {_ctrl ctrlSetText "\acm_extended\ui\iv\field\cursor_flush_ca.paa";};
        _paintRow=[_row,_direct] call ACME_fnc_ivFieldAccessoryRow;
    };
    private _g=[_paintRow] call ACME_fnc_ivFinishGeometry;
    if (_g isNotEqualTo []) then {
        _g params ["_x","_y","_w","_h","_angle"];
        private _pivot=if (_field) then {[0.5,0.5]} else {if (_tool in ["extension","flush","line"]) then {[1006.5/2048,1052/2048]} else {[1006.5/2048,1032/2048]}};
        if (_field) then {_w=_w*2;_h=_h*2;};
        private _rect=[_x-_w*(_pivot select 0),_y-_h*(_pivot select 1),_w,_h];
        private _body=uiNamespace getVariable ["ACME_IV_BodyRect",[0,0,1,1]];
        private _magnet=[_cursor,_target select 2,_rect,_angle,_pivot,pixelW/(pixelH max 1e-9),_body select 3] call ACME_fnc_ivMagnetGeometry;
        _ctrl ctrlSetPosition (_magnet select 0);
        _ctrl ctrlSetAngle [_magnet select 1,_pivot select 0,_pivot select 1,false];_ctrl ctrlCommit 0;
    };
} else {
    // Free tool keeps the catheter-scale canvas and its logical contact point.
    private _r=uiNamespace getVariable ["ACME_IV_BodyRect",[0,0,1,1]];
    private _h=(_r select 3)*(uiNamespace getVariable ["ACME_IV_CathScale",0.62]);
    private _w=_h*(pixelW/(pixelH max 1e-9));
    if (_tool=="lock") then {_w=_w*2;_h=_h*2;};
    private _uv=if (_tool=="lock") then {[0.5,0.5]} else {if (_tool in ["flush","line"]) then {[1033.02/2048,1386.52/2048]} else {[1006.5/2048,1032/2048]}};
    _ctrl ctrlSetAngle [0,_uv select 0,_uv select 1,false];
    _ctrl ctrlSetPosition [(_cursor select 0)-_w*(_uv select 0),(_cursor select 1)-_h*(_uv select 1),_w,_h];
    _ctrl ctrlCommit 0;_ctrl setVariable ["ACME_IV_FinishPose",[]];_ctrl setVariable ["ACME_IV_FieldPose",[]];
};
_ctrl setVariable ["ACME_IV_FinishPose",[]];_ctrl setVariable ["ACME_IV_FieldPose",[]];
_ctrl ctrlShow true;
