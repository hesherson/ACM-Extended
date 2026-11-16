/* Requests carry the local actor, followed by the action and its objects. */
params [["_actor", objNull, [objNull]], ["_action", "", [""]], ["_target", objNull, [objNull]], ["_extra", objNull, [objNull]]];
if (isNull _actor || {!(_actor isKindOf "CAManBase")}) exitWith {};
if (!isServer) exitWith {
    if (!isRemoteExecuted && {local _actor}) then {
        [_actor, _action, _target, _extra] remoteExecCall ["acme_sked_fnc_request", 2];
    };
};
if (if (isRemoteExecuted) then {owner _actor != remoteExecutedOwner} else {!local _actor}) exitWith {};
private _bearing = _actor getVariable ["acme_sked_bearing", objNull];
if (_action == "letGo") exitWith {
    if (!isNull _bearing) then {[_actor] call acme_sked_fnc_srvLetGo;};
};
if (_action == "stow") exitWith {[_actor] call acme_sked_fnc_srvStow;};
if (_action == "restore") exitWith {[_actor] call acme_sked_fnc_srvRestore;};
if (!alive _actor || {_actor getVariable ["ACE_isUnconscious", false]} || {!isNull objectParent _actor}) exitWith {};

if (_action == "layOutItem") exitWith {
    if ("ACME_SKED_Item" in items _actor) then {
        private _open = ["ACME_SKED_Open", _actor getRelPos [1.7, 0], getDir _actor] call acme_sked_fnc_place;
        if (!isNull _open) then {_actor removeItem "ACME_SKED_Item";};
    };
};
if (_action in ["foldTalon", "deployTalon"]) exitWith {
    if (isNull _target || {_actor distance _target > 3.5}
        || {!([_actor, _target] call acme_sked_fnc_canHandleEmpty)}) exitWith {};
    private _fold = _action == "foldTalon";
    if ((typeOf _target) != (["ACME_Talon_Folded", "ACME_Talon_Open"] select _fold)) exitWith {};
    private _class = ["ACME_Talon_Open", "ACME_Talon_Folded"] select _fold;
    private _replacement = [_class, getPosATL _target, getDir _target] call acme_sked_fnc_place;
    if (!isNull _replacement) then {
        deleteVehicle _target;
        [_action, _replacement, _actor] call acme_sked_fnc_traceTransport;
    };
};
if (_action in ["layOut", "pickUp", "rollUp"]) exitWith {
    if (isNull _target || {_actor distance _target > 3.5}
        || {!([_actor, _target] call acme_sked_fnc_canHandleEmpty)}) exitWith {};
    if (_action == "rollUp") then {
        if ((typeOf _target) != "ACME_SKED_Open") exitWith {};
        if (_actor canAdd "ACME_SKED_Item") exitWith {
            _actor addItem "ACME_SKED_Item";
            deleteVehicle _target;
        };
        private _rolled = ["ACME_SKED_Rolled", getPosATL _target, (getDir _target) + 90] call acme_sked_fnc_place;
        if (!isNull _rolled) then {deleteVehicle _target;};
    } else {
        if !(_target isKindOf "ACME_SKED_Pack") exitWith {};
        if (_action == "pickUp") exitWith {
            if (_actor canAdd "ACME_SKED_Item") then {
                _actor addItem "ACME_SKED_Item";
                deleteVehicle _target;
            };
        };
        private _open = ["ACME_SKED_Open", getPosATL _target, getDir _actor] call acme_sked_fnc_place;
        if (!isNull _open) then {deleteVehicle _target;};
    };
};
if (_action == "strap") exitWith {
    if (!isNull _target && {_target isKindOf "CAManBase"} && {!isNull _extra}
        && {_extra isKindOf "ACME_SKED_Open"} && {_actor distance _target <= 3.5}
        && {_target distance _extra <= 3.5} && {_actor isNotEqualTo _target}) then {
        [_actor, _target, _extra] call acme_sked_fnc_srvLoad;
    };
};
if (isNull _target || {!(_target isKindOf "ACME_SKED_Wrapped")} || {_actor distance _target > 4}) exitWith {};
private _patient = _target getVariable ["acme_sked_patient", objNull];
if (isNull _patient || {(_patient getVariable ["acme_sked_litter", objNull]) isNotEqualTo _target}) exitWith {};
switch (_action) do {
    case "unstrap": {
        if ([_actor, _target] call acme_sked_fnc_canUnstrapLitter) then {[_target] call acme_sked_fnc_srvUnstrap;};
    };
    case "takeHandle": {
        if ([_actor, _target] call acme_sked_fnc_canTakeHandle) then {[_actor, _target] call acme_sked_fnc_srvTakeHandle;};
    };
    case "lift": {
        if (_bearing isEqualTo _target) then {[_actor, _target] call acme_sked_fnc_srvLift;};
    };
    case "setDown": {
        if (_bearing isEqualTo _target) then {[_target] call acme_sked_fnc_srvSetDown;};
    };
    case "reposition": {
        [_patient, "reattach", [_patient, _target]] call acme_sked_fnc_sendLocal;
    };
    case "loadVehicle": {
        if (alive _patient && {alive _extra} && {_extra isKindOf "AllVehicles"} && {!(_extra isKindOf "CAManBase")}
            && {_actor distance _extra < 12} && {_patient distance _extra < 12}
            && {[_actor, _target] call acme_sked_fnc_canUnstrapLitter}
            && {_extra in ([_patient, 12] call ace_common_fnc_nearestVehiclesFreeSeat)}) then {
            [_patient, "loadLocal", [_patient, _extra, _actor, _target]] call acme_sked_fnc_sendLocal;
        };
    };
};
