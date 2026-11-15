/* The lid travels through the same clearance positions in both directions. */
params ["_chest", "_cabinet", "_lid", "_lidPaint", "_cargo", "_actor", "_revision", "_opening", "_seatPose", "_restPose"];

_seatPose params ["_seated", "_caseDir", "_caseUp"];
_restPose params ["_restPos", "_restDir", "_restUp"];
private _side = _caseUp vectorMultiply -1;
(0 boundingBoxReal _cabinet) params ["_cabinetMin", "_cabinetMax"];
private _cabinetDir = vectorDir _cabinet;
private _cabinetUp = vectorUp _cabinet;
private _cabinetAxes = [_cabinetDir vectorCrossProduct _cabinetUp, _cabinetDir, _cabinetUp];
private _cabinetCenter = getPosWorld _cabinet vectorDiff _seated;
private _cabinetEdge = {
    params ["_direction"];
    private _edge = _cabinetCenter vectorDotProduct _direction;
    {
        private _projection = _x vectorDotProduct _direction;
        private _bound = [_cabinetMin, _cabinetMax] select (_projection >= 0);
        _edge = _edge + _projection * (_bound select _forEachIndex);
    } forEach _cabinetAxes;
    _edge
};

(0 boundingBoxReal _lid) params ["_lidMin", "_lidMax"];
private _halfSize = _lidMin apply {abs _x};
{_halfSize set [_forEachIndex, _x max (_halfSize select _forEachIndex)];} forEach _lidMax;
private _sweepRadius = vectorMagnitude _halfSize;

// Keep the lid upright until its inside face clears the front of the cabinet.
private _frontEdge = [_caseDir] call _cabinetEdge;
private _pullDistance = 0.065 max (_frontEdge - (_lidMin select 1) + 0.075);
private _released = _seated vectorAdd (_caseDir vectorMultiply _pullDistance);

// Keep the entire rotating lid outboard of the cabinet, including on uneven ground.
private _restSide = (_restPos vectorDiff _seated) vectorDotProduct _side;
private _sideEdge = [_side] call _cabinetEdge;
private _turnSide = _restSide max (_sideEdge + _sweepRadius + 0.04);
private _clear = _released vectorAdd (_side vectorMultiply _turnSide);
private _hover = _restPos vectorAdd (_side vectorMultiply (_turnSide - _restSide));

// Raise the upright lid over the support along the sideways path.
private _carryHeight = (_restPos select 2) + _sweepRadius + 0.025;
{
    ([_x, [_cabinet, _lid], 0.55, 1.1, false, true] call ACME_fnc_medicalChestGround) params ["_floor", "_normal"];
    private _slopeRise = (
        abs (_normal vectorDotProduct _caseDir) * (_halfSize select 1) +
        abs (_normal vectorDotProduct _caseUp) * (_halfSize select 2)
    ) / ((_normal select 2) max 0.5);
    private _minZ = (_floor select 2) + (_halfSize select 0) + _slopeRise + 0.025;
    _carryHeight = _carryHeight max _minZ;
} forEach [_released, _clear];
_hover set [2, _carryHeight];
_clear set [2, _carryHeight];

if (_opening) then {
    diag_log format ["[ACME] Medical chest lid path: %1 m straight pull, %2 m front clearance",
        _pullDistance toFixed 3, (_pullDistance + (_lidMin select 1) - _frontEdge) toFixed 3];
};

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
    private _pullEnd = 0.23;
    private _slideDuration = 0.46;
    private _turnDuration = 0.24;
    private _settleDuration = 0.38;
    private _slideEnd = _pullEnd + _slideDuration;
    private _turnEnd = _slideEnd + _turnDuration;
    private _duration = _turnEnd + _settleDuration;
    private _finished = _elapsed >= _duration;
    private _t = if (_opening) then {_elapsed min _duration} else {(_duration - _elapsed) max 0};
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
            private _progress = (_t - _pullEnd) / _slideDuration;
            private _carry = [_released, _clear, [_progress] call _ease] call _lerp;
            // Pick up the lid early in the carry so its lower edge can clear raised ground.
            private _lift = [_progress / 0.8] call _ease;
            _carry set [2, (_released select 2) + ((_clear select 2) - (_released select 2)) * _lift];
            _carry
        } else {
            if (_t < _turnEnd) then {
                private _s = [(_t - _slideEnd) / _turnDuration] call _ease;
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
