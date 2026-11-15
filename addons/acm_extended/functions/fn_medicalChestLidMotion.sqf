/* The lid travels through the same clearance positions in both directions. */
params ["_chest", "_cabinet", "_lid", "_lidPaint", "_cargo", "_actor", "_revision", "_opening", "_seatPose", "_restPose"];

_seatPose params ["_seated", "_caseDir", "_caseUp"];
_restPose params ["_restPos", "_restDir", "_restUp"];
private _released = _seated vectorAdd (_caseDir vectorMultiply 0.051);
private _side = _caseUp vectorMultiply -1;
private _clear = _released vectorAdd (_side vectorMultiply ((_restPos vectorDiff _released) vectorDotProduct _side));

// Raise the upright lid over the support along the sideways path, including on steps and slopes.
(0 boundingBoxReal _lid) params ["_lidMin", "_lidMax"];
private _carryHeight = _clear select 2;
private _halfSize = _lidMin apply {abs _x};
{_halfSize set [_forEachIndex, _x max (_halfSize select _forEachIndex)];} forEach _lidMax;
{
    ([_x, [_cabinet, _lid], 0.55, 1.1, false, true] call ACME_fnc_medicalChestGround) params ["_floor", "_normal"];
    private _slopeRise = (
        abs (_normal vectorDotProduct _caseDir) * (_halfSize select 1) +
        abs (_normal vectorDotProduct _caseUp) * (_halfSize select 2)
    ) / ((_normal select 2) max 0.5);
    private _minZ = (_floor select 2) + (_halfSize select 0) + _slopeRise + 0.025;
    _carryHeight = _carryHeight max _minZ;
} forEach [_released, _clear];

private _hover = +_restPos;
_hover set [2, _carryHeight max ((_restPos select 2) + vectorMagnitude _halfSize + 0.025)];
_clear set [2, _hover select 2];

private _parts = [_lid] + _lidPaint;
private _apply = {
    params ["_parts", "_position", "_dir", "_up"];
    {
        if (!isNull _x) then {
            _x setVectorDirAndUp [_dir, _up];
            _x setPosWorld _position;
        };
    } forEach _parts;
};

[{
    params ["_args", "_handle"];
    _args params ["_chest", "_cabinet", "_lid", "_parts", "_cargo", "_actor", "_revision", "_opening",
        "_seated", "_released", "_clear", "_hover", "_restPos", "_caseDir", "_caseUp", "_restDir", "_restUp", "_apply", "_started"];
    if (isNull _chest || {(_chest getVariable ["ACME_medicalChestState", []]) isNotEqualTo [_revision, !_opening]}) exitWith {
        [_handle] call CBA_fnc_removePerFrameHandler;
    };
    if (isNull _cabinet || {isNull _lid}) exitWith {
        [_handle] call CBA_fnc_removePerFrameHandler;
        diag_log "[ACME] Medical chest lid motion interrupted by a missing cabinet or lid";
        [_chest, false, _revision, true] call ACME_fnc_medicalChestSetOpen;
    };
    // A closing chest waits at the resting pose until every drawer is flush.
    if (!_opening && {(_chest getVariable ["ACME_medicalChestDrawerFraction", 0]) > 0}) exitWith {
        _args set [18, CBA_missionTime];
    };

    private _elapsed = CBA_missionTime - _started;
    private _pullEnd = 0.19;
    private _slideDuration = 0.46;
    private _turnDuration = 0.18;
    private _settleDuration = 0.28;
    private _slideEnd = _pullEnd + _slideDuration;
    private _turnEnd = _slideEnd + _turnDuration;
    private _duration = _turnEnd + _settleDuration;
    private _finished = _elapsed >= _duration;
    private _t = if (_opening) then {_elapsed min _duration} else {(_duration - _elapsed) max 0};
    private _ease = {
        params ["_fraction", ["_sharp", false]];
        _fraction = _fraction max 0 min 1;
        private _square = _fraction * _fraction;
        if (_sharp) exitWith {
            // Quintic smoothstep concentrates the speed through the middle of the motion.
            _square * _fraction * (10 + _fraction * (6 * _fraction - 15))
        };
        _square * (3 - 2 * _fraction)
    };
    private _lerp = {
        params ["_from", "_to", "_s"];
        _from vectorAdd ((_to vectorDiff _from) vectorMultiply _s)
    };
    private _dir = _caseDir;
    private _up = _caseUp;
    private _pos = if (_t < _pullEnd) then {
        [_seated, _released, [_t / _pullEnd] call _ease] call _lerp
    } else {
        if (_t < _slideEnd) then {
            private _progress = (_t - _pullEnd) / _slideDuration;
            private _carry = [_released, _clear, [_progress] call _ease] call _lerp;
            // Pick up the lid early in the carry so its lower edge can clear raised ground.
            private _lift = [_progress / 0.6] call _ease;
            _carry set [2, (_released select 2) + ((_clear select 2) - (_released select 2)) * _lift];
            _carry
        } else {
            if (_t < _turnEnd) then {
                private _s = [(_t - _slideEnd) / _turnDuration, true] call _ease;
                _dir = vectorNormalized ([_caseDir, _restDir, _s] call _lerp);
                _up = [_caseUp, _restUp, _s] call _lerp;
                _up = vectorNormalized (_up vectorDiff (_dir vectorMultiply (_up vectorDotProduct _dir)));
                [_clear, _hover, _s] call _lerp
            } else {
                _dir = _restDir;
                _up = _restUp;
                [_hover, _restPos, [(_t - _turnEnd) / _settleDuration] call _ease] call _lerp
            }
        }
    };

    if (!_finished) exitWith {[_parts, _pos, _dir, _up] call _apply;};
    [_handle] call CBA_fnc_removePerFrameHandler;
    if (_opening) then {
        [_parts, _restPos, _restDir, _restUp] call _apply;
        private _openedRevision = _revision + 1;
        _chest setVariable ["ACME_medicalChestState", [_openedRevision, true], true];
        _chest setVariable ["ACME_medicalChestTransition", false, true];
        diag_log format ["[ACME] Medical chest opened: %1 in %2 seconds", typeOf _cabinet, _elapsed toFixed 2];
        if (!isNull _actor && {!isNull _cargo}) then {
            ["ACME_medicalChestOpened", [_actor, _chest, _cargo, _openedRevision], _actor] call CBA_fnc_targetEvent;
        };
    } else {
        [_parts, _seated, _caseDir, _caseUp] call _apply;
        diag_log format ["[ACME] Medical chest closed: %1 in %2 seconds", typeOf _cabinet, _elapsed toFixed 2];
        [_chest, false, _revision, true] call ACME_fnc_medicalChestSetOpen;
    };
}, [0, 0.03] select isMultiplayer, [_chest, _cabinet, _lid, _parts, _cargo, _actor, _revision, _opening,
    _seated, _released, _clear, _hover, _restPos, _caseDir, _caseUp, _restDir, _restUp, _apply, CBA_missionTime]] call CBA_fnc_addPerFrameHandler;
