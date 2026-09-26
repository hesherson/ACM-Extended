// Request one patient-owner lease before creating Hang Bag presentation or applying flow.
params ["_medic", "_patient", ["_bodyPart", ""], ["_fluidType", ""]];
_bodyPart = toLower _bodyPart;
if (isNull _patient || {isNull _medic} || {!local _medic}) exitWith {};
if (_medic getVariable ["ACME_hang_Active", false]) exitWith {
    ["You're already holding a bag up.", 2, _medic] call ace_common_fnc_displayTextStructured;
};
if (!alive _medic || {_medic getVariable ["ACE_isUnconscious", false]}
    || {!isNull objectParent _medic} || {!(missionNamespace getVariable ["ACME_sys_hang", true])}) exitWith {
    [_medic] call ACME_fnc_hangBagPrepStop;
};
if (_fluidType == "") then {_fluidType = [_patient, _bodyPart] call ACME_fnc_hangBagFluidType;};

// A monotonic episode distinguishes even a same-frame cancel/restart. Only the owner
// writes patient custody/flow; replicated provider Active is not the acquisition lock.
private _episode = serverTime max ((_medic getVariable ["ACME_hang_Start", -1]) + 0.001);
_medic setVariable ["ACME_hang_Active", true, true];
_medic setVariable ["ACME_hang_Claimed", false, false];
_medic setVariable ["ACME_hang_ClaimRequestedAt", serverTime, false];
_medic setVariable ["ACME_hang_ClaimAckAt", serverTime, false];
_medic setVariable ["ACME_hang_ClaimEpoch", [_patient] call ACME_fnc_clinicalEpoch, false];
_medic setVariable ["ACME_hang_ClaimOwner", owner _medic, false];
_medic setVariable ["ACME_hang_PlayerBound", hasInterface && {_medic isEqualTo (call ACME_fnc_controlledProvider)}, false];
_medic setVariable ["ACME_hang_Patient", _patient, true];
_medic setVariable ["ACME_hang_Part", _bodyPart];
_medic setVariable ["ACME_hang_FluidType", _fluidType, true];
_medic setVariable ["ACME_hang_Start", _episode];
_medic setVariable ["ACME_hang_sawFlow", false];
_medic setVariable ["ACME_hang_LastPos", getPosASL _medic];

// the manual release and the placement tuner.
private _ids = [];
_ids pushBack ([0x01, [false,false,false], { [false] call ACME_fnc_hangBagStop; }, "keydown", "", false, 0] call CBA_fnc_addKeyHandler);
_ids pushBack ([0xF1, [false,false,false], { [false] call ACME_fnc_hangBagStop; }, "keydown", "", false, 0] call CBA_fnc_addKeyHandler);
// the placement tuner, with sliders, is a debug dev tool. only bind f2 to it when debug features are enabled.
if (missionNamespace getVariable ["ACME_debug_enabled", false]) then {
    _ids pushBack ([0x3C, [false,false,false], { [] call ACME_fnc_hangBagTuneOpen; }, "keydown", "", false, 0] call CBA_fnc_addKeyHandler);
};
_medic setVariable ["ACME_hang_KeyIDs", _ids];

private _pfh = [ACME_fnc_hangBagTick, 0.05, [_medic, _patient]] call CBA_fnc_addPerFrameHandler;
_medic setVariable ["ACME_hang_PFH", _pfh];
[_patient, "hangBagClaim", [_medic, _episode,
    missionNamespace getVariable ["ACME_hang_flowMult", 1.75],
    _medic getVariable ["ACME_hang_ClaimEpoch", -1], owner _medic]] call ACME_fnc_ownerDispatch;
