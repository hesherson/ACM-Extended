// A rescuer holding a SKED handle can do nothing else with ACE (the SKED self actions are exempt).
["acme_sked_notBearing", {isNull ((_this select 0) getVariable ["acme_sked_bearing", objNull])}] call ace_common_fnc_addCanInteractWithCondition;

// The server owns the litter state: who is strapped in, who holds which handle, lifted or not.
if (isServer) then {
    // The SKED is deleted (Zeus, cleanup): free the casualty and the rescuers.
    ["ACME_SKED_Wrapped", "Deleted", {
        params ["_litter"];
        [_litter, false] call acme_sked_fnc_srvRelease;
    }] call CBA_fnc_addClassEventHandler;

    // A strapped casualty is deleted (body cleanup, disconnect): the SKED goes back to laid out, empty.
    // A rescuer is deleted: they let go.
    ["CAManBase", "Deleted", {
        params ["_unit"];
        private _litter = _unit getVariable ["acme_sked_litter", objNull];
        if (!isNull _litter) then {
            _litter setVariable ["acme_sked_patient", objNull, true];
            [_litter] call acme_sked_fnc_srvUnstrap;
        };
        if (!isNull (_unit getVariable ["acme_sked_bearing", objNull])) then {[_unit] call acme_sked_fnc_srvLetGo};
    }] call CBA_fnc_addClassEventHandler;

    addMissionEventHandler ["HandleDisconnect", {
        params ["_unit"];
        if (!isNull (_unit getVariable ["acme_sked_bearing", objNull])) then {[_unit] call acme_sked_fnc_srvLetGo};
        false
    }];
};

// ACE drag of a loaded SKED (on the dragger's machine): the casualty rides with the dragger while the SKED
// is attached to them, and goes back onto the SKED when it is put down. The re-attach reads what the SKED
// is attached to when it runs, so the order of these calls does not matter.
{
    [_x, {
        params ["_unit", "_target"];
        if !(_target isKindOf "ACME_SKED_Wrapped") exitWith {};
        private _patient = _target getVariable ["acme_sked_patient", objNull];
        if (isNull _patient) exitWith {};
        ["ACE drag changed", _target, _unit, [attachedTo _target, attachedTo _patient]] call acme_sked_fnc_traceTransport;
        [_unit, "reposition", _target] call acme_sked_fnc_request;
        [{[_this select 0, "reposition", _this select 1] call acme_sked_fnc_request}, [_unit, _target], 0.8] call CBA_fnc_waitAndExecute;
    }] call CBA_fnc_addEventHandler;
} forEach ["ace_dragging_startedDrag", "ace_dragging_stoppedDrag"];

// Vehicles. A strapped casualty put into a vehicle (by "Load into vehicle" or ACE "Load Patient") goes in
// without the SKED, which is stowed with them; when they are unloaded, the SKED comes back round them.
// A rescuer holding a handle who gets into a vehicle lets go first.
["CAManBase", "GetInMan", {
    params ["_unit"];
    if (!local _unit) exitWith {};
    if (!isNull (_unit getVariable ["acme_sked_bearing", objNull])) then {[_unit, "letGo"] call acme_sked_fnc_request};
    if (isNull (_unit getVariable ["acme_sked_litter", objNull])) exitWith {};
    [_unit, "stow"] call acme_sked_fnc_request;
    // The server can see the seat change after the first request from the casualty owner.
    [{[_this, "stow"] call acme_sked_fnc_request}, _unit, 0.8] call CBA_fnc_waitAndExecute;
}] call CBA_fnc_addClassEventHandler;
["CAManBase", "GetOutMan", {
    params ["_unit"];
    if (!local _unit || {!(_unit getVariable ["acme_sked_stowed", false])}) exitWith {};
    // ACE moves the unloaded casualty to its unload position just after they leave the seat.
    [{[_this, "restore"] call acme_sked_fnc_request}, _unit, 1.5] call CBA_fnc_waitAndExecute;
}] call CBA_fnc_addClassEventHandler;

// A rescuer on a handle who is killed or knocked out lets go.
["CAManBase", "Killed", {
    params ["_unit"];
    if (local _unit && {!isNull (_unit getVariable ["acme_sked_bearing", objNull])}) then {
        [_unit, "letGo"] call acme_sked_fnc_request;
    };
}] call CBA_fnc_addClassEventHandler;
["ace_unconscious", {
    params ["_unit", "_active"];
    if (_active && {local _unit} && {!isNull (_unit getVariable ["acme_sked_bearing", objNull])}) then {
        [_unit, "letGo"] call acme_sked_fnc_request;
    };
}] call CBA_fnc_addEventHandler;

// A strapped casualty who changes owner (player leaves, AI takes over) keeps the pose guard.
["CAManBase", "Local", {
    params ["_unit", "_isLocal"];
    if (_isLocal && {!isNull (_unit getVariable ["acme_sked_litter", objNull])}) then {[_unit] call acme_sked_fnc_poseGuard};
}] call CBA_fnc_addClassEventHandler;

// Joining in progress: ACE makes every dead body draggable on this machine when it starts, which can come
// after the JIP "not draggable" for a body strapped in a SKED. Turn it off again here, locally.
if (hasInterface) then {
    [{
        {
            if (!isNull (_x getVariable ["acme_sked_litter", objNull])) then {
                [_x, false] call ace_dragging_fnc_setDraggable;
                [_x, false] call ace_dragging_fnc_setCarryable;
            };
        } forEach (allDeadMen + allUnits);
    }, [], 2] call CBA_fnc_waitAndExecute;
};

// The carry bag, slung on whoever has a SKED in their inventory: kept up to date on this machine.
if (hasInterface) then {
    [{call acme_sked_fnc_slungUpdate}, 1, []] call CBA_fnc_addPerFrameHandler;
};

if (isServer) then {diag_log "[ACME] SKED assets and ACE transport actions registered";};
