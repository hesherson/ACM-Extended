/* B277: nine native pictures; create nothing on refresh, preserve the radius in screen pixels. */
disableSerialization;
params ["_group","_rect",["_profile","panel"],["_radius",0.007],["_show",true],["_tint",[1,1,1,1]]];
if (isNull _group) exitWith {false};
[_group,"show",_show] call ACME_fnc_transfusionUiSet;
if (!_show) exitWith {true};
private _signature = [_rect,_profile,_radius,pixelW,pixelH,_tint];
if ((_group getVariable ["ACME_txFrameSignature",[]]) isEqualTo _signature) exitWith {true};
_group setVariable ["ACME_txFrameSignature",_signature];
[_group,"position",_rect] call ACME_fnc_transfusionUiSet;
_rect params ["","","_w","_h"];
// One integer pixel radius is shared by every corner. Fractional screen-unit
// radii can round differently on opposing slices when the UI is stretched.
private _radiusPixels = floor (((safeZoneH * _radius / pixelH) min (_h / pixelH / 2) min (_w / pixelW / 2)) max 0);
private _ry = _radiusPixels * pixelH;
private _rx = _radiusPixels * pixelW;
private _widths = [_rx,(_w - 2 * _rx) max 0,_rx];
private _heights = [_ry,(_h - 2 * _ry) max 0,_ry];
private _xs = [0,_rx,_w - _rx];
private _ys = [0,_ry,_h - _ry];
private _parts = ["tl","top","tr","left","center","right","bl","bottom","br"];
for "_i" from 0 to 8 do {
    private _col = _i mod 3;
    private _row = floor (_i / 3);
    private _piece = _group controlsGroupCtrl _i;
    [_piece,"position",[_xs select _col,_ys select _row,_widths select _col,_heights select _row]] call ACME_fnc_transfusionUiSet;
    [_piece,"text",format ["\acm_extended\ui\transfusion\%1_%2_ca.paa",_profile,_parts select _i]] call ACME_fnc_transfusionUiSet;
    [_piece,"color",_tint] call ACME_fnc_transfusionUiSet;
    _piece ctrlEnable false;
};
true
