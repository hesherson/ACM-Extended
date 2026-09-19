// Observer-only replicas: local props and rope preserve the provider's existing animation/physics behavior.
params ["_medic", "_epoch", "_operation", ["_data", []], ["_owner", -1]];
if (!hasInterface || {isNull _medic}) exitWith {};
private _record = _medic getVariable ["ACME_hang_RemoteVisual", [-1, "", [], -1]];
if ((_record select 0) > _epoch) exitWith {};
if ((_record select 0) == _epoch && {(_record select 1) == "hide"}) exitWith {};
if (_operation == "show") then {
    private _episode = _medic getVariable ["ACME_hang_VisualEpisode", [-1, false]];
    if ((_episode select 0) < _epoch) exitWith {
        [{
            params ["_medic", "_epoch"];
            isNull _medic || {((_medic getVariable ["ACME_hang_VisualEpisode", [-1, false]]) select 0) >= _epoch}
        }, {_this call ACME_fnc_hangBagVisualSync;}, _this, 3] call CBA_fnc_waitUntilAndExecute;
    };
};
// The wait above only exits its block. Unknown/stale episodes must not fall through to object creation.
if (_operation == "show" && {!((_medic getVariable ["ACME_hang_VisualEpisode", []]) isEqualTo [_epoch, true])}) exitWith {};
if (_operation == "show" && {local _medic} && {clientOwner == _owner}) exitWith {};
if (_operation == "show" && {(_record select 0) == _epoch} && {(_record select 1) == "show"}) exitWith {};

// Only the server can resolve remote object owners. Clients use local plus the sender's clientOwner.
private _ownerChanged = if (isServer) then {owner _medic != _owner} else {local _medic && {clientOwner != _owner}};
private _oldObjects = _record select 2;
if !(_oldObjects isEqualTo []) then {
    _oldObjects params ["_bag", "_anchor", "_bagHelper", "_rope"];
    if (!isNull _rope) then {[_rope] call ACME_fnc_ivLineDestroy;};
    {if (!isNull _x) then {detach _x; deleteVehicle _x;};} forEach [_bagHelper, _anchor, _bag];
};
if ((_record select 3) >= 0) then {[(_record select 3)] call CBA_fnc_removePerFrameHandler;};
_medic setVariable ["ACME_hang_RemoteVisual", [_epoch, "hide", [], -1]];
if (_operation != "show" || {!alive _medic} || {_medic getVariable ["ACE_isUnconscious", false]}
    || {!isNull objectParent _medic} || {_ownerChanged}) exitWith {};
_data params ["_patient", "_bagModel", "_bagTexture", "_handOffset", "_handSel", "_bagEuler",
    "_anchorClass", "_lineEnd", "_lineRot", "_lineTip", "_bagOut", "_ropeClass", "_lineLength", "_segments", "_useRope"];
if (isNull _patient || {_bagModel == ""}) exitWith {};
private _bag = createSimpleObject [_bagModel, [0,0,0], true];
if (isNull _bag) exitWith {};
_bag setObjectTexture [0, _bagTexture];
_bag attachTo [_medic, _handOffset, _handSel, true];
[_bag, _bagEuler] call BIS_fnc_setObjectRotation;
private _anchor = _anchorClass createVehicleLocal [0, 0, 0];
private _bagHelper = _anchorClass createVehicleLocal [0, 0, 0];
if (!isNull _anchor) then {
    _anchor allowDamage false;
    _anchor hideObject true;
    _anchor attachTo [_patient, _lineEnd];
    [_anchor, _lineRot] call BIS_fnc_setObjectRotation;
    _anchor disableCollisionWith _patient;
    _anchor disableCollisionWith _bag;
};
if (!isNull _bagHelper) then {
    _bagHelper allowDamage false;
    _bagHelper hideObject true;
    _bagHelper attachTo [_bag, _bagOut];
    _bagHelper disableCollisionWith _bag;
    _bagHelper disableCollisionWith _medic;
    if (!isNull _anchor) then {_bagHelper disableCollisionWith _anchor;};
};
private _rope = objNull;
if (_useRope && {!isNull _anchor} && {!isNull _bagHelper}) then {
    _rope = [_anchor, _lineTip, _bagHelper, [0,0,0], _lineLength, _segments, _ropeClass] call ACME_fnc_ivLineCreate;
};
private _objects = [_bag, _anchor, _bagHelper, _rope];
private _record = [_epoch, "show", _objects, -1];
_medic setVariable ["ACME_hang_RemoteVisual", _record];
private _pfh = [{
    params ["_args", "_pfh"];
    _args params ["_medic", "_patient", "_epoch", "_owner", "_objects"];
    // The captured local handles allow cleanup even after the provider object has been deleted.
    if (isNull _medic) exitWith {
        private _rope = _objects select 3;
        if (!isNull _rope) then {[_rope] call ACME_fnc_ivLineDestroy;};
        {if (!isNull _x) then {detach _x; deleteVehicle _x;};} forEach (_objects select [0, 3]);
        [_pfh] call CBA_fnc_removePerFrameHandler;
    };
    private _ownerChanged = if (isServer) then {owner _medic != _owner} else {local _medic && {clientOwner != _owner}};
    if (!alive _medic || {isNull _patient} || {_medic getVariable ["ACE_isUnconscious", false]}
        || {!isNull objectParent _medic} || {_ownerChanged}
        || {!((_medic getVariable ["ACME_hang_VisualEpisode", []]) isEqualTo [_epoch, true])}) then {
        [_medic, _epoch, "hide"] call ACME_fnc_hangBagVisualSync;
    };
}, 0.2, [_medic, _patient, _epoch, _owner, _objects]] call CBA_fnc_addPerFrameHandler;
_record set [3, _pfh];
