/* B395: draw (or remove) a bag hung on an IV stand's hook, and its line to the casualty, on this machine
 * (fn_ivStandServer.sqf sends it to every machine, JIP included). Everything here is a local, collision-free
 * prop: the bag art is the hold's (ACE bag model with the fluid's texture), the line is the hold's IV line rope
 * from the same point on the casualty. */
if (!hasInterface) exitWith {};
params ["_stand", "_slot", "_patient", "_show", ["_key", "", [""]], ["_model", ""], ["_tex", ""], ["_ropeClass", ""], ["_vol", 500], ["_part", ""]];
if (isNil "ACME_ivStand_local") then {ACME_ivStand_local = createHashMap;};
private _localKey = if (_key != "") then {_key} else {format ["%1_%2", hashValue _stand, _slot]};

// whatever this hook showed before goes first (and any drawing whose stand is gone)
private _drop = [];
{
    if (_x == _localKey || {isNull (_y param [4, objNull])} || {(_y param [4, objNull]) isEqualTo _stand && {(_y param [5, -1]) == _slot}}) then {
        _y params [["_bag", objNull], ["_anchor", objNull], ["_helper", objNull], ["_rope", objNull]];
        if (!isNull _rope) then {[_rope] call ACME_fnc_ivLineDestroy;};
        {if (!isNull _x) then {detach _x; deleteVehicle _x;};} forEach [_helper, _anchor, _bag];
        _drop pushBack _x;
    };
} forEach ACME_ivStand_local;
{ACME_ivStand_local deleteAt _x;} forEach _drop;
if (!_show || {isNull _stand} || {isNull _patient} || {_model == ""}) exitWith {};

private _hook = (missionNamespace getVariable ["ACME_ivStand_hooks", [[0, 0.13, 0.76], [0, -0.13, 0.76]]]) param [_slot, [0, 0.13, 0.76]];
private _bag = createSimpleObject [_model, [0, 0, 0], true];
_bag setObjectTexture [0, _tex];  // (_model is the bag class: a simple object made from a model path ignores textures)
_bag attachTo [_stand, _hook];
(missionNamespace getVariable ["ACME_ivStand_bagVectors", [[0, 1, 0], [0, 0, -1]]]) params ["_dir", "_up"];
_bag setVectorDirAndUp [_dir, _up];

private _helperClass = missionNamespace getVariable ["ACME_hang_anchorClass", "ace_fastroping_helper"];
private _anchor = _helperClass createVehicleLocal [0, 0, 0];
private _helper = _helperClass createVehicleLocal [0, 0, 0];
private _lineEnd = if (_vol == 250) then {
    missionNamespace getVariable ["ACME_hang_linePatientOffset_250", [0.35404, -0.0718271, 0.12404]]
} else {
    missionNamespace getVariable ["ACME_hang_linePatientOffset", [0.399215, -0.0718271, 0.12404]]
};
private _lineRot = if (_vol == 250) then {
    missionNamespace getVariable ["ACME_hang_linePatientEuler_250", [-173.23, -84.1472, 180]]
} else {
    missionNamespace getVariable ["ACME_hang_linePatientEuler", [-186.934, -84.1472, 180]]
};
{
    _x allowDamage false;
    _x hideObject true;
} forEach [_anchor, _helper];
// the line runs to the limb whose bag it is (that limb's bone); a bag with no known limb uses the held bag's spot
private _bone = createHashMapFromArray [["leftarm", "LeftForeArm"], ["rightarm", "RightForeArm"], ["leftleg", "LeftLeg"],
    ["rightleg", "RightLeg"], ["body", "Spine3"], ["head", "Neck"]] getOrDefault [toLowerANSI _part, ""];
if (_bone != "") then {
    _anchor attachTo [_patient, [0, 0, 0], _bone, true];
} else {
    _anchor attachTo [_patient, _lineEnd];
    [_anchor, _lineRot] call BIS_fnc_setObjectRotation;
};
_anchor disableCollisionWith _patient;
_helper attachTo [_stand, _hook vectorAdd (missionNamespace getVariable ["ACME_ivStand_bagOutlet", [0, 0, -0.16]])];
_helper disableCollisionWith _stand;
_helper disableCollisionWith _anchor;
private _rope = objNull;
if (missionNamespace getVariable ["ACME_hang_useRope", true]) then {
    _rope = [_anchor, missionNamespace getVariable ["ACME_hang_lineTipOffset", [0, 0.04, 0.06]], _helper, [0, 0, 0],
        missionNamespace getVariable ["ACME_hang_lineLength", 3], missionNamespace getVariable ["ACME_hang_lineSagSegs", 24], _ropeClass] call ACME_fnc_ivLineCreate;
};
ACME_ivStand_local set [_localKey, [_bag, _anchor, _helper, _rope, _stand, _slot, _ropeClass, getPosASL _stand]];
