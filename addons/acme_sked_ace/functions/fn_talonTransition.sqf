/* Run the authored assembly steps under server ownership and keep an empty litter recoverable. */
params ["_actor", "_target", "_folding"];
if (!isServer || {isNull _target} || {_target getVariable ["acme_talon_busy", false]}) exitWith {};
_target setVariable ["acme_talon_busy", true, true];
[_target, false, nil, nil, false, true] call ace_dragging_fnc_setCarryable;
[_actor, _target, _folding] spawn {
    params ["_actor", "_original", "_folding"];
    private _litter = _original;
    private _restore = {
        params ["_object"];
        if (isNull _object) exitWith {};
        _object setVariable ["acme_talon_busy", false, true];
        private _cfg = configOf _object;
        [_object, true, getArray (_cfg >> "ace_dragging_carryPosition"),
            getNumber (_cfg >> "ace_dragging_carryDirection"), false, true] call ace_dragging_fnc_setCarryable;
    };
    if (_folding && {!local _litter}) then {
        _litter setOwner 2;
        private _deadline = diag_tickTime + 1.5;
        waitUntil {sleep .05; isNull _litter || {local _litter} || {diag_tickTime >= _deadline}};
    };
    if (isNull _original || {!isNull attachedTo _original} || {_folding && {!local _litter}}) exitWith {
        [_original] call _restore;
    };
    private _originalPosition = getPosWorld _original;
    if (!_folding) then {
        _litter = createVehicle ["ACME_Talon_Open", [0, 0, 1000], [], 0, "CAN_COLLIDE"];
        if (!isNull _litter) then {
            _litter setVariable ["acme_talon_busy", true, true];
            [_litter, false, nil, nil, false, true] call ace_dragging_fnc_setCarryable;
            _litter animateSource ["fold", 1, true];
            _litter animateSource ["handles", 1, true];
            _litter setVectorDirAndUp [vectorDir _original, vectorUp _original];
            _original hideObjectGlobal true;
            _original enableSimulationGlobal false;
            _original setPosWorld (_originalPosition vectorAdd [0, 0, -12]);
            _litter setPosWorld _originalPosition;
        };
    };
    if (isNull _litter) exitWith {[_original] call _restore;};
    private _mode = ["unfold", "fold"] select _folding;
    private _success = true;
    {
        _x params ["_source", "_phase", "_seconds", "_pause"];
        private _difference = abs ((_litter animationSourcePhase _source) - _phase);
        if (_difference > .001) then {
            private _period = [12, 4] select (_source == "handles");
            _litter animateSource [_source, _phase, _difference * _period / _seconds];
            private _deadline = diag_tickTime + _seconds + 1.5;
            waitUntil {
                sleep .05;
                isNull _litter || {!local _litter} || {!isNull attachedTo _litter}
                    || {abs ((_litter animationSourcePhase _source) - _phase) < .002} || {diag_tickTime >= _deadline}
            };
        };
        if (isNull _litter || {!local _litter} || {!isNull attachedTo _litter}
            || {abs ((_litter animationSourcePhase _source) - _phase) >= .002}) exitWith {_success = false;};
        sleep _pause;
    } forEach (([_mode] call acme_sked_fnc_talonSteps) select 0);
    if (_success && {_folding}) then {
        private _bundle = createVehicle ["ACME_Talon_Folded", [0, 0, 1000], [], 0, "CAN_COLLIDE"];
        if (isNull _bundle) then {_success = false;} else {
            _bundle setVectorDirAndUp [vectorDir _litter, vectorUp _litter];
            private _position = getPosWorld _litter;
            deleteVehicle _litter;
            _bundle setPosWorld _position;
            _litter = _bundle;
        };
    };
    if (!_success) exitWith {
        if (_folding && {!isNull _litter}) then {
            _litter animateSource ["fold", 0, true];
            _litter animateSource ["handles", 0, true];
        };
        if (!_folding) then {
            deleteVehicle _litter;
            _original setPosWorld _originalPosition;
            _original enableSimulationGlobal true;
            _original hideObjectGlobal false;
        };
        [_original] call _restore;
        ["Talon animation aborted", _original, _actor, [_mode]] call acme_sked_fnc_traceTransport;
    };
    if (!_folding) then {deleteVehicle _original;};
    [_litter] call _restore;
    ["Talon animation complete", _litter, _actor, [_mode]] call acme_sked_fnc_traceTransport;
};
