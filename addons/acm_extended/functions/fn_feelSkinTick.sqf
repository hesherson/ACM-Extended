/* The contact clock starts at the observed held frame, not at the button press or the kneeling request. */
params ["_args", "_pfh"];
_args params ["_medic", "_serial"];
if (isNull _medic) exitWith {[_pfh] call CBA_fnc_removePerFrameHandler;};
private _record = _medic getVariable ["ACME_feelSkinAction", []];
if (_record isEqualTo [] || {(_record select 0) != _serial}) exitWith {[_pfh] call CBA_fnc_removePerFrameHandler;};
(_record select 1) params ["", "_patient"];
private _epoch = _record select 2;
private _pose = _medic getVariable ["ACME_treatmentPoseState", []];
private _menu = _record select 8;
private _localPlayer = hasInterface && {_medic isEqualTo ACE_player};
private _invalid = !local _medic || {!alive _medic} || {!([_medic] call ace_common_fnc_isAwake)}
    || {isNull _patient} || {isNull objectParent _medic && {[_medic] call ACME_fnc_animBlocked}}
    || {(_record select 7) != (_medic getVariable ["ACME_providerLocalityEpoch", 0])}
    || {(_record select 14) != ([_patient] call ACME_fnc_clinicalEpoch)}
    || {objectParent _medic isNotEqualTo (_record select 11)}
    || {objectParent _medic isNotEqualTo objectParent _patient}
    || {([_medic, _patient] call ACME_fnc_patientInteractionDistance) > ace_medical_gui_maxDistance}
    || {!([_medic, _patient, ["isNotInside", "isNotSwimming", "isNotInZeus"]] call ace_common_fnc_canInteractWith)}
    || {_epoch >= 0 && {(_pose param [0, -1]) != _epoch}}
    || {(_record select 10) && {isNull _menu || {!_localPlayer}
        || {(missionNamespace getVariable ["ace_medical_gui_target", objNull]) isNotEqualTo _patient}}}
    || {CBA_missionTime - (_record select 5) > 12};
if (_localPlayer) then {
    _invalid = _invalid || {["MoveForward", "MoveBack", "MoveLeft", "MoveRight", "TurnLeft", "TurnRight",
        "MoveFastForward", "MoveSlowForward", "Evasive"] findIf {(inputAction _x) > 0.01} >= 0};
};
if (_invalid) exitWith {[_medic, _serial] call ACME_fnc_feelSkinStop;};
private _phase = _record select 3;
if (_phase == -1) exitWith {
    // This is exactly the hands-on-chest workspace entry used by Chest Seal. Once observed,
    // hand off without another weapon stow, stand/kneel sequence or patient animation.
    if ((_pose param [3, -1]) >= 2) then {
        private _next = [_medic, "feelSkin", -1, _patient, true] call ACME_fnc_treatmentPoseStart;
        if (_next < 0) exitWith {[_medic, _serial] call ACME_fnc_feelSkinStop;};
        _record set [2, _next];
        _record set [3, 0];
    };
};
if (_phase == 0) exitWith {
    if ((_pose param [3, -1]) == 3) then {
        _record set [3, 1];
        _record set [4, _pose select 14];
    };
};
if (_phase == 1) then {
    if (_epoch >= 0 && {(_pose param [3, -1]) != 3}) exitWith {[_medic, _serial] call ACME_fnc_feelSkinStop;};
    if (CBA_missionTime - (_record select 4) >= 1.5) then {
        // No second Putdown reach/return. Release the held medic3 straight through its normal exit graph.
        [_medic, _serial, true] call ACME_fnc_feelSkinStop;
    };
};
