/*
 * On the rescuer's machine: drag a thing or a casualty. It trails behind the rescuer on a short strap, like a
 * sled: its near end is pulled toward the rescuer when the strap is taut, its far end follows, and it lies on
 * the ground under it. The rescuer walks as usual (no sprint), in any direction, and keeps the ACE menu.
 *
 * The target is attached to the rescuer, and this machine sets where it hangs on them (see the note at the
 * per-frame part below for how, and for what was measured). A unit is drawn anew every frame on every machine,
 * so what hangs on it moves smoothly for everybody; a helper object did not (measured on a dedicated server,
 * 2026-11-18: steps twice a second here, jumps of metres for others). A casualty strapped on a dragged litter
 * stays attached to the litter (fn_patientRoot.sqf). A dead body is dragged as ACE's clone of it, as ACE does.
 *
 * Arguments: 0: rescuer, 1: target.
 */
params ["_unit", "_target"];
if (!local _unit || {isNull _target}) exitWith {};
if ((_unit getVariable ["acme_drag_target", objNull]) isNotEqualTo _target || {!alive _unit}) exitWith {
    [_unit, "dragEnd"] call acme_sked_fnc_request;
};
if (!isNil {_unit getVariable "acme_drag_state"}) then {[_unit, false] call acme_sked_fnc_dragStop;};

private _body = _target;
if (_target isKindOf "CAManBase" && {!alive _target}) then {
    _body = [_unit, _target] call ace_dragging_fnc_createClone;
    // The clone is a living unit and would stand: it lies on its back, as the body it stands in for.
    if (!isNull _body) then {
        private _lying = ["AinjPpneMstpSnonWrflDnon", "ACM_LyingState"] select (isClass (configFile >> "CfgMovesMaleSdr" >> "States" >> "ACM_LyingState"));
        ["ace_common_switchMove", [_body, _lying]] call CBA_fnc_globalEvent;
    };
};
if (isNull _body) exitWith {[_unit, "dragEnd"] call acme_sked_fnc_request;};

// The end that is pulled and the end that trails, in the target's own axes, on the ground.
private _tow = [0, 0, 0];
private _rear = [0, 0, 0];
private _rope = 0.8;
// How far a lifted end is raised (0: the thing is not lifted, it trails flat). See the Talon in Talon.hpp.
private _lift = 0;
// Its strap is taken up to the rescuer's hip (a SKED, fn_dragStrapAim.sqf)?
private _strapped = false;
// A casualty gets a limp pose of his own (tools/build_drag_poses.py), with loose limbs while he is moved. (The
// game cannot make a dragged unit a ragdoll: one that hangs on something never becomes one, and a force does
// nothing to one lying in an animation. Measured 2026-11-18.)
private _limp = _body isKindOf "CAManBase" && {missionNamespace getVariable ["acme_drag_limp", true]}
    && {isClass (configFile >> "CfgMovesMaleSdr" >> "States" >> "ACME_Drag_Limp")}
    // (not one who is wrapped in an HPMK: he stays in the one pose the shell is made for, dragged too; any other
    // pulls the shell out of shape: ACME_fnc_hpmkPose)
    && {!((_body getVariable ["ACME_hpmk_state", ""]) in ["wrapped", "exposed"])};
if (_body isKindOf "CAManBase") then {
    if (_limp) then {
        [_body, "ACME_Drag_Rest", 2] call ace_common_fnc_doAnimation;
        // the neck and the middle of the feet in that pose, as the game has them (measured in game; the axes of
        // the animation file are turned half round against the model's)
        _tow = [-0.07, 0.52, 0];
        _rear = [0.15, -0.99, 0];
    } else {
        _tow = _body selectionPosition ["neck", "Memory"];
        private _feet = ((_body selectionPosition ["leftfoot", "Memory"]) vectorAdd (_body selectionPosition ["rightfoot", "Memory"])) vectorMultiply 0.5;
        if (_tow isEqualTo [0, 0, 0] || {_tow distance2D _feet < 0.6}) then {
            _tow = [0, 0.55, 0];
            _feet = [0, -1.0, 0];
        };
        _rear = _feet;
    };
    _rope = 0.7;
} else {
    private _cfg = configOf _body;
    private _named = getText (_cfg >> "acmeDragPoint");
    (0 boundingBoxReal _body) params ["_min", "_max"];
    private _mid = (_min vectorAdd _max) vectorMultiply 0.5;
    if (_named != "" && {(_body selectionPosition [_named, "Memory"]) isNotEqualTo [0, 0, 0]}) then {
        _tow = _body selectionPosition [_named, "Memory"];
        private _far = getText (_cfg >> "acmeDragRear");
        _rear = if (_far != "") then {_body selectionPosition [_far, "Memory"]} else {(_mid vectorMultiply 2) vectorDiff _tow};
        // A SKED whose strap is taken up to the hip (fn_dragStrapAim.sqf) is pulled by its head end, and the
        // rescuer walks a strap's reach in front of that.
        if (getNumber (_cfg >> "acmeDragStrap") > 0 && {([] call acme_sked_fnc_dragStrapClass) != ""}) then {
            private _from = _body selectionPosition [getText (_cfg >> "acmeDragStrapFrom"), "Memory"];
            if (_from isNotEqualTo [0, 0, 0]) then {
                _tow = _from;
                _rope = (getNumber (_cfg >> "acmeDragStrapReach")) max 0.5;
                _strapped = true;
            };
        };
    } else {
        // The end nearest to the rescuer; a long thing is always taken by an end, never by its side.
        private _half = (_max vectorDiff _min) vectorMultiply 0.5;
        private _to = (_body worldToModel (ASLToAGL getPosASL _unit)) vectorDiff _mid;
        _half params ["_hx", "_hy"];
        _to params ["_tx", "_ty"];
        private _alongX = if (_hx > _hy * 1.5) then {true} else {
            if (_hy > _hx * 1.5) then {false} else {(abs _tx) * _hy > (abs _ty) * _hx}
        };
        private _end = if (_alongX) then {[_hx * ([1, -1] select (_tx < 0)), 0, 0]} else {[0, _hy * ([1, -1] select (_ty < 0)), 0]};
        _tow = _mid vectorAdd _end;
        _rear = _mid vectorDiff _end;
    };
    // A litter that is taken by its handles (the Talon): always by its head end, whichever end the rescuer is
    // at, and that end is lifted to his hands. A second rescuer can lift the foot end (fn_carryRearLocal.sqf).
    _lift = getNumber (_cfg >> "acmeDragLift");
    if (_lift > 0) then {
        private _handles = (getArray (_cfg >> "acmeLitterHandles")) apply {_body selectionPosition [_x, "Memory"]};
        if (count _handles == 4 && {(_handles findIf {_x isEqualTo [0, 0, 0]}) < 0}) then {
            _tow = ((_handles select 0) vectorAdd (_handles select 1)) vectorMultiply 0.5;
            _rear = ((_handles select 2) vectorAdd (_handles select 3)) vectorMultiply 0.5;
        };
        _rope = (getNumber (_cfg >> "acmeDragReach")) max 0.2;
    };
};
_tow set [2, 0];
_rear set [2, 0];
private _length = (_tow distance2D _rear) max 0.3;
private _forward = vectorNormalized (_tow vectorDiff _rear);
private _modelAngle = (_forward select 0) atan2 (_forward select 1);

// (Model centres throughout: an object hangs by its centre, and its points are measured from it.)
private _startASL = getPosWorld _body;
private _ground = [_startASL select 0, _startASL select 1, (getPosASL _unit) select 2, _body, _unit, ((_unit distance2D _body) max 0.5) min 3] call acme_sked_fnc_dragGround;
private _rise = ((_startASL select 2) - _ground) max 0 min 3;
private _dir = vectorDir _body;
_dir set [2, 0];
_dir = vectorNormalized _dir;
private _angle = (_dir select 0) atan2 (_dir select 1);
private _world = {
    params ["_point", "_origin", "_angle"];
    [(_origin select 0) + (_point select 0) * cos _angle + (_point select 1) * sin _angle,
     (_origin select 1) - (_point select 0) * sin _angle + (_point select 1) * cos _angle]
};
private _towAt = [_tow, _startASL, _angle] call _world;
private _rearAt = [_rear, _startASL, _angle] call _world;
// It comes into line as a sled this long would, whatever its own length: a long litter that took its whole
// length to come round was still turning 14 s into a straight walk (measured on a server), and while it turns
// its place is sent every frame. _rearAt is the trailing end of that short sled, not of the target.
private _axle = _length min 1.0;
_rearAt = [(_towAt select 0) + ((_rearAt select 0) - (_towAt select 0)) * _axle / _length,
    (_towAt select 1) + ((_rearAt select 1) - (_towAt select 1)) * _axle / _length];
if (_body isNotEqualTo _target) then {_target setVariable ["acme_drag_clone", _body, true];};
// A rescuer who takes a SKED by its strap pulls a load: his weapon comes down (he can raise it again).
if (_strapped && {!weaponLowered _unit} && {currentWeapon _unit != ""}) then {_unit action ["WeaponOnBack", _unit];};
// how far apart two rescuers who carry it belong: its length and a reach at either end
if (_lift > 0) then {_body setVariable ["acme_carry_span", _length + 2 * _rope, true];};

[_unit, "forceWalk", "acme_drag", true] call ace_common_fnc_statusEffect_set;
[_unit, "blockSprint", "acme_drag", true] call ace_common_fnc_statusEffect_set;
if (_unit isEqualTo (call ace_common_fnc_player)) then {["", "Let go"] call ace_interaction_fnc_showMouseHint;};
private _key = [0xF1, [false, false, false], {
    private _unit = call ace_common_fnc_player;
    if (isNil {_unit getVariable "acme_drag_state"}) exitWith {false};
    [_unit, true] call acme_sked_fnc_dragStop;
    false
}, "keydown", "", false, 0] call CBA_fnc_addKeyHandler;

// How the target hangs on the rescuer, and why there are two ways (measured in game and on a dedicated server,
// 2026-11-18).
//   following: its place on him is set every frame, worked out against where he is DRAWN. A player's own unit
//       is drawn exactly where it is simulated (0.0 mm apart at any pace), so on the rescuer's machine the target
//       is exactly where the strap puts it; and the places sent to the other machines change evenly, so there
//       it moves evenly on him as they draw him (a thing set this way: 4 mm of jitter for another player).
//       (Worked out against where he is SIMULATED it was exact for the owner of an AI rescuer too, whose drawn
//       and simulated places are centimetres apart, but then that difference went out with every place sent,
//       and other players saw the target jitter by 2 to 5 cm. Players matter more than the owner of an AI.)
//   riding: nothing is set and nothing is sent. The target rides on the rescuer as any attached thing does,
//       which is smooth on every machine and costs no traffic.
// What is set is not the target itself but a carrier (ACME_DragCarrier: static, invisible) on which the target
// is fixed once. Measured on a dedicated server: a thing with physics (a box, a litter) whose own place on a
// walking unit is set anew every frame stands still on 42 to 45 % of another player's frames and jitters by 21
// to 23 mm; a static thing set the same way, 0 % and 1 mm; a box fixed on a static carrier that is set, 3 to
// 8 % and 7 to 9 mm.
// It follows while it has to turn or catch up, and rides once it trails straight behind a steady walk, or lies
// still. The state: [riding, steady since, rescuer's direction when it began to ride, attached yet,
// his direction a frame ago, since when he walks across the target, how fast he turns (smoothed, degrees a second)].
// The last two: the angle between the target and the way he goes a frame ago, and how fast that angle changes
// (smoothed, degrees a second).
// The last two after those: how high its middle rode over the ground under its pulled end and under its trailing
// end when it began to ride (1e9: not measured yet), each as fn_dragLie.sqf would lay it.
// And last: when the casualty's animation is looked at next; how far its head end and its foot end are lifted (0 to 1).
// And: the place it was last set at on him, how often that is still to be set again, and when next.
private _state = [false, -1, 0, false, getDir _unit, -1, 0, 0, 999, 1e9, 1e9, 0, 0, 0, 0, 0, [[0, 0, 0], [0, 1, 0], [0, 0, 1]], 0, 0, 0];
private _carrier = createVehicle ["ACME_DragCarrier", ASLToAGL getPosASL _unit, [], 0, "CAN_COLLIDE"];
_carrier setVariable ["acme_drag_carrier", true, true];
["acme_drag_carrierMade", [_carrier]] call CBA_fnc_serverEvent;
private _pfh = [{
    params ["_args", "_handle"];
    _args params ["_unit", "_target", "_body", "_tow", "_rear", "_length", "_modelAngle", "_rope", "_rise", "_towAt", "_rearAt", "_state", "_axle", "_carrier", "_limp", "_lift", "_strapped"];
    if (isNull _unit || {!alive _unit} || {!local _unit} || {_unit getVariable ["ACE_isUnconscious", false]}
        || {!isNull objectParent _unit} || {isNull _body} || {!isNull objectParent _body}
        // he began to drag or carry something with ACE: one thing at a time
        || {_unit getVariable ["ace_dragging_isDragging", false]} || {_unit getVariable ["ace_dragging_isCarrying", false]}
        || {(_unit getVariable ["acme_drag_target", objNull]) isNotEqualTo _target}
        || {isNull _carrier}
        || {(_state select 3) && {(attachedTo _body) isNotEqualTo _carrier || {(attachedTo _carrier) isNotEqualTo _unit}}}
        // a casualty who has come round walks by himself; one who has died is let go (and can be dragged again)
        || {_body isEqualTo _target && {_body isKindOf "CAManBase"} && {!alive _body || {lifeState _body in ["HEALTHY", "INJURED"]}}}
        || {(getPosASL _unit) distance2D _towAt > 6}) exitWith {
        [_unit, true] call acme_sked_fnc_dragStop;
    };
    // A second rescuer at the foot end? Then it is carried: it lies between the two, and each is held to the
    // other's pace (fn_carryBand.sqf). It never rides then: where it lies depends on both of them.
    private _mate = if (_lift > 0) then {_body getVariable ["acme_carry_rear", objNull]} else {objNull};
    if (!isNull _mate && {!alive _mate || {!isNull objectParent _mate}}) then {_mate = objNull;};
    if (isNull _mate) then {
        [_unit] call acme_sked_fnc_carryBandEnd;
    } else {
        [_unit, _mate, _body, true] call acme_sked_fnc_carryBand;
        _state set [0, false];
        _state set [1, -1];
    };
    // he may jog with it while he holds the sprint key (fn_dragPace.sqf)
    [_unit, "acme_drag"] call acme_sked_fnc_dragPace;
    // a casualty who is dragged onto a laid out litter is put into it (fn_dragOnto.sqf), looked at four times a second
    private _loaded = false;
    if (_target isKindOf "CAManBase" && {diag_tickTime >= (_unit getVariable ["acme_drag_ontoAt", 0])}) then {
        _unit setVariable ["acme_drag_ontoAt", diag_tickTime + 0.25];
        _loaded = [_unit, _target] call acme_sked_fnc_dragOnto;
    };
    // (the drag has ended in there: nothing more to do in this frame)
    if (_loaded) exitWith {};
    private _facing = getDir _unit;
    // how fast he turns, smoothed over about a fifth of a second
    private _rate = (abs ((((_facing - (_state select 4)) mod 360) + 540) mod 360 - 180)) / (diag_deltaTime max 0.001);
    _state set [4, _facing];
    private _turning = (_state select 6) + ((_rate min 720) - (_state select 6)) * ((diag_deltaTime * 5) min 1);
    _state set [6, _turning];
    private _velocity = velocity _unit;
    private _speed = sqrt ((_velocity select 0) ^ 2 + (_velocity select 1) ^ 2);
    // The strap of a SKED, up to his hip (fn_dragStrapAim.sqf): eight times a second.
    if (_strapped && {diag_tickTime > (_state select 15)}) then {
        _state set [15, diag_tickTime + 0.12];
        [_unit, _body] call acme_sked_fnc_dragStrapAim;
    };
    // The limbs of a dragged casualty: loose while he is moved, still while the rescuer stands. Looked at four
    // times a second and changed only when it has to be (one message), also when ACE or the engine took the
    // pose away.
    if (_limp && {diag_tickTime > (_state select 12)} && {!((_body getVariable ["ACME_hpmk_state", ""]) in ["wrapped", "exposed"])}) then {
        _state set [12, diag_tickTime + 0.25];
        private _wanted = ["acme_drag_rest", "acme_drag_limp"] select (_speed > 0.4);
        if ((toLowerANSI animationState _body) isNotEqualTo _wanted) then {
            [_body, _wanted, 2] call ace_common_fnc_doAnimation;
        };
    };

    if (_state select 0 && {_rate > 300}) then {
        // He turned sharply in this very frame (a flick of the mouse: measured, a quarter turn in one frame threw
        // a riding SKED 3.9 m sideways). Riding, it has swung round with him; it follows again at once, from
        // where it was a frame ago (the strap's ends still hold that place), so it is seen not to have swung.
        _state set [0, false];
        _state set [1, -1];
        _state set [5, -1];
    };
    if (_state select 0) then {
        // riding: is there a reason to follow again? The rescuer turned, or he no longer walks along the target.
        private _towNow = _body modelToWorldVisualWorld _tow;
        private _rearNow = _body modelToWorldVisualWorld _rear;
        private _ax = (_towNow select 0) - (_rearNow select 0);
        private _ay = (_towNow select 1) - (_rearNow select 1);
        private _al = sqrt (_ax * _ax + _ay * _ay) max 0.001;
        private _across = if (_speed > 0.4) then {acos ((((_ax * (_velocity select 0)) + (_ay * (_velocity select 1))) / (_al * _speed)) max -1 min 1)} else {0};
        // He may turn while it rides: a thing fixed behind a walking man swings round with him in a curve, and
        // that is smooth on every machine. It follows again only when he turns sharply or walks across it.
        // (Measured on a server: a walking unit's direction wanders all the time and it walks in arcs; with
        // narrow limits the target was following, and jittering for others, for most of a walk.)
        // Where a trailing thing lies in a steady curve: behind the way he goes by about his rate of turn times
        // the time he takes to walk the strap and the short sled (measured on a server: 30 to 40 degrees at 20
        // to 27 degrees a second). Standing, it must not be swept round him.
        private _wrong = if (_speed > 0.4) then {
            abs (_across - (((_turning * (_rope + _axle)) / _speed) min 60)) > 15
        } else {
            _turning > 20
        };
        if (_wrong) then {
            if ((_state select 5) < 0) then {_state set [5, diag_tickTime];};
        } else {
            _state set [5, -1];
        };
        // Riding keeps its place on him, and that is right only while the ground is even: on a change of slope,
        // a step or a kerb it would float or sink. So how it would lie now is worked out every frame, and it
        // follows again as soon as either end would lie 4 cm from where it rides.
        private _middle = (getPosWorldVisual _body) select 2;
        ([_towNow, _rearNow, getPosASL _unit, _body, _unit, [0, 0.3] select (_body isKindOf "CAManBase")] call acme_sked_fnc_dragLie) params ["_lieFront", "_lieRear", "_lieSide"];
        private _overFront = _middle - _lieFront;
        private _overRear = _middle - _lieRear;
        if ((_state select 9) > 1e8) then {
            _state set [9, _overFront];
            _state set [10, _overRear];
            _state set [11, _lieSide];
        };
        private _uneven = abs (_overFront - (_state select 9)) > 0.04 || {abs (_overRear - (_state select 10)) > 0.04} || {abs (_lieSide - (_state select 11)) > 0.07};
        _unit setVariable ["acme_drag_dbg", ["riding", _turning, _across, _speed, _uneven]];
        // The strap's ends are kept where the target is, so following goes on from there, and so the check
        // that the rescuer has not been taken away from his target holds while he walks.
        _towAt set [0, _towNow select 0];
        _towAt set [1, _towNow select 1];
        _rearAt set [0, (_towNow select 0) - _ax / _al * _axle];
        _rearAt set [1, (_towNow select 1) - _ay / _al * _axle];
        if (_uneven || {_turning > 70} || {(_state select 5) >= 0 && {diag_tickTime - (_state select 5) > 0.3}}) then {
            _state set [5, -1];
            _state set [0, false];
            _state set [1, -1];
        };
    };
    if (_state select 0) exitWith {
        // The place it rides at is set again three times in its first two seconds of riding: the last places
        // set before it began to ride do not reliably reach the other machines (seen on a dedicated server: a
        // Talon whose head end had been lifted was still level there three seconds later).
        if ((_state select 17) > 0 && {diag_tickTime > (_state select 18)}) then {
            (_state select 16) params ["_place", "_placeDir", "_placeUp"];
            _carrier attachTo [_unit, _place];
            _carrier setVectorDirAndUp [_placeDir, _placeUp];
            // How it is turned goes out as an event too, kept for players who join later: the engine does not
            // reliably tell the other machines how a thing that hangs on something is turned.
            if ((_state select 17) == 3) then {
                private _jip = ["acme_drag_pose", [_carrier, _placeDir, _placeUp], "acme_drag_pose_" + netId _carrier] call CBA_fnc_globalEventJIP;
                [_jip, _carrier] call CBA_fnc_removeGlobalEventJIP;
            };
            _state set [17, (_state select 17) - 1];
            _state set [18, diag_tickTime + 0.7];
        };
    };

    private _hand = getPosASLVisual _unit;
    private _gap = _hand distance2D _towAt;
    private _hx = (_towAt select 0) - (_rearAt select 0);
    private _hy = (_towAt select 1) - (_rearAt select 1);
    private _h = sqrt (_hx * _hx + _hy * _hy);
    if (_h < 0.001) exitWith {};
    _hx = _hx / _h;
    _hy = _hy / _h;
    private _taut = false;
    if (_gap > _rope) then {
        private _dx = ((_hand select 0) - (_towAt select 0)) / _gap;
        private _dy = ((_hand select 1) - (_towAt select 1)) / _gap;
        // Pulled straight back along itself (the rescuer walked past it, end over end): a strap cannot push, and
        // on that exact line it would never turn by itself. It is eased off the line, at 110 degrees a second;
        // from there the pull turns it the rest of the way as it would a sled.
        if (_hx * _dx + _hy * _dy < -0.8) then {
            private _cross = _hx * _dy - _hy * _dx;
            private _turn = (110 * diag_deltaTime) * ([1, -1] select (_cross < 0));
            private _nx = _hx * cos _turn - _hy * sin _turn;
            private _ny = _hx * sin _turn + _hy * cos _turn;
            _hx = _nx;
            _hy = _ny;
        } else {
            // (caught up at no more than 6 m/s, so nothing jumps after a swing)
            private _pull = _gap - _rope;
            // taut: it is being pulled and keeps up (one frame of walking is up to 5 cm at 30 frames a second)
            _taut = _pull < 0.12;
            _pull = _pull min (6 * diag_deltaTime);
            _towAt set [0, (_towAt select 0) + _dx * _pull];
            _towAt set [1, (_towAt select 1) + _dy * _pull];
            _hx = (_towAt select 0) - (_rearAt select 0);
            _hy = (_towAt select 1) - (_rearAt select 1);
            _h = sqrt (_hx * _hx + _hy * _hy);
            if (_h > 0.001) then {
                _hx = _hx / _h;
                _hy = _hy / _h;
            };
        };
    };
    if (!isNull _mate) then {
        // carried by two: it points from the second rescuer to its head end
        private _m = getPosASLVisual _mate;
        private _mx = (_towAt select 0) - (_m select 0);
        private _my = (_towAt select 1) - (_m select 1);
        private _ml = sqrt (_mx * _mx + _my * _my);
        if (_ml > 0.5) then {
            _hx = _mx / _ml;
            _hy = _my / _ml;
        };
    };
    _rearAt set [0, (_towAt select 0) - _hx * _axle];
    _rearAt set [1, (_towAt select 1) - _hy * _axle];
    // where the target's own trailing end is
    private _endAt = [(_towAt select 0) - _hx * _length, (_towAt select 1) - _hy * _length];
    // The target's own axes turned so that its pulled end leads.
    private _angle = (_hx atan2 _hy) - _modelAngle;
    private _ox = (_towAt select 0) - ((_tow select 0) * cos _angle + (_tow select 1) * sin _angle);
    private _oy = (_towAt select 1) + (_tow select 0) * sin _angle - (_tow select 1) * cos _angle;
    // It lies as a board does on what is under it (fn_dragLie.sqf).
    ([_towAt, _endAt, _hand, _body, _unit, [0, 0.3] select (_body isKindOf "CAManBase")] call acme_sked_fnc_dragLie) params ["_zFront", "_zRear", "_side"];
    if (_lift > 0) then {
        // its head end is in the rescuer's hands; its foot end on the ground, or in the second rescuer's hands
        // (lifted and lowered over half a second)
        private _step = diag_deltaTime / 0.5;
        _state set [13, ((_state select 13) + _step) min 1];
        _state set [14, if (isNull _mate) then {((_state select 14) - _step) max 0} else {((_state select 14) + _step) min 1}];
        private _held = (_hand select 2) + _lift;
        _zFront = _zFront + (_held - _zFront) * (_state select 13);
        private _heldRear = if (isNull _mate) then {_held} else {((getPosASLVisual _mate) select 2) + _lift};
        _zRear = _zRear + (_heldRear - _zRear) * (_state select 14);
        _side = 0;
    };
    // how far along the line from the trailing end to the pulled end the origin lies
    private _t = (((_ox - (_endAt select 0)) * _hx + (_oy - (_endAt select 1)) * _hy) / _length) max 0 min 1;
    private _along = vectorNormalized [_hx * _length, _hy * _length, _zFront - _zRear];
    private _up = (vectorNormalized [_hy, -_hx, _side]) vectorCrossProduct _along;
    private _flat = [sin _angle, cos _angle, 0];
    private _dir = vectorNormalized (_flat vectorDiff (_up vectorMultiply (_flat vectorDotProduct _up)));
    private _want = [_ox, _oy, _zRear + (_zFront - _zRear) * _t + _rise];
    private _place = _unit worldToModelVisual (ASLToAGL _want);
    private _placeDir = _unit vectorWorldToModelVisual _dir;
    private _placeUp = _unit vectorWorldToModelVisual _up;
    _carrier attachTo [_unit, _place];
    _carrier setVectorDirAndUp [_placeDir, _placeUp];
    _state set [16, [_place, _placeDir, _placeUp]];
    // (while he stands, how it is turned does not reach the other machines by itself: five times a second; a
    // litter whose ends are lifted and lowered, always)
    if ((_speed < 0.4 || {_lift > 0}) && {diag_tickTime > (_state select 19)}) then {
        _state set [19, diag_tickTime + 0.2];
        ["acme_drag_pose", [_carrier, _placeDir, _placeUp]] call CBA_fnc_remoteEvent;
    };
    if !(_state select 3) then {
        // once: the target on the carrier, centre on centre, facing as the carrier faces
        _body attachTo [_carrier, [0, 0, 0]];
        _body setVectorDirAndUp [[0, 1, 0], [0, 0, 1]];
    };
    _state set [3, true];
    // Is it still coming round? The angle between the target and the way he goes, and how fast it changes
    // (measured against the way he goes, not the way he faces: a walking unit's facing wanders).
    private _lie = if (_speed > 0.4) then {
        (((_velocity select 0) * _hy) - ((_velocity select 1) * _hx)) atan2 (((_velocity select 0) * _hx) + ((_velocity select 1) * _hy))
    } else {_state select 7};
    private _swing = (_state select 8) + (((((((_lie - (_state select 7)) mod 360) + 540) mod 360) - 180) / (diag_deltaTime max 0.001)) - (_state select 8)) * ((diag_deltaTime * 5) min 1);
    _state set [7, _lie];
    _state set [8, _swing];
    _unit setVariable ["acme_drag_want", _want];
    _unit setVariable ["acme_drag_sends", (_unit getVariable ["acme_drag_sends", 0]) + 1];   // for the tests

    // Steady? Walking with the strap taut and the target behind the way he goes, or standing still; and not
    // turning (a rate: a walking unit's direction wanders, so it is not held to one direction).
    private _steady = isNull _mate && {_lift <= 0 || {(_state select 13) >= 1 && {(_state select 14) <= 0}}} && {_turning < 60} && {if (_speed > 0.4) then {_taut && {abs _swing < 8}} else {_speed < 0.05 && {_turning < 15}}};
    _unit setVariable ["acme_drag_dbg", ["following", _turning, abs _swing, _speed, _taut, _lie]];
    if (_steady) then {
        if ((_state select 1) < 0) then {_state set [1, diag_tickTime];};
        if (diag_tickTime - (_state select 1) > 0.25) then {
            _state set [0, true];
            _state set [2, _facing];
            _state set [5, -1];
            _state set [9, 1e9];
            _state set [10, 1e9];
            _state set [17, 3];
            _state set [18, diag_tickTime + 0.3];
        };
    } else {
        _state set [1, -1];
    };
}, 0, [_unit, _target, _body, _tow, _rear, _length, _modelAngle, _rope, _rise, _towAt, _rearAt, _state, _axle, _carrier, _limp, _lift, _strapped]] call CBA_fnc_addPerFrameHandler;

_unit setVariable ["acme_drag_state", [_target, _body, _pfh, _key, _carrier, [_tow, _rear, _rise, _length, _lift]]];
["acme_drag_started", [_unit, _target]] call CBA_fnc_localEvent;
