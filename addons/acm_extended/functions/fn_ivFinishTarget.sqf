/* Nearest current-view component, in physical pixel units. Used for both
   magnetic previews and click acceptance; never target a last-used catheter. */
params ["_ux","_uy","_tool",["_pull",false],["_close",false]];
private _p=uiNamespace getVariable ["ACME_IV_Patient",objNull];
private _bp=uiNamespace getVariable ["ACME_IV_BodyPart",""];
private _view=uiNamespace getVariable ["ACME_IV_View",""];
private _rect=uiNamespace getVariable ["ACME_IV_BodyRect",[]];
if (isNull _p || {count _rect!=4}) exitWith {[]};
private _aspect=pixelW/(pixelH max 1e-9);
// Keep the visual magnet's hard seat at 0.4% body height, but make mouse
// acceptance forgiving once the tool is visibly attracting toward a socket.
private _radius=(_rect select 3)*(if (_pull) then {0.025} else {if (_close) then {0.018} else {0.052}});
private _best=[];private _distance=_radius;
private _deepOrigin=[1006.5/2048,1052/2048];
{
    private _row=_x;
    if ((_row param [4,""])=="hub" && {(_row select 0)==_bp} && {(_row select 1)==_view}) then {
        private _state=_row param [15,[false,false,false,false]];
        private _points=[];
        if (_state param [4,false]) then {
            if (_pull) then {
                _points pushBack ["catheter",[(_rect select 0)+(_rect select 2)*(_row select 2),(_rect select 1)+(_rect select 3)*(_row select 3)]];
                _points pushBack ["removeLock",[_row,[1006.5,1060]] call ACME_fnc_ivFieldPoint];
                if ((_state param [5,0])>0) then {_points pushBack ["removeSecondary",[_row,[1006.5,1140]] call ACME_fnc_ivFieldPoint];};
                private _y=if ((_state param [5,0])>0) then {1189} else {1088};
                if (_state select 0) then {_points pushBack ["removeExtension",[_row,[1007,_y+190]] call ACME_fnc_ivFieldPoint];};
                if ((_state select 2) || {_state param [6,false]}) then {_points pushBack ["removeDressing",[_row,[1120,970]] call ACME_fnc_ivFieldPoint];};
                if (_state select 3) then {_points pushBack ["removeLine",[_row,[1100,_y+(if (_state select 0) then {650} else {310})]] call ACME_fnc_ivFieldPoint];};
            } else {
                private _point=switch (_tool) do {
                    case "field";case "field14";case "field16": {[1006.5,1088]};
                    case "extension": {[1006.5,if ((_state param [5,0])>0) then {1189} else {1088}]};
                    case "dressing";case "lock": {[1006.5,1037]};
                    default {[_row] call ACME_fnc_ivFieldPort};
                };
                _points pushBack [_tool,[_row,_point] call ACME_fnc_ivFieldPoint];
            };
        } else {
        if (_tool in ["field","field14","field16"]) then {} else {
        if (_pull) then {
            _points pushBack ["catheter",[(_rect select 0)+(_rect select 2)*(_row select 2),(_rect select 1)+(_rect select 3)*(_row select 3)]];
            if (_state select 0) then {_points pushBack ["removeExtension",[_row,[1007/2048,1230/2048],_deepOrigin] call ACME_fnc_ivFinishPoint];};
            if (_state select 2) then {_points pushBack ["removeDressing",[_row,[1140/2048,970/2048]] call ACME_fnc_ivFinishPoint];};
            if (_state select 3) then {_points pushBack ["removeLine",[_row,[1100/2048,1720/2048],_deepOrigin] call ACME_fnc_ivFinishPoint];};
        } else {
            private _deep=_tool in ["extension","flush","line"];
            private _uv=if (_tool in ["flush","line"]) then {[1033.02/2048,1386.52/2048]} else {
                if (_deep) then {_deepOrigin} else {[1006.5/2048,1032/2048]}
            };
            _points pushBack [_tool,if (_deep) then {[_row,_uv,_deepOrigin] call ACME_fnc_ivFinishPoint} else {[_row,_uv] call ACME_fnc_ivFinishPoint}];
        };
        };
        };
        {
            _x params ["_kind","_point"];
            if (count _point==2) then {
                private _dx=(_ux-(_point select 0))/_aspect;private _dy=_uy-(_point select 1);
                private _d=sqrt (_dx*_dx+_dy*_dy);
                if (_d<_distance) then {_distance=_d;_best=[+_row,_kind,_point];};
            };
        } forEach _points;
    };
} forEach (_p getVariable ["ACME_IV_Marks",[]]);
_best
