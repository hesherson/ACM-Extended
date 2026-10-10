/* A real gauge-specific needle magnetizes only near an existing lock port.
   Return true also for unsuitable gauges: a blocked lock click must not puncture skin. */
params ["_ctrl","_cursor"];
private _target=[_cursor select 0,_cursor select 1,"field"] call ACME_fnc_ivFinishTarget;
if (_target isEqualTo []) exitWith {false};
private _row=_target select 0;
private _gauge=uiNamespace getVariable ["ACME_IV_Gauge",16];
private _child=[_row,_gauge] call ACME_fnc_ivFieldSecondaryRow;
if (_child isEqualTo []) exitWith {false};
private _r=uiNamespace getVariable ["ACME_IV_BodyRect",[]];
private _x=(_r select 0)+(_r select 2)*(_child select 2);
private _y=(_r select 1)+(_r select 3)*(_child select 3);
private _frame=_row param [6,""];private _angle=_row param [13,0];
_ctrl ctrlSetText ([_gauge,_frame,0] call ACME_fnc_ivCathTex);
private _g=[_frame,_angle] call ACME_fnc_ivCathGeometry;
_g params ["_w","_h","_pivot"];
private _rect=[_x-_w*(_pivot select 0),_y-_h*(_pivot select 1),_w,_h];
private _magnet=[_cursor,_target select 2,_rect,_angle,_pivot,pixelW/(pixelH max 1e-9),_r select 3] call ACME_fnc_ivMagnetGeometry;
_ctrl ctrlSetPosition (_magnet select 0);
_ctrl ctrlSetAngle [_magnet select 1,_pivot select 0,_pivot select 1,false];_ctrl ctrlCommit 0;
_ctrl setVariable ["ACME_IV_Pose",[]];
uiNamespace setVariable ["ACME_IV_LastNeedleState",[]];
_ctrl ctrlShow true;
true
