/* A grant belongs to one requesting provider, locality generation and still-idle native controller. */
params [["_patient",objNull,[objNull]],["_medic",objNull,[objNull]],["_request",[],[[]]],["_accepted",false,[false]],["_grantUntil",-1,[0]],["_reason","treatment-busy",[""]]];
if (canSuspend) exitWith {isNil {[_patient,_medic,_request,_accepted,_grantUntil,_reason] call ACME_fnc_resusAck;};};
if (count _request != 9) exitWith {};
if (isNull _medic || {!local _medic}) exitWith {};
_request params [["_kind","",[""]],["_requestedPatient",objNull,[objNull]],["_token","",[""]],["_epoch",-1,[0]],
    ["_providerOwner",-1,[0]],["_locality",-1,[0]],["_nativeEpoch",-1,[0]],["_options",[],[[]]]];
if (!(_kind in ["cpr","bvm"]) || {_token == ""} || {!finite _epoch} || {!finite _providerOwner}
    || {!finite _locality} || {!finite _nativeEpoch}) exitWith {};
private _key = "ACME_resusToken_" + _kind;
private _state = [_patient,_token,_epoch,_providerOwner,_locality,_nativeEpoch];
if (_accepted && {(_medic getVariable [_key,[]]) isEqualTo _state}) exitWith {};
private _same = (_medic getVariable ["ACME_resusPending",[]]) isEqualTo _request;
private _currentNative = if (_kind == "cpr") then {
    1 + ((missionNamespace getVariable ["ACM_circulation_CPR_Epoch",0]) max (_medic getVariable ["ACM_circulation_CPR_Sequence",0]))
} else {1 + (missionNamespace getVariable ["ACM_core_ContinuousAction_Epoch",0])};
private _boundIndex = [0,2] select (_kind == "bvm");
private _playerBound = count _options > _boundIndex && {(_options select _boundIndex) isEqualTo true};
private _valid = _same && {_accepted} && {_patient isEqualTo _requestedPatient}
    && {finite _grantUntil} && {serverTime < _grantUntil}
    && {(_request select 8) isEqualType 0} && {finite (_request select 8)} && {serverTime < (_request select 8)}
    && {!isNull _patient} && {_epoch == ([_patient] call ACME_fnc_clinicalEpoch)}
    && {_providerOwner == clientOwner} && {(_medic getVariable ["ACME_providerLocalityEpoch",0]) == _locality}
    && {alive _medic} && {[_medic] call ace_common_fnc_isAwake}
    && {!_playerBound || {!isNil "ACE_player" && {_medic isEqualTo ACE_player}}}
    && {_currentNative == _nativeEpoch}
    && {!(missionNamespace getVariable ["ACM_core_ContinuousAction_Active",false])}
    && {!(_medic getVariable ["ACM_circulation_isPerformingCPR",false])}
    && {[_medic,_patient] call ACME_fnc_patientInteractionContact};
if (_same) then {_medic setVariable ["ACME_resusPending",[],false];};
if (!_valid) exitWith {
    if (_accepted && {!isNull _patient}) then {
        [_patient,"resus",["release",_kind,_medic,_token,_epoch,_providerOwner,_locality,_nativeEpoch,serverTime,[]]] call ACME_fnc_ownerDispatch;
    };
    if (_same) then {["Treatment could not start. Review the patient and try again.",2,_medic] call ace_common_fnc_displayTextStructured;};
};
_medic setVariable [_key,_state,false];
if (_kind == "cpr") then {
    [_medic,_patient,_state] call ACM_circulation_fnc_beginCPR;
} else {
    [_medic,_patient,_options param [0,false],_options param [1,false],_state] call ACM_breathing_fnc_useBVM;
};
// Startup can reject a provider or patient that changed between grant and this callback.
private _started = if (_kind == "cpr") then {
    (_medic getVariable ["ACM_circulation_CPR_Epoch",-1]) == _nativeEpoch
} else {
    (missionNamespace getVariable ["ACM_breathing_BVM_LocalSession",[]]) isEqualTo [_medic,_patient,_nativeEpoch]
};
if (!_started) then {
    _medic setVariable [_key,[],false];
    [_patient,"resus",["release",_kind,_medic,_token,_epoch,_providerOwner,_locality,_nativeEpoch,serverTime,[]]] call ACME_fnc_ownerDispatch;
};
