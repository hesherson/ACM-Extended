/*
 * Server: fold a laid out Talon II into its bundle, or unfold a bundle, by the litter's authored animation, and
 * keep an empty litter recoverable when anything breaks it off.
 *
 * The animation is not played on the litter itself: one model has no room for the litter's 253 bones (acme_talon,
 * tools/build_talon_fold_parts.py). Four part models, one for each segment, stand in the litter's place for
 * the seconds of the sequence; the litter is hidden meanwhile. All four are driven through the same steps
 * (fn_talonSteps.sqf) at the same time.
 * Arguments: 0: who does it, 1: the litter (laid out) or the bundle, 2: fold <BOOL> (false: unfold).
 */
params ["_actor", "_target", "_folding"];
if (!isServer || {isNull _target} || {_target getVariable ["acme_talon_busy", false]}) exitWith {};
_target setVariable ["acme_talon_busy", true, true];
// ACE needs a real position and direction here: with nil and a global call it throws before it sets anything.
private _carryOff = {
    params ["_object"];
    private _cfg = configOf _object;
    private _position = getArray (_cfg >> "ace_dragging_carryPosition");
    if (count _position != 3) then {_position = [0, 1, 1];};
    [_object, false, _position, getNumber (_cfg >> "ace_dragging_carryDirection"), false, true] call ace_dragging_fnc_setCarryable;
};
[_target] call _carryOff;
[_actor, _target, _folding, _carryOff] spawn {
    params ["_actor", "_original", "_folding", "_carryOff"];
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
        // the laid out litter that will be there at the end: in place already, not shown until the parts are done
        _litter = createVehicle ["ACME_Talon_Open", [0, 0, 1000], [], 0, "CAN_COLLIDE"];
        if (!isNull _litter) then {
            _litter setVariable ["acme_talon_busy", true, true];
            [_litter] call _carryOff;
            _litter animateSource ["fold", 0, true];
            _litter animateSource ["handles", 0, true];
            _litter hideObjectGlobal true;
            _litter setVectorDirAndUp [vectorDir _original, vectorUp _original];
            _litter setPosWorld _originalPosition;
        };
    };
    if (isNull _litter) exitWith {[_original] call _restore;};
    // The four parts, in the litter's place: an axis point that no bone moves is at the same place in the
    // litter's model and in a part's, which says where a part's own middle belongs.
    private _parts = [];
    private _start = [0, 1] select !_folding;
    {
        private _part = createVehicle [_x, [0, 0, 1000], [], 0, "CAN_COLLIDE"];
        if (!isNull _part) then {
            _part animateSource ["fold", _start, true];
            _part animateSource ["handles", _start, true];
            _part attachTo [_litter, (_litter selectionPosition ["ax_body_00", "Memory"]) vectorDiff (_part selectionPosition ["ax_body_00", "Memory"])];
            _parts pushBack _part;
        };
    } forEach ["ACME_Talon_FoldPart_1", "ACME_Talon_FoldPart_2", "ACME_Talon_FoldPart_3", "ACME_Talon_FoldPart_4"];
    private _mode = ["unfold", "fold"] select _folding;
    private _success = count _parts == 4;
    if (_success) then {
        // (a moment for the parts to be there on every machine before what they replace goes)
        sleep 0.15;
        if (_folding) then {
            _litter hideObjectGlobal true;
        } else {
            _original hideObjectGlobal true;
            _original enableSimulationGlobal false;
            _original setPosWorld (_originalPosition vectorAdd [0, 0, -12]);
        };
        private _first = _parts select 0;
        {
            _x params ["_source", "_phase", "_seconds", "_pause"];
            private _difference = abs ((_first animationSourcePhase _source) - _phase);
            if (_difference > .001) then {
                private _period = [12, 4] select (_source == "handles");
                {_x animateSource [_source, _phase, _difference * _period / _seconds];} forEach _parts;
                private _deadline = diag_tickTime + _seconds + 1.5;
                waitUntil {
                    sleep .05;
                    isNull _litter || {!local _litter} || {!isNull attachedTo _litter} || {isNull _first}
                        || {abs ((_first animationSourcePhase _source) - _phase) < .002} || {diag_tickTime >= _deadline}
                };
            };
            if (isNull _litter || {!local _litter} || {!isNull attachedTo _litter} || {isNull _first}
                || {abs ((_first animationSourcePhase _source) - _phase) >= .002}) exitWith {_success = false;};
            sleep _pause;
        } forEach (([_mode] call acme_sked_fnc_talonSteps) select 0);
    };
    if (_success && {_folding}) then {
        private _bundle = createVehicle ["ACME_Talon_Folded", [0, 0, 1000], [], 0, "CAN_COLLIDE"];
        if (isNull _bundle) then {_success = false;} else {
            _bundle setVectorDirAndUp [vectorDir _litter, vectorUp _litter];
            private _position = getPosWorld _litter;
            {deleteVehicle _x} forEach _parts;
            deleteVehicle _litter;
            _bundle setPosWorld _position;
            _litter = _bundle;
        };
    };
    if (!_success) exitWith {
        {deleteVehicle _x} forEach _parts;
        if (_folding) then {
            if (!isNull _litter) then {_litter hideObjectGlobal false;};
        } else {
            deleteVehicle _litter;
            _original setPosWorld _originalPosition;
            _original enableSimulationGlobal true;
            _original hideObjectGlobal false;
        };
        [_original] call _restore;
        ["Talon animation aborted", _original, _actor, [_mode]] call acme_sked_fnc_traceTransport;
    };
    if (!_folding) then {
        // the laid out litter takes the parts' place
        _litter hideObjectGlobal false;
        {deleteVehicle _x} forEach _parts;
        deleteVehicle _original;
    };
    [_litter] call _restore;
    ["Talon animation complete", _litter, _actor, [_mode]] call acme_sked_fnc_traceTransport;
};
