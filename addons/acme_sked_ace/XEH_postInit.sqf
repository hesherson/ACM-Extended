// (Until B377 a condition of the mod's own was registered here with ACE's canInteractWith, to keep a rescuer on
// a litter handle from other ACE actions. ACE's menu key asks canInteractWith with a fixed list of exceptions,
// so that condition kept the whole ACE menu shut for him, "let go" included. A rescuer on a handle who starts an
// ACE drag or carry lets go of the handle instead: fn_bearerLocal.sqf.)

// The server owns the litter state: who is strapped in, who holds which handle, lifted or not.
if (isServer) then {
    // The server's copy of what an undressed casualty wore (fn_gearHide.sqf), by the casualty's network id.
    acme_sked_gearKept = [] call CBA_fnc_createNamespace;
    ["acme_sked_gearKeep", {
        params ["_patient", "_kept"];
        if (!isNull _patient) then {acme_sked_gearKept setVariable [netId _patient, _kept];};
    }] call CBA_fnc_addEventHandler;
    ["acme_sked_gearGone", {
        params ["_patient"];
        if (!isNull _patient) then {acme_sked_gearKept setVariable [netId _patient, nil];};
    }] call CBA_fnc_addEventHandler;

    // The SKED is deleted (Zeus, cleanup): free the casualty and the rescuers.
    // the straps buckled over the casualty of a Talon (fn_strapFit.sqf asks, fn_strapArcs.sqf hangs them on it)
    ["acme_sked_strapArcs", {_this call acme_sked_fnc_strapArcs}] call CBA_fnc_addEventHandler;
    ["ACME_SKED_Wrapped", "Deleted", {
        params ["_litter"];
        {deleteVehicle _x} forEach (_litter getVariable ["acme_strap_arcs", []]);
        [_litter, false] call acme_sked_fnc_srvRelease;
    }] call CBA_fnc_addClassEventHandler;
    // (a laid out litter that was deleted while a casualty was being strapped in)
    ["ACME_SKED_Open", "Deleted", {
        params ["_litter"];
        {deleteVehicle _x} forEach (_litter getVariable ["acme_strap_arcs", []]);
        // an HPMK laid out ready on it (fn_stageHpmk.sqf) that was not used: the kit stays behind on the ground
        deleteVehicle (_litter getVariable ["acme_sked_hpmkSheet", objNull]);
        if (isServer && {_litter getVariable ["acme_sked_hpmkStaged", false]}) then {
            private _holder = createVehicle ["GroundWeaponHolder", getPosATL _litter, [], 0, "CAN_COLLIDE"];
            _holder addItemCargoGlobal ["ACME_HPMK", 1];
        };
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

// ACME drag (fn_dragLocal.sqf): anything with physics, and any casualty. The litters and people have the action
// in their config; every other thing gets it here, on a point of its own in its middle.
// How a dragged thing's carrier is turned on its rescuer (fn_dragLocal.sqf sends it): every machine turns it
// itself, because the engine does not reliably pass that on for a thing that hangs on something.
["acme_drag_pose", {
    params ["_carrier", "_dir", "_up"];
    if (!isNull _carrier && {!local _carrier}) then {_carrier setVectorDirAndUp [_dir, _up];};
}] call CBA_fnc_addEventHandler;
// A dragged thing is set down where it is local (fn_dragStop.sqf asks): only there can it be turned.
["acme_drag_setDown", {
    params ["_body", "_at", "_dir", "_up"];
    if (isNull _body || {!isNull attachedTo _body} || {!isNull objectParent _body}) exitWith {};
    _body setPosWorld _at;
    _body setVectorDirAndUp [_dir, _up];
    _body setVelocity [0, 0, 0];
}] call CBA_fnc_addEventHandler;
// How a thing that hangs on another is turned is set where it is local (a litter in a helicopter).
["acme_sked_turnAttached", {
    params ["_thing", "_dir", "_up"];
    if (!isNull _thing && {!isNull attachedTo _thing}) then {_thing setVectorDirAndUp [_dir, _up];};
}] call CBA_fnc_addEventHandler;
if (isServer) then {
    // Litters that lie in vehicles (fn_srvVehicleLitter.sqf): when a vehicle is lost, its litters come out
    // where they are.
    acme_sked_vehicleLitters = [];
    [{
        {
            if (isNull _x) then {
                acme_sked_vehicleLitters = acme_sked_vehicleLitters - [_x];
            } else {
                private _vehicle = _x getVariable ["acme_sked_inVehicle", objNull];
                if (isNull _vehicle || {!alive _vehicle}) then {[objNull, _x, _vehicle, false] call acme_sked_fnc_srvVehicleLitter;};
            };
        } forEach +acme_sked_vehicleLitters;
    }, 2] call CBA_fnc_addPerFrameHandler;
};
if (hasInterface) then {
    // On the vehicle itself: take a litter out that lies on its cabin floor.
    {
        if (isClass (configFile >> "CfgVehicles" >> _x)) then {
            private _out = ["acme_sked_litterOut", "Unload litter", "\acme_sked\data\ui\icon_sked_ca.paa", {
                private _litter = ((_target getVariable ["acme_sked_litters", []]) select {!isNull _x}) param [0, objNull];
                if (!isNull _litter) then {[_player, _litter, _target, false] call acme_sked_fnc_vehicleLitter;};
            }, {((_target getVariable ["acme_sked_litters", []]) findIf {!isNull _x}) >= 0 && {isNull objectParent _player}}] call ace_interact_menu_fnc_createAction;
            [_x, 0, ["ACE_MainActions"], _out, true] call ace_interact_menu_fnc_addActionToClass;
        };
    } forEach (missionNamespace getVariable ["acme_sked_vehicleLitterKinds", ["vtx_H60_base"]]);
};
// A casualty lies the right way round on his litter on every machine (fn_orientLocal.sqf).
[{call acme_sked_fnc_orientLocal}, 0.5] call CBA_fnc_addPerFrameHandler;
// (while he is being strapped in he lies on the laid out litter: fn_placeLocal.sqf sends his turn)
["acme_sked_laidTurn", {
    params ["_patient", "_litter", "_dir", "_up"];
    if (isNull _patient || {isNull _litter}) exitWith {};
    if ((attachedTo _patient) isEqualTo _litter) then {_patient setVectorDirAndUp [_dir, _up];};
    [{
        params ["_patient", "_litter", "_dir", "_up"];
        if (!isNull _patient && {!isNull _litter} && {(attachedTo _patient) isEqualTo _litter}) then {_patient setVectorDirAndUp [_dir, _up];};
    }, _this, 1] call CBA_fnc_waitAndExecute;
}] call CBA_fnc_addEventHandler;
// Casualties and occupied litters that were left on a steep slope slide down it (fn_slideLocal.sqf): on every
// machine, for what is local to it.
acme_slide_list = [];
acme_slide_scanAt = 0;
[{call acme_sked_fnc_slideLocal}, 0] call CBA_fnc_addPerFrameHandler;
if (hasInterface) then {
    // The same with ACE's own drag: a casualty the player drags onto a laid out litter is put into it.
    [{
        private _unit = call ace_common_fnc_player;
        if (_unit getVariable ["ace_dragging_isDragging", false]) then {
            [_unit, _unit getVariable ["ace_dragging_draggedObject", objNull], true] call acme_sked_fnc_dragOnto;
        };
    }, 0.25] call CBA_fnc_addPerFrameHandler;
    // Jogging with what he drags or carries (fn_dragPace.sqf) costs a man several times the effort, with ACE's
    // fatigue on.
    if (!isNil "ace_advanced_fatigue_fnc_addDutyFactor") then {
        ["acme_drag_jog", {
            [1, missionNamespace getVariable ["acme_drag_jogDuty", 3.5]] select (ACE_player getVariable ["acme_drag_jogging", false])
        }] call ace_advanced_fatigue_fnc_addDutyFactor;
    };
    // dust under what is dragged, on this machine for itself (fn_dragDustLocal.sqf)
    acme_drag_dustNear = [];
    [{call acme_sked_fnc_dragDustLocal}, 0.12] call CBA_fnc_addPerFrameHandler;
    // and its sound, on this machine for itself (fn_dragSoundLocal.sqf)
    acme_drag_soundNear = [];
    [{call acme_sked_fnc_dragSoundLocal}, 0.12] call CBA_fnc_addPerFrameHandler;
    // "Drag behind you" on things, inside each thing's own menu (fn_dragAction.sqf says why). Not on the
    // litters (their classes have the action), on things with a menu root of their own (their addons add it
    // there) and on things nobody is to take away (parts of a medical chest, hanging bags, rope ends).
    ["ThingX", 0, ["ACE_MainActions"], call acme_sked_fnc_dragAction, true,
        ["ACME_SKED_Base", "ACME_AccuvacRescue", "ACME_MedicalChestCargo", "ACME_MedicalChestLid", "ACME_MedicalChest8Drawers",
            "ACME_IVBagObject", "ACME_RopeHelper"]] call ace_interact_menu_fnc_addActionToClass;
};
if (isServer) then {
    // Every drag [rescuer, target, since when] is watched, so that nothing stays marked as dragged, and claimed,
    // when the rescuer's machine did not end it itself: it never started, it crashed, or some mod moved or
    // removed a unit in a way that raises none of the events below.
    acme_drag_active = [];
    // every carrier ever made [carrier, when]: one that hangs on nothing ten seconds on is a leftover
    acme_drag_carriers = [];
    ["acme_drag_carrierMade", {
        params ["_carrier"];
        if (!isNull _carrier) then {acme_drag_carriers pushBack [_carrier, serverTime];};
    }] call CBA_fnc_addEventHandler;
    [{
        acme_drag_carriers = acme_drag_carriers select {
            _x params ["_carrier", "_made"];
            if (isNull _carrier) then {false} else {
                if (isNull attachedTo _carrier && {serverTime - _made > 10}) then {
                    {[_x, objNull] call acme_sked_fnc_dragFree;} forEach (attachedObjects _carrier);
                    if (!isNull _carrier) then {deleteVehicle _carrier;};
                    false
                } else {true}
            }
        };
        acme_drag_active = acme_drag_active select {
            _x params ["_unit", "_target", "_since"];
            if (isNull _target) then {
                if (!isNull _unit && {isNull (_unit getVariable ["acme_drag_target", objNull])}) then {_unit setVariable ["acme_drag_target", nil, true];};
                false
            } else {
                if (isNull _unit) then {
                    // the rescuer no longer exists: free what he had
                    if (isNull (_target getVariable ["acme_drag_by", objNull])) then {
                        [_target, objNull] call acme_sked_fnc_dragFree;
                        private _clone = _target getVariable ["acme_drag_clone", objNull];
                        if (!isNull _clone) then {
                            [_clone, objNull] call acme_sked_fnc_dragFree;
                            [objNull, _clone, false] call ace_dragging_fnc_deleteClone;
                            _target setVariable ["acme_drag_clone", nil, true];
                        };
                        _target setVariable ["acme_drag_by", nil, true];
                        [objNull, _target, true] call ace_common_fnc_claim;
                        ["drag ended by the watch (rescuer gone)", _target, objNull, []] call acme_sked_fnc_traceTransport;
                    };
                    false
                } else {
                    if ((_unit getVariable ["acme_drag_target", objNull]) isNotEqualTo _target) then {
                        false       // ended in the ordinary way
                    } else {
                        private _body = _target getVariable ["acme_drag_clone", objNull];
                        if (isNull _body) then {_body = _target;};
                        // a second rescuer at its foot end who cannot go on lets go
                        private _rear = _target getVariable ["acme_carry_rear", objNull];
                        if (!isNull _rear && {!alive _rear || {_rear getVariable ["ACE_isUnconscious", false]} || {!isNull objectParent _rear}}) then {
                            [_rear] call acme_sked_fnc_carrySrvEnd;
                        };
                        // (it hangs on its carrier, and the carrier on him)
                        private _holder = attachedTo _body;
                        if (_holder getVariable ["acme_drag_carrier", false]) then {_holder = attachedTo _holder;};
                        private _over = !alive _unit || {_unit getVariable ["ACE_isUnconscious", false]} || {!isNull objectParent _unit}
                            || {serverTime - _since > 8 && {_holder isNotEqualTo _unit}};
                        if (_over) then {
                            ["drag ended by the watch", _target, _unit, []] call acme_sked_fnc_traceTransport;
                            [_unit] call acme_sked_fnc_dragSrvEnd;
                        };
                        !_over
                    }
                }
            }
        };
    }, 2] call CBA_fnc_addPerFrameHandler;
    // A rescuer who dies, goes down, gets into a vehicle or leaves lets go; a dragged thing that is deleted frees them.
    ["CAManBase", "Killed", {
        params ["_unit"];
        if (!isNull (_unit getVariable ["acme_drag_target", objNull])) then {[_unit] call acme_sked_fnc_dragSrvEnd;};
    }] call CBA_fnc_addClassEventHandler;
    ["CAManBase", "Deleted", {
        params ["_unit"];
        if (!isNull (_unit getVariable ["acme_drag_target", objNull])) then {[_unit] call acme_sked_fnc_dragSrvEnd;};
    }] call CBA_fnc_addClassEventHandler;
    addMissionEventHandler ["HandleDisconnect", {
        params ["_unit"];
        if (!isNull (_unit getVariable ["acme_drag_target", objNull])) then {[_unit] call acme_sked_fnc_dragSrvEnd;};
        false
    }];
};
["CAManBase", "GetInMan", {
    params ["_unit"];
    if (local _unit && {!isNil {_unit getVariable "acme_drag_state"}}) then {[_unit, true] call acme_sked_fnc_dragStop;};
}] call CBA_fnc_addClassEventHandler;

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
