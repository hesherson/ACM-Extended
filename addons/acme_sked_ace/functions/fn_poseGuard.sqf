/*
 * Where the casualty is local: once a second, keep a strapped casualty on the SKED, and in the pose. The
 * pose is put back after it has been wrong for two checks running, and then at most every 4 s, so a pose
 * that does not hold (ACE or the engine overriding it) costs one global animation change every 4 s, not
 * every second. Stops by itself when they leave the SKED.
 * Arguments: 0: casualty.
 */
params ["_patient"];
if (!local _patient || {(_patient getVariable ["acme_sked_guard", -1]) >= 0}) exitWith {};
private _id = [{
    params ["_args", "_id"];
    _args params ["_patient"];
    private _litter = _patient getVariable ["acme_sked_litter", objNull];
    if (!local _patient || {isNull _litter}) exitWith {
        [_id] call CBA_fnc_removePerFrameHandler;
        _patient setVariable ["acme_sked_guard", nil];
    };
    if (!isNull objectParent _patient || {_patient getVariable ["acme_sked_loading", false]}) exitWith {};
    private _expected = [_litter] call acme_sked_fnc_patientRoot;
    if ((attachedTo _patient) isNotEqualTo _expected) then {
        if ((_litter getVariable ["acme_sked_attach", []]) isEqualTo []) then {
            [_patient, _litter, false] call acme_sked_fnc_align;
        } else {
            [_patient, _litter] call acme_sked_fnc_reattach;
        };
    };
    // the litter's straps sit on what he wears now (bare, or the HPMK)
    [_litter] call acme_sked_fnc_strapFit;
    if (!alive _patient) exitWith {};
    private _anim = [_patient] call acme_sked_fnc_patientPose;
    if ((toLowerANSI animationState _patient) isEqualTo (toLowerANSI _anim)) exitWith {_patient setVariable ["acme_sked_poseMiss", 0]};
    private _miss = (_patient getVariable ["acme_sked_poseMiss", 0]) + 1;
    _patient setVariable ["acme_sked_poseMiss", _miss];
    if (_miss >= 2 && {CBA_missionTime > (_patient getVariable ["acme_sked_poseAt", -100]) + 4}) then {
        _patient setVariable ["acme_sked_poseAt", CBA_missionTime];
        [_patient, _anim, 2] call ace_common_fnc_doAnimation;
        [{
            params ["_patient", "_litter"];
            if (local _patient && {!isNull _litter} && {isNull objectParent _patient}
                && {!(_patient getVariable ["acme_sked_loading", false])}
                && {(_patient getVariable ["acme_sked_litter", objNull]) isEqualTo _litter}) then {
                [_patient, _litter] call acme_sked_fnc_align;
            };
        }, [_patient, _litter], .35] call CBA_fnc_waitAndExecute;
    };
}, 1, [_patient]] call CBA_fnc_addPerFrameHandler;
_patient setVariable ["acme_sked_guard", _id];
