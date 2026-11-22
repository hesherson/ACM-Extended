/*
 * "Stage HPMK": an HPMK is laid out ready on an empty litter, so that the casualty who is loaded onto it next is
 * wrapped in it at once (asked for on 2026-11-20: "lay a sheet out over the top of the sked/litter, allowing for
 * a patient to be laid on top and then wrapped into the HPMK as soon as they are on the litter or sked").
 *
 * The laid out shell is a model fixed on the litter (the litter's acmeHpmkStaged, made by
 * tools/build_hpmk_staged.py from the kit's own model of the opened shell), like the strap models of
 * fn_strapArcs.sqf. The kit comes out of the rescuer's inventory and goes back into it when it is taken off the
 * litter again; a litter that goes away with a kit staged on it (rolled up, folded, deleted) leaves the kit on
 * the ground (XEH_postInit.sqf). fn_srvLoad.sqf wraps the casualty.
 *
 * Arguments: 0: rescuer, 1: laid out litter, 2: "start" (where the rescuer is local: the timer, then the request),
 *   "stage" or "unstage" (server), "wrap" (server, from fn_srvLoad.sqf: 1 is the casualty then, 3 the litter
 *   they are on).
 */
params ["_actor", "_litter", ["_mode", "start"], ["_extra", objNull]];

if (_mode == "start") exitWith {
    private _stage = !(_litter getVariable ["acme_sked_hpmkStaged", false]);
    [[3, 4] select _stage, [_actor, _litter, _stage], {
        (_this select 0) params ["_actor", "_litter", "_stage"];
        [_actor, ["unstageHpmk", "stageHpmk"] select _stage, _litter] call acme_sked_fnc_request;
    }, {}, ["Taking the HPMK off...", "Laying out the HPMK..."] select _stage, {
        (_this select 0) params ["_actor", "_litter", "_stage"];
        !isNull _litter && {_actor distance _litter < 3.5} && {(_litter getVariable ["acme_sked_hpmkStaged", false]) isNotEqualTo _stage}
    }] call ace_common_fnc_progressBar;
};
if (!isServer) exitWith {};

if (_mode == "wrap") exitWith {
    private _patient = _litter;
    private _on = _extra;
    // A casualty who has an HPMK of their own already (prepped, wrapped): the staged kit is not used.
    if ((_patient getVariable ["ACME_hpmk_state", ""]) != "") exitWith {
        ["ACME_hpmkReturnItem", [_actor], _actor] call CBA_fnc_targetEvent;
    };
    // (a moment later: the casualty is put on the new litter where they are local, fn_attachLocal.sqf)
    [{
        params ["_actor", "_patient", "_on"];
        if (isNull _patient || {isNull _on} || {(_patient getVariable ["acme_sked_litter", objNull]) isNotEqualTo _on}
            || {(_patient getVariable ["ACME_hpmk_state", ""]) != ""}) exitWith {
            ["ACME_hpmkReturnItem", [_actor], _actor] call CBA_fnc_targetEvent;
        };
        _patient setVariable ["ACME_hpmk_provider", _actor, true];
        _patient setVariable ["ACME_hpmk_returnPending", false, true];
        [_actor, _patient] call ACME_fnc_hpmkWrap;
    }, [_actor, _patient, _on], 1] call CBA_fnc_waitAndExecute;
};

if (isNull _litter || {!(_litter isKindOf "ACME_SKED_Open")}) exitWith {};
private _staged = _litter getVariable ["acme_sked_hpmkStaged", false];
if (_mode == "stage") exitWith {
    private _model = getText (configOf _litter >> "acmeHpmkStaged");
    if (_staged || {_model == ""} || {!("ACME_HPMK" in (items _actor))}) exitWith {};
    _actor removeItem "ACME_HPMK";
    if ((_model select [0, 1]) == "\") then {_model = _model select [1];};
    private _sheet = createSimpleObject [_model, getPosWorld _litter];
    _sheet attachTo [_litter, [0, 0, 0]];
    _litter setVariable ["acme_sked_hpmkSheet", _sheet, true];
    _litter setVariable ["acme_sked_hpmkStaged", true, true];
};
if (_mode == "unstage") exitWith {
    if (!_staged) exitWith {};
    deleteVehicle (_litter getVariable ["acme_sked_hpmkSheet", objNull]);
    _litter setVariable ["acme_sked_hpmkSheet", nil, true];
    _litter setVariable ["acme_sked_hpmkStaged", false, true];
    // back to who took it off (their inventory, or the ground at their feet if it is full: ACE)
    if (!isNull _actor) then {["ACME_hpmkReturnItem", [_actor], _actor] call CBA_fnc_targetEvent;};
};
