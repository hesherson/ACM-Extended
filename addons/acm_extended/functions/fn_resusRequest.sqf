/* Multiplayer resuscitation admission. Clinical/animation work starts only after the patient owner's grant. */
params [["_kind","",[""]],["_medic",objNull,[objNull]],["_patient",objNull,[objNull]],["_options",[],[[]]]];
if (canSuspend) exitWith {
    private _answer=false;
    isNil {_answer=[_kind,_medic,_patient,_options] call ACME_fnc_resusRequest;};
    _answer
};
if (!(_kind in ["cpr","bvm"]) || {isNull _medic} || {isNull _patient} || {!local _medic}
    || {!alive _medic} || {!([_medic] call ace_common_fnc_isAwake)}
    || {!([_medic,_patient] call ACME_fnc_patientInteractionContact)}
    || {missionNamespace getVariable ["ACM_core_ContinuousAction_Active",false]}
    || {_medic getVariable ["ACM_circulation_isPerformingCPR",false]}) exitWith {false};
private _cprLocal = missionNamespace getVariable ["ACM_circulation_CPR_LocalSession",[]];
if (_kind == "bvm" && {count _cprLocal == 3} && {(_cprLocal select 0) isEqualTo _medic}) exitWith {false};
private _pending = _medic getVariable ["ACME_resusPending",[]];
if !(_pending isEqualTo []) exitWith {false};
private _playerBound = hasInterface && {!isNil "ACE_player"} && {_medic isEqualTo ACE_player};
_options = if (_kind == "bvm") then {[_options param [0,false],_options param [1,false],_playerBound]} else {[_playerBound]};
private _epoch = [_patient] call ACME_fnc_clinicalEpoch;
private _locality = _medic getVariable ["ACME_providerLocalityEpoch",0];
private _serial = (missionNamespace getVariable ["ACME_resusSequence",0]) + 1;
missionNamespace setVariable ["ACME_resusSequence",_serial];
private _token = format ["%1:%2:%3:%4",clientOwner,netId _medic,_locality,_serial];
private _nativeEpoch = if (_kind == "cpr") then {
    1 + ((missionNamespace getVariable ["ACM_circulation_CPR_Epoch",0]) max (_medic getVariable ["ACM_circulation_CPR_Sequence",0]))
} else {1 + (missionNamespace getVariable ["ACM_core_ContinuousAction_Epoch",0])};
private _until = serverTime + 10;
private _request = [_kind,_patient,_token,_epoch,clientOwner,_locality,_nativeEpoch,+_options,_until];
_medic setVariable ["ACME_resusPending",_request,false];
[_patient,"resus",["claim",_kind,_medic,_token,_epoch,clientOwner,_locality,_nativeEpoch,_until-10,+_options]] call ACME_fnc_ownerDispatch;
[{
    params ["_medic","_request"];
    if (isNull _medic || {!local _medic} || {(_medic getVariable ["ACME_resusPending",[]]) isNotEqualTo _request}) exitWith {};
    _request params ["_kind","_patient","_token","_epoch","_providerOwner","_locality","_nativeEpoch"];
    _medic setVariable ["ACME_resusPending",[],false];
    if (!isNull _patient) then {
        [_patient,"resus",["release",_kind,_medic,_token,_epoch,_providerOwner,_locality,_nativeEpoch,serverTime,[]]] call ACME_fnc_ownerDispatch;
    };
    ["Treatment confirmation timed out. Try again.",2,_medic] call ace_common_fnc_displayTextStructured;
},[_medic,_request],10] call CBA_fnc_waitAndExecute;
true
