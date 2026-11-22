/* The lid travels through the same clearance positions in both directions. */
params ["_chest", "_cabinet", "_lid", "_cargo", "_actor", "_revision", "_opening", "_seatPose", "_restPose"];

_seatPose params ["_seated", "_caseDir", "_caseUp", "_outward", "_side"];
_restPose params ["_restPos", "_restDir", "_restUp", "_normal"];
private _pull = 0.11;
private _released = _seated vectorAdd (_outward vectorMultiply _pull);

// Tip over the lower edge so the lid stays just above its landing surface.
// Half-extents match the native axes of the seated and flat poses.
private _halfSize = [0.270, 0.048, 0.423];
private _heightForPose = {
    params ["_dir", "_up", "_normal", "_halfSize"];
    private _side = _dir vectorCrossProduct _up;
    (
        abs (_side vectorDotProduct _normal) * (_halfSize select 0) +
        abs (_dir vectorDotProduct _normal) * (_halfSize select 1) +
        abs (_up vectorDotProduct _normal) * (_halfSize select 2)
    ) / (_normal select 2)
};
private _hover = _restPos vectorAdd [0, 0, 0.025];
private _tipBaseZ = (_hover select 2) - ([_restDir, _restUp, _normal, _halfSize] call _heightForPose);
private _uprightZ = _tipBaseZ + ([_caseDir, _caseUp, _normal, _halfSize] call _heightForPose);
// Keep the lid at its release depth until its full width is beside the cabinet.
private _lateralDistance = (_restPos vectorDiff _released) vectorDotProduct _side;
private _clear = _released vectorAdd (_side vectorMultiply _lateralDistance);
_clear set [2, (_seated select 2) max _uprightZ];
private _extraHeight = (_clear select 2) - _uprightZ;

if (_opening) then {
    diag_log format ["[ACME] Medical chest lid path: %1 m pull along %2, then %3 m sideways; landing normal %4",
        _pull toFixed 3, _outward, (abs _lateralDistance) toFixed 3, _normal];
};

private _apply = {
    params ["_lid", "_position", "_dir", "_up"];
    _lid setVectorDirAndUp [_dir, _up];
    _lid setPosWorld _position;
};

[{
    params ["_args", "_handle"];
    _args params ["_chest", "_cabinet", "_lid", "_cargo", "_actor", "_revision", "_opening",
        "_seated", "_released", "_clear", "_hover", "_restPos", "_caseDir", "_caseUp", "_restDir", "_restUp", "_apply",
        "_normal", "_halfSize", "_tipBaseZ", "_extraHeight", "_heightForPose", "_started"];
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
        _args set [count _args - 1, CBA_missionTime];
    };

    private _elapsed = CBA_missionTime - _started;
    private _pullEnd = 0.18;
    private _slideDuration = 0.38;
    private _turnDuration = 0.25;
    private _settleDuration = 0.18;
    private _slideEnd = _pullEnd + _slideDuration;
    private _turnEnd = _slideEnd + _turnDuration;
    private _duration = _turnEnd + _settleDuration;
    // The ten latches come off one after the other before the lid moves, the last one inside two seconds; a
    // closing chest runs the same line backward, so they go on again after the lid is seated.
    private _latchTime = 1.9;
    private _latchEach = 0.5;
    private _latchStep = (_latchTime - _latchEach) / 9;
    private _whole = _latchTime + _duration;
    private _finished = _elapsed >= _whole;
    private _line = if (_opening) then {_elapsed min _whole} else {(_whole - _elapsed) max 0};
    private _t = (_line - _latchTime) max 0;
    private _latchPhases = _cabinet getVariable ["ACME_medicalChestLatchPhases", [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]];
    for "_number" from 1 to 10 do {
        private _phase = ((_line - (_number - 1) * _latchStep) / _latchEach) max 0 min 1;
        _phase = _phase * _phase * (3 - 2 * _phase);
        if (abs (_phase - (_latchPhases select (_number - 1))) > 0.002 || {_finished}) then {
            _latchPhases set [_number - 1, _phase];
            _cabinet animateSource [format ["latch_%1", _number], _phase, true];
        };
    };
    _cabinet setVariable ["ACME_medicalChestLatchPhases", _latchPhases];
    private _ease = {
        params ["_fraction"];
        _fraction = _fraction max 0 min 1;
        _fraction * _fraction * (3 - 2 * _fraction)
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
            [_released, _clear, [(_t - _pullEnd) / _slideDuration] call _ease] call _lerp
        } else {
            if (_t < _turnEnd) then {
                private _s = [(_t - _slideEnd) / _turnDuration] call _ease;
                _dir = vectorNormalized ([_caseDir, _restDir, _s] call _lerp);
                _up = [_caseUp, _restUp, _s] call _lerp;
                _up = vectorNormalized (_up vectorDiff (_dir vectorMultiply (_up vectorDotProduct _dir)));
                // Align with the landing point while tipping outside the cabinet.
                private _pos = [_clear, _restPos, _s] call _lerp;
                private _height = [_dir, _up, _normal, _halfSize] call _heightForPose;
                _pos set [2, _tipBaseZ + _height + _extraHeight * (1 - _s)];
                _pos
            } else {
                _dir = _restDir;
                _up = _restUp;
                [_hover, _restPos, [(_t - _turnEnd) / _settleDuration] call _ease] call _lerp
            }
        }
    };

    if (!_finished) exitWith {[_lid, _pos, _dir, _up] call _apply;};
    [_handle] call CBA_fnc_removePerFrameHandler;
    if (_opening) then {
        [_lid, _restPos, _restDir, _restUp] call _apply;
        private _openedRevision = _revision + 1;
        _chest setVariable ["ACME_medicalChestState", [_openedRevision, true], true];
        _chest setVariable ["ACME_medicalChestTransition", false, true];
        diag_log format ["[ACME] Medical chest opened: %1 in %2 seconds", typeOf _cabinet, _elapsed toFixed 2];
        if (!isNull _actor && {!isNull _cargo}) then {
            ["ACME_medicalChestOpened", [_actor, _chest, _cargo, _openedRevision], _actor] call CBA_fnc_targetEvent;
        };
    } else {
        [_lid, _seated, _caseDir, _caseUp] call _apply;
        diag_log format ["[ACME] Medical chest closed: %1 in %2 seconds", typeOf _cabinet, _elapsed toFixed 2];
        [_chest, false, _revision, true] call ACME_fnc_medicalChestSetOpen;
    };
}, [0, 0.03] select isMultiplayer, [_chest, _cabinet, _lid, _cargo, _actor, _revision, _opening,
    _seated, _released, _clear, _hover, _restPos, _caseDir, _caseUp, _restDir, _restUp, _apply,
    _normal, _halfSize, _tipBaseZ, _extraHeight, _heightForPose, CBA_missionTime]] call CBA_fnc_addPerFrameHandler;
