/* B233: shared physical-square accessory transform. The authored extension's
   proximal socket is registered to the catheter's real hub, not its skin tip.
   Returns [socketX,socketY,width,height,angle]. */
params ["_row"];
private _r=uiNamespace getVariable ["ACME_IV_BodyRect",[]];
if (count _r!=4 || {count _row<7}) exitWith {[]};
_r params ["_bx","_by","_bw","_bh"];
private _suffix=_row param [6,""];
private _extra=_row param [13,0];
private _anchor=(uiNamespace getVariable ["ACME_IV_FrameAnchors",createHashMap]) getOrDefault [_suffix,[0.49166,0.44434]];
private _legacyHub=(uiNamespace getVariable ["ACME_IV_LineAnchors",createHashMap]) getOrDefault [_suffix,[0.49246,0.50391]];
private _hub=(uiNamespace getVariable ["ACME_IV_HubSockets",createHashMap]) getOrDefault [_suffix,_legacyHub];
private _legacyAxis=(uiNamespace getVariable ["ACME_IV_FrameAxis",createHashMap]) getOrDefault [_suffix,[0,-1]];
private _axis=(uiNamespace getVariable ["ACME_IV_HubAxes",createHashMap]) getOrDefault [_suffix,_legacyAxis];
private _h=_bh*(uiNamespace getVariable ["ACME_IV_CathScale",0.62]);
private _w=_h*(pixelW/(pixelH max 1e-9));
private _du=(_hub select 0)-(_anchor select 0);
private _dv=(_hub select 1)-(_anchor select 1);
private _x=_bx+_bw*(_row select 2)+_w*(_du*cos _extra-_dv*sin _extra);
private _y=_by+_bh*(_row select 3)+_h*(_du*sin _extra+_dv*cos _extra);
[_x,_y,_w,_h,((_axis select 0) atan2 (-(_axis select 1)))+_extra]
