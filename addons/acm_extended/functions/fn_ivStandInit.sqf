/* B395: IV stands hold IV bags.
 * The game's IV stands (Land_IntravenStand_01_empty_F / _1bag_F / _2bags_F, and anything built on
 * Land_IntravenStand_01_base_F) get two actions in their ACE interaction menu:
 *   "Hang IV bag"    - one entry per casualty within the line's reach (ACME_hang_leash, 3 m) whose IV bag is running:
 *                      the bag goes onto a free hook of the stand and runs with the same gravity boost as a bag held
 *                      up by hand (ACME_hang_flowMult). A provider holding that casualty's bag up hands it over.
 *   "Take down bag"  - one entry per casualty hung on this stand.
 * The server owns the stand's two hooks (fn_ivStandServer.sqf) and lowers a bag by itself when the casualty is
 * moved out of reach, dies, or the bag runs dry. Every machine draws the hung bag and its line itself
 * (fn_ivStandVisual.sqf, a JIP event per hook). Called from fn_postInit on every machine.
 * The poles can be dragged (ACE dragging, held beside the provider); a pole stands itself upright again where it is
 * put down (its weight is in the base), and the lines of its bags follow it. */
if (!isNil "ACME_ivStand_ready") exitWith {};
ACME_ivStand_ready = true;

ACME_ivStand_baseClass = "Land_IntravenStand_01_base_F";
// Where a bag hangs on each of the stand's two hooks (stand model space, whose origin is the middle of the stand,
// 0.94 m up; the game's own bags hang at y +-0.13, z 0.77), and its turn there (tubes down, as the game's bags). The stand's own
// decorative bags (animation sources Bag1_Hide / Bag2_Hide) are hidden while ACME uses that hook.
if (isNil "ACME_ivStand_hooks") then {ACME_ivStand_hooks = [[0, 0.13, 0.76], [0, -0.13, 0.76]];};
if (isNil "ACME_ivStand_bagVectors") then {ACME_ivStand_bagVectors = [[0, 1, 0], [0, 0, -1]];};
if (isNil "ACME_ivStand_bagOutlet") then {ACME_ivStand_bagOutlet = [0, 0, -0.16];};  // from the hook to the bag's port

["ACME_ivStandVisual", {_this call ACME_fnc_ivStandVisual}] call CBA_fnc_addEventHandler;
["ACME_ivStandMessage", {
    params [["_text", "", [""]]];
    if (_text != "") then {[_text, 2] call ace_common_fnc_displayTextStructured;};
}] call CBA_fnc_addEventHandler;

if (isServer) then {
    ACME_ivStand_hung = [];
    ["ACME_ivStandRequest", {["request", _this] call ACME_fnc_ivStandServer}] call CBA_fnc_addEventHandler;
    [{["watch", []] call ACME_fnc_ivStandServer}, 1] call CBA_fnc_addPerFrameHandler;
};

// dragging: every machine marks each stand draggable (ACE keeps it local); the lines on this machine follow a
// moving pole; a pole that is put down tilted (a slope, a drop) stands upright again on the machine that owns it.
["Land_IntravenStand_01_base_F", "init", {
    params ["_stand"];
    [_stand, true, [0.45, 0.75, 0], 0, true] call ace_dragging_fnc_setDraggable;
}, true, [], true] call CBA_fnc_addClassEventHandler;
["ace_dragging_stoppedDrag", {
    params ["_unit", "_target"];
    if (_target isKindOf "Land_IntravenStand_01_base_F") then {["ACME_ivStandUpright", [_target], _target] call CBA_fnc_targetEvent;};
}] call CBA_fnc_addEventHandler;
["ACME_ivStandUpright", {
    params ["_stand"];
    [{
        params ["_stand"];
        if (isNull _stand || {!isNull attachedTo _stand}) exitWith {};
        _stand setVectorUp [0, 0, 1];  // (ACE itself puts a dropped object back on the ground)
    }, [_stand], 0.3] call CBA_fnc_waitAndExecute;
}] call CBA_fnc_addEventHandler;
if (hasInterface) then {
    [{
        if (isNil "ACME_ivStand_local") exitWith {};
        {
            _y params ["_bag", "_anchor", "_helper", "_rope", "_stand", "_slot", ["_ropeClass", ""], ["_at", [0, 0, 0]]];
            if (!isNull _stand && {!isNull _anchor} && {!isNull _helper} && {(getPosASL _stand) distance _at > 0.04}) then {
                // a rope stays where it was made (an engine rope does not follow its ends): make it again
                if (!isNull _rope) then {[_rope] call ACME_fnc_ivLineDestroy;};
                _rope = [_anchor, missionNamespace getVariable ["ACME_hang_lineTipOffset", [0, 0.04, 0.06]], _helper, [0, 0, 0],
                    missionNamespace getVariable ["ACME_hang_lineLength", 3], missionNamespace getVariable ["ACME_hang_lineSagSegs", 24], _ropeClass] call ACME_fnc_ivLineCreate;
                _y set [3, _rope];
                _y set [7, getPosASL _stand];
            };
        } forEach ACME_ivStand_local;
    }, 0.25] call CBA_fnc_addPerFrameHandler;
};

if (!hasInterface) exitWith {};
private _hang = ["ACME_IVStandHang", "Hang IV bag", "", {}, {
    (missionNamespace getVariable ["ACME_sys_hang", true]) && {([_target, _player, "hang"] call ACME_fnc_ivStandCandidates) isNotEqualTo []}
}, {
    ([_target, _player, "hang"] call ACME_fnc_ivStandCandidates) apply {
        _x params ["_patient", "_label", "_id", "_part"];
        [["ACME_IVStandHang_" + _id, _label, "", {
            params ["_target", "_player", "_args"];
            [_target, _args select 0, true, _args select 1] call ACME_fnc_ivStandRequest;
        }, {true}, {}, [_patient, _part]] call ace_interact_menu_fnc_createAction, [], _target]
    }
}] call ace_interact_menu_fnc_createAction;
private _down = ["ACME_IVStandDown", "Take down bag", "", {}, {
    ([_target, _player, "down"] call ACME_fnc_ivStandCandidates) isNotEqualTo []
}, {
    ([_target, _player, "down"] call ACME_fnc_ivStandCandidates) apply {
        _x params ["_patient", "_label", "_id", "_part"];
        [["ACME_IVStandDown_" + _id, _label, "", {
            params ["_target", "_player", "_args"];
            [_target, _args select 0, false, _args select 1] call ACME_fnc_ivStandRequest;
        }, {true}, {}, [_patient, _part]] call ace_interact_menu_fnc_createAction, [], _target]
    }
}] call ace_interact_menu_fnc_createAction;
private _classes = ("configName _x isKindOf ['Land_IntravenStand_01_base_F', configFile >> 'CfgVehicles']" configClasses (configFile >> "CfgVehicles")) apply {configName _x};
{
    [_x, 0] call ace_interact_menu_fnc_addMainAction;
    [_x, 0, ["ACE_MainActions"], _hang] call ace_interact_menu_fnc_addActionToClass;
    [_x, 0, ["ACE_MainActions"], _down] call ace_interact_menu_fnc_addActionToClass;
} forEach _classes;
