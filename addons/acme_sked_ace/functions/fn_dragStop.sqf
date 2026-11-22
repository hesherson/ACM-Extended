/*
 * On the rescuer's machine: let go. The target is set down where it is, the helper is removed, and the server
 * is told. Safe to call when nothing is being dragged.
 * Arguments: 0: rescuer, 1: tell the server <BOOL> (default: true).
 */
params ["_unit", ["_tell", true]];
private _state = _unit getVariable ["acme_drag_state", []];
_unit setVariable ["acme_drag_state", nil];
if (_state isNotEqualTo []) then {
    _state params ["_target", "_body", "_pfh", "_key", ["_carrier", objNull], ["_geometry", []]];
    [_unit] call acme_sked_fnc_carryBandEnd;
    [_unit, "acme_drag", true] call acme_sked_fnc_dragPace;
    // the strap of a SKED (fn_dragStrapAim.sqf) is laid flat again
    if (!isNull _body && {getNumber (configOf _body >> "acmeDragStrap") > 0}) then {[_unit, _body, true] call acme_sked_fnc_dragStrapAim;};
    [_pfh] call CBA_fnc_removePerFrameHandler;
    [_key, "keydown"] call CBA_fnc_removeKeyHandler;
    if (_unit isEqualTo (call ace_common_fnc_player)) then {[] call ace_interaction_fnc_hideMouseHint;};
    [_unit, "forceWalk", "acme_drag", false] call ace_common_fnc_statusEffect_set;
    [_unit, "blockSprint", "acme_drag", false] call ace_common_fnc_statusEffect_set;
    if (!isNull _body) then {
        private _holder = attachedTo _body;
        if (!isNull _holder && {_holder isEqualTo _unit || {_holder isEqualTo _carrier}}) then {
            private _at = getPosWorldVisual _body;
            private _dir = vectorDirVisual _body;
            private _up = vectorUpVisual _body;
            // (its two ends, for a litter that has to be set down flat)
            private _front = _body modelToWorldVisualWorld ((_geometry param [0, [0, 0, 0]]));
            private _back = _body modelToWorldVisualWorld ((_geometry param [1, [0, 0, 0]]));
            detach _body;
            // (a casualty who was put into a vehicle while dragged stays in it)
            if (isNull objectParent _body) then {_body setPosWorld _at;};
            if !(_body isKindOf "CAManBase") then {
                if (_geometry isNotEqualTo [] && {(_geometry select 4) > 0} && {isNull objectParent _body}) then {
                    // a litter that was held by its handles is set down flat where it is
                    _geometry params ["_tow", "_rear", "_rise", "_length"];
                    private _hx = (_front select 0) - (_back select 0);
                    private _hy = (_front select 1) - (_back select 1);
                    private _h = (sqrt (_hx * _hx + _hy * _hy)) max 0.01;
                    _hx = _hx / _h;
                    _hy = _hy / _h;
                    ([_front, _back, getPosASL _unit, _body, _unit] call acme_sked_fnc_dragLie) params ["_zFront", "_zRear", "_side"];
                    private _t = ((((_at select 0) - (_back select 0)) * _hx + ((_at select 1) - (_back select 1)) * _hy) / _length) max 0 min 1;
                    private _along = vectorNormalized [_hx * _length, _hy * _length, _zFront - _zRear];
                    _up = (vectorNormalized [_hy, -_hx, _side]) vectorCrossProduct _along;
                    private _flat = vectorNormalized [_dir select 0, _dir select 1, 0];
                    _dir = vectorNormalized (_flat vectorDiff (_up vectorMultiply (_flat vectorDotProduct _up)));
                    _body setPosWorld [_at select 0, _at select 1, _zRear + (_zFront - _zRear) * _t + _rise];
                };
                // (a thing can only be turned where it is local: the machine it belongs to sets it down)
                ["acme_drag_setDown", [_body, getPosWorld _body, _dir, _up], _body] call CBA_fnc_targetEvent;
            };
        };
        // a casualty who still lies in the drag's own pose goes back to an ordinary one
        if (_body isEqualTo _target && {_body isKindOf "CAManBase"} && {alive _body}
            && {(toLowerANSI animationState _body) in ["acme_drag_rest", "acme_drag_limp"]}) then {
            [_body, ["AmovPpneMstpSnonWnonDnon", "unconscious"] select (_body getVariable ["ACE_isUnconscious", false]), 2] call ace_common_fnc_doAnimation;
        };
        if (_body isNotEqualTo _target) then {
            // a dead body was dragged as ACE's clone of it: the body is put where the clone lies
            [_unit, _body, false] call ace_dragging_fnc_deleteClone;
            if (!isNull _target) then {_target setVariable ["acme_drag_clone", nil, true];};
        };
    };
    if (!isNull _carrier) then {deleteVehicle _carrier;};
    if (!isNull _target) then {["acme_drag_stopped", [_unit, _target]] call CBA_fnc_localEvent;};
};
if (_tell) then {[_unit, "dragEnd"] call acme_sked_fnc_request;};
