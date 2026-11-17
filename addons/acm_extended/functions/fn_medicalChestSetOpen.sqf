/* Trusted server-side transition used after validation or during initialization. */
params ["_chest", "_opening", "_revision", ["_initial", false], ["_actor", objNull]];
if (!isServer || {is3DEN} || {isRemoteExecuted && {_initial}}) exitWith {};
private _cabinet = _chest getVariable ["ACME_medicalChestCabinet", objNull];
private _cargo = _chest getVariable ["ACME_medicalChestCargo", objNull];
private _lid = _chest getVariable ["ACME_medicalChestLid", objNull];
private _restPose = _chest getVariable ["ACME_medicalChestLidRest", []];
private _seatPose = _chest getVariable ["ACME_medicalChestLidSeat", []];

(_chest getVariable "ACME_medicalChestPlacement") params ["_base", "_heading"];
if (!_opening && {_initial}) exitWith {
    // Keep the same cargo, and move it out of native Gear reach while shut.
    detach _cargo;
    _cargo setPosWorld (_base vectorAdd [0, 0, -25]);
    _chest hideObjectGlobal false;
    deleteVehicle _cabinet;
    deleteVehicle _lid;
    _chest setVariable ["ACME_medicalChestCabinet", objNull, true];
    _chest setVariable ["ACME_medicalChestLid", objNull];
    _chest setVariable ["ACME_medicalChestLidRest", []];
    _chest setVariable ["ACME_medicalChestLidSeat", []];
    _chest setVariable ["ACME_medicalChestViewers", []];
    _chest setVariable ["ACME_medicalChestState", [_revision + 1, false], true];
    _chest setVariable ["ACME_medicalChestTransition", false, true];
};

if (_opening) then {
    private _class = "ACME_MedicalChest8Drawers";
    _cabinet = createVehicle [_class, ASLToATL _base, [], 0, "CAN_COLLIDE"];
    if (isNull _cabinet) exitWith {};
    private _cabinetPose = [_cabinet, _base, _heading, "cabinet", [0, 0, 1], false] call ACME_fnc_medicalChestPlace;
    _seatPose = [_cabinetPose] call ACME_fnc_medicalChestLidSeat;
    _lid = createSimpleObject ["ACME_MedicalChestLid", _seatPose select 0];
    if (isNull _lid) exitWith {
        deleteVehicle _cabinet;
        _cabinet = objNull;
    };
    _cabinet allowDamage false;
    (getObjectTextures _chest) params [["_texture", ""], ["_artwork", ""]];
    if (_texture != "") then {
        _cabinet setObjectTextureGlobal ["camo", _texture];
        _lid setObjectTextureGlobal ["camo", _texture];
    };
    if (_artwork != "") then {_lid setObjectTextureGlobal ["lid_artwork", _artwork];};
    _cabinet enableSimulationGlobal false;
    _cabinetPose params ["_cabinetPosition", "_cabinetDir", "_cabinetUp"];
    _cabinet setVectorDirAndUp [_cabinetDir, _cabinetUp];
    _cabinet setPosWorld _cabinetPosition;
    _cargo attachTo [_cabinet, [0, 0, 0]];
    _cabinet setVariable ["ACME_medicalChestAnchor", _chest, true];
    _chest setVariable ["ACME_medicalChestCabinet", _cabinet, true];
    _chest setVariable ["ACME_medicalChestLid", _lid];
    private _drawerPlan = [_cabinet] call ACME_fnc_medicalChestDrawerPlan;
    [_cabinet, _drawerPlan, 0] call ACME_fnc_medicalChestDrawers;
    ([_base, _heading, _chest, _lid] call ACME_fnc_medicalChestLidBase) params ["_side", "_normal"];
    _seatPose params ["_seat", "_outward", "_lateral"];
    _restPose = [_lid, _side, _heading, "lid", _normal, false] call ACME_fnc_medicalChestPlace;
    _seatPose = [_seat, _outward, [0, 0, 1], _outward, _lateral];
    ([_seatPose, _restPose] select _initial) params ["_position", "_dir", "_up"];
    _lid setVectorDirAndUp [_dir, _up];
    _lid setPosWorld _position;
    private _lidTextures = getObjectTextures _lid;
    diag_log format ["[ACME] Medical chest finish: %1, cabinet %2, lid %3, artwork %4", _texture,
        ((getObjectTextures _cabinet) param [0, ""]) isEqualTo _texture,
        (_lidTextures param [0, ""]) isEqualTo _texture,
        (_lidTextures param [1, ""]) isEqualTo _artwork];
    _chest setVariable ["ACME_medicalChestLidRest", _restPose];
    _chest setVariable ["ACME_medicalChestLidSeat", _seatPose];
    _chest hideObjectGlobal true;
    _chest setVariable ["ACME_medicalChestDrawerPlan", _drawerPlan];
    _chest setVariable ["ACME_medicalChestDrawerFraction", 0];
    _chest setVariable ["ACME_medicalChestDrawerPFH", -1];
};
if (_opening && {isNull _cabinet}) exitWith {};
if (_initial) exitWith {
    _chest setVariable ["ACME_medicalChestState", [_revision + 1, true], true];
};

_chest setVariable ["ACME_medicalChestTransition", true, true];
if (!_opening) then {
    _chest setVariable ["ACME_medicalChestViewers", []];
    ["ACME_medicalChestClosing", [_cargo, _revision]] call CBA_fnc_globalEvent;
};
private _sound = ["medical_chest_close", "medical_chest_open"] select _opening;
playSound3D [format ["acm_extended\sound\%1.ogg", _sound], objNull, false, getPosWorld _chest, 1.5, 1, 18];
if (isNull _lid) exitWith {
    [ACME_fnc_medicalChestSetOpen, [_chest, false, _revision, true]] call CBA_fnc_execNextFrame;
};
[_chest, _cabinet, _lid, _cargo, _actor, _revision, _opening, _seatPose, _restPose] call ACME_fnc_medicalChestLidMotion;
