/* Move the native lid and its fitted paint on the server before exposing Gear. */
params ["_chest", "_cabinet", "_lid", "_lidPaint", "_drawerPlan", "_cargo", "_actor", "_revision"];

private _endPos = getPosWorld _lid;
private _endDir = vectorDir _lid;
private _endUp = vectorUp _lid;
private _startDir = vectorDir _chest;
private _startUp = vectorUp _chest;
private _chestFront = (0 boundingBoxReal _chest) select 1 select 1;
private _lidFront = (0 boundingBoxReal _lid) select 1 select 1;
private _startPos = _chest modelToWorldWorld [0, _chestFront - _lidFront, 0];
private _liftedPos = _startPos vectorAdd (_startDir vectorMultiply 0.24) vectorAdd [0, 0, 0.07];
private _hoverPos = +_endPos;
_hoverPos set [2, ((_liftedPos select 2) max (_endPos select 2)) + 0.08];

private _lidParts = [_lid] + _lidPaint;
private _pose = {
    params ["_parts", "_position", "_dir", "_up"];
    {
        if (!isNull _x) then {
            _x setVectorDirAndUp [_dir, _up];
            _x setPosWorld _position;
        };
    } forEach _parts;
};
[_lidParts, _startPos, _startDir, _startUp] call _pose;

[{
    params ["_args", "_handle"];
    _args params ["_chest", "_cabinet", "_lid", "_lidParts", "_drawerPlan", "_cargo", "_actor", "_revision",
        "_startPos", "_liftedPos", "_hoverPos", "_endPos", "_startDir", "_startUp", "_endDir", "_endUp", "_pose", "_started"];
    if (isNull _chest || {(_chest getVariable ["ACME_medicalChestState", []]) isNotEqualTo [_revision, false]}) exitWith {
        [_handle] call CBA_fnc_removePerFrameHandler;
    };
    if (isNull _cabinet || {isNull _lid}) exitWith {
        [_handle] call CBA_fnc_removePerFrameHandler;
        diag_log "[ACME] Medical chest opening interrupted by a missing cabinet or lid";
        [_chest, false, _revision, true] call ACME_fnc_medicalChestSetOpen;
    };

    private _elapsed = CBA_missionTime - _started;
    private _smooth = {
        params ["_fraction"];
        _fraction = _fraction max 0 min 1;
        _fraction * _fraction * (3 - 2 * _fraction)
    };
    if (_elapsed < 0.12) exitWith {
        private _s = [_elapsed / 0.12] call _smooth;
        [_lidParts, _startPos vectorAdd ((_liftedPos vectorDiff _startPos) vectorMultiply _s), _startDir, _startUp] call _pose;
    };
    if (_elapsed < 0.32) exitWith {
        private _s = [(_elapsed - 0.12) / 0.20] call _smooth;
        private _pos = _liftedPos vectorAdd ((_hoverPos vectorDiff _liftedPos) vectorMultiply _s);
        _pos = _pos vectorAdd (_startDir vectorMultiply (0.16 * sin (180 * _s)));
        private _dir = vectorNormalized (_startDir vectorAdd ((_endDir vectorDiff _startDir) vectorMultiply _s));
        private _up = _startUp vectorAdd ((_endUp vectorDiff _startUp) vectorMultiply _s);
        _up = vectorNormalized (_up vectorDiff (_dir vectorMultiply (_up vectorDotProduct _dir)));
        [_lidParts, _pos, _dir, _up] call _pose;
    };

    // The lid is now clear of the cabinet. Slide the drawers as it settles.
    private _finished = _elapsed >= 0.56;
    private _s = if (_finished) then {1} else {[(_elapsed - 0.32) / 0.24] call _smooth};
    private _pos = if (_finished) then {_endPos} else {_hoverPos vectorAdd ((_endPos vectorDiff _hoverPos) vectorMultiply _s)};
    [_lidParts, _pos, _endDir, _endUp] call _pose;
    [_cabinet, _drawerPlan, _s] call ACME_fnc_medicalChestDrawers;
    if (_finished) then {
        [_handle] call CBA_fnc_removePerFrameHandler;
        private _openedRevision = _revision + 1;
        _chest setVariable ["ACME_medicalChestState", [_openedRevision, true], true];
        _chest setVariable ["ACME_medicalChestOpening", false];
        diag_log format ["[ACME] Medical chest opened: %1 in %2 seconds", typeOf _cabinet, _elapsed toFixed 2];
        if (!isNull _actor && {!isNull _cargo}) then {
            ["ACME_medicalChestOpened", [_actor, _chest, _cargo, _openedRevision], _actor] call CBA_fnc_targetEvent;
        };
    };
}, 0.03, [_chest, _cabinet, _lid, _lidParts, _drawerPlan, _cargo, _actor, _revision,
    _startPos, _liftedPos, _hoverPos, _endPos, _startDir, _startUp, _endDir, _endUp, _pose, CBA_missionTime]] call CBA_fnc_addPerFrameHandler;
