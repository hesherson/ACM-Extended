#include "..\script_component.hpp"
/* Patient-owner decision. Cancel tombstones precede refunds; only a live exact funded binding
 * can create equipment. A replay returns its immutable outcome without equipping another item.
 */
if (canSuspend) exitWith {isNil {_this call FUNC(shieldCommit);};};
params ["_mode","_request",["_hops",0],["_proof",[]]];
if (!(_mode in ["apply","cancel","query","proofQuery","proof","settled","retire","terminalClosed"]) || {!(_request isEqualType [])} || {count _request != 12}) exitWith {};
_request params ["_patient","_medic","_id","_epoch","_kit","_medicKit","_locality","_deadline","_receipt","_source","_eyeIndex","_period"];
if (isNull _patient || {!(_id isEqualType "")}
    || {!(_receipt isEqualType [])} || {count _receipt != 4}
    || {(_receipt select 1) != "kat_eyecovers"} || {!((_receipt select 3) isEqualType "")}
    || {_id != ("ocular-shield:" + (_receipt select 3))}
    || {!(_eyeIndex in [0,1])} || {!(_deadline isEqualType 0)} || {!finite _deadline}
    || {!(_period isEqualType [])} || {count _period != 2}) exitWith {};
private _private = missionNamespace getVariable [QGVAR(shieldDecisions),createHashMap];
{
    private _prior = _private get _x;
    private _scope = _prior select 0;
    private _p = _scope select 0;
    if (serverTime > (_scope select 7)+30 && {isNull _p
        || {count ((_p getVariable [QGVAR(shieldTerminal),createHashMap]) getOrDefault [_x,[]]) >= 2}}) then {_private deleteAt _x;};
} forEach +(keys _private);
private _decision = _private getOrDefault [_id,[]];
if (_mode == "proofQuery") exitWith {
    if ((_period select 0) != clientOwner) exitWith {};
    if (_decision isEqualTo []) then {
        // Closing a never-applied departed period certifies cancellation. A late
        // packet can never resume that old period, including an away/back move.
        if (local _patient && {_period isEqualTo [clientOwner,_patient getVariable ["ACME_providerLocalityEpoch",0]]}) exitWith {};
        _decision = [_request,false];
        _private set [_id,_decision];
        missionNamespace setVariable [QGVAR(shieldDecisions),_private];
    };
    if (count _decision == 2 && {(_decision select 0) isEqualTo _request}
        && {(_decision select 1) isEqualType false}) then {
        [QGVAR(shieldDecisionProof),[_request,_decision select 1],_patient] call CBA_fnc_targetEvent;
    };
};
if (!local _patient) exitWith {
    if (_hops >= 0 && {_hops < 4}) then {
        [QGVAR(applyEyeShield),[_mode,_request,_hops+1,_proof],_patient] call CBA_fnc_targetEvent;
    };
};
private _all = _patient getVariable [QGVAR(shieldReceipts),createHashMap];
private _old = _all getOrDefault [_id,[]];
private _incoming = _patient getVariable [QGVAR(shieldIncoming),createHashMap];
private _terminals = _patient getVariable [QGVAR(shieldTerminal),createHashMap];
private _reply = {
    params ["_accepted"];
    [QGVAR(shieldResult),[_request,_accepted],_source] call CBA_fnc_ownerEvent;
};
if (_mode == "settled") exitWith {
    if !(_proof in ["applied","refunded","spent"]) exitWith {};
    private _existing = _terminals getOrDefault [_id,[]];
    if (count _existing == 3 && {(_existing select 0) isEqualTo _request} && {_existing select 2}) then {
        _proof = _existing select 1;
    } else {_terminals set [_id,[_request,_proof]];};
    _patient setVariable [QGVAR(shieldTerminal),_terminals,true];
    _incoming deleteAt _id;
    _patient setVariable [QGVAR(shieldIncoming),_incoming,true];
    [QGVAR(shieldClosed),[_request,_proof],_source] call CBA_fnc_ownerEvent;
};
if (_mode == "terminalClosed") exitWith {
    if !(_proof in ["applied","refunded","spent"]) exitWith {};
    private _terminal = _terminals getOrDefault [_id,[]];
    if (_terminal isEqualTo [] || {(_terminal select 0) isEqualTo _request}) then {
        _terminals set [_id,[_request,_proof,true]];
        _patient setVariable [QGVAR(shieldTerminal),_terminals,true];
    };
};
if (_mode == "retire") exitWith {
    if (serverTime <= _deadline+30) exitWith {};
    private _terminal = _terminals getOrDefault [_id,[]];
    if (_terminal isEqualTo []) then {
        _terminals set [_id,[_request,"spent"]];
        _patient setVariable [QGVAR(shieldTerminal),_terminals,true];
    };
    _incoming deleteAt _id;
    _patient setVariable [QGVAR(shieldIncoming),_incoming,true];
    if (!isNull _medic) then {[QGVAR(shieldCleanup),[_medic],_medic] call CBA_fnc_targetEvent;};
    // A closed expired scope may only retire its already-debited source as spent.
    // It never grants equipment or authorizes a guessed negative/refund.
    [true] call _reply;
};
private _terminal = _terminals getOrDefault [_id,[]];
if (count _terminal >= 2 && {(_terminal select 0) isEqualTo _request}) exitWith {
    [(_terminal select 1) != "refunded"] call _reply;
};
if (_mode == "proof") exitWith {
    if !(_proof isEqualType false) exitWith {};
    if (_decision isNotEqualTo [] && {!(_decision isEqualTo [_request,_proof])}) exitWith {};
    if (_old isNotEqualTo [] && {!(_old isEqualTo [_request,_proof])}) exitWith {};
    _private set [_id,[_request,_proof]];
    missionNamespace setVariable [QGVAR(shieldDecisions),_private];
    _all set [_id,[_request,_proof]];
    _incoming set [_id,_request];
    _patient setVariable [QGVAR(shieldIncoming),_incoming,true];
    _patient setVariable [QGVAR(shieldReceipts),_all,true];
    [_proof] call _reply;
};
if (_old isNotEqualTo []) exitWith {
    if ((_old select 0) isEqualTo _request) then {
        _incoming set [_id,_request];_patient setVariable [QGVAR(shieldIncoming),_incoming,true];
        [_old select 1] call _reply;
    };
};
// Public clinical state may lag the native HMD across ownership transfer. Only
// the machine that owned the captured period may certify its missing outcome.
// A new owner must never reinterpret an already fitted shield as a rejection.
if (_decision isNotEqualTo []) exitWith {
    if (count _decision == 2 && {(_decision select 0) isEqualTo _request}
        && {(_decision select 1) isEqualType false}) then {
        _all set [_id,_decision];
        _incoming set [_id,_request];_patient setVariable [QGVAR(shieldIncoming),_incoming,true];
        _patient setVariable [QGVAR(shieldReceipts),_all,true];
        [_decision select 1] call _reply;
    };
};
if !(_period isEqualTo [clientOwner,_patient getVariable ["ACME_providerLocalityEpoch",0]]) exitWith {
    if (serverTime > _deadline+30) then {
        ["retire",_request] call FUNC(shieldCommit);
    } else {[QGVAR(shieldDecisionQuery),[_request],_period select 0] call CBA_fnc_ownerEvent;};
};
// Retire only expired completed scopes. A stale packet cannot regain authority after its
// tombstone leaves this bounded history: its funding binding has already been withdrawn.
{
    private _entry = _all get _x;
    private _scope = _entry select 0;
    if ((_scope select 7) + 30 < serverTime
        && {!(_scope in ((_scope select 1) getVariable [QGVAR(shieldBindings),[]]))}) then {_all deleteAt _x;};
} forEach +(keys _all);
if (count _all >= 64) exitWith {};
private _fundingKey = QGVAR(shieldFunding_) + (((_receipt select 3) splitString ":") joinString "_");
private _binding = _medic getVariable [_fundingKey,[]];
private _funded = _request in (_medic getVariable [QGVAR(shieldBindings),[]])
    && {_binding isEqualTo [_request,"sent"]};
// Missing public scope can be in transit; it never authorizes a positive or a refund.
// Cancellation is safe without it: the source still requires its own real private receipt.
if (_mode != "cancel" && {!_funded} && {serverTime <= _deadline}) exitWith {};
private _providerPeriod = if (local _medic) then {[clientOwner,_medic getVariable ["ACME_providerLocalityEpoch",0]]}
    else {_medic getVariable ["ACME_vent_batterySwapOwnerPeriod",[]]};
// The counter itself is machine-local. A provider's public period can also lag its
// newly published binding, so wait for that generation instead of guessing failure.
if (_mode == "apply" && {_funded} && {owner _medic == _source}
    && {count _providerPeriod != 2 || {(_providerPeriod select 0) != _source}
        || {(_providerPeriod select 1) < _locality}}) exitWith {};
// This patient-owned custody fence survives loss of the provider object/roster.
// Install before any HMD mutation and retain until actual settlement or bounded spent retirement.
if (_funded || {_mode == "cancel"}) then {
    _incoming set [_id,_request];
    _patient setVariable [QGVAR(shieldIncoming),_incoming,true];
};
private _accepted = _mode == "apply" && {_funded} && {alive _patient} && {alive _medic}
    && {_epoch == (_patient getVariable ["ACME_clinicalEpoch",0])}
    && {_kit == (_patient getVariable ["ACME_equipmentKitEpoch",0])}
    && {_medicKit == (_medic getVariable ["ACME_equipmentKitEpoch",0])}
    && {owner _medic == _source} && {_providerPeriod isEqualTo [_source,_locality]}
    && {serverTime <= _deadline}
    && {!(_patient getVariable ["ACME_persistenceFrozen",false])}
    && {!(_medic getVariable ["ACME_persistenceFrozen",false])}
    && {!(_medic getVariable ["ACE_isUnconscious",false])}
    && {([_medic,_patient] call ACME_fnc_patientInteractionDistance) <= 3}
    && {[_medic,_patient] call FUNC(eyeShieldCondition)};
if (_accepted) then {
    if !((_incoming getOrDefault [_id,[]]) isEqualTo _request) exitWith {};
    private _eyes = _patient getVariable [QGVAR(eyeInjuries),[1,1]];
    _accepted = (_eyes select _eyeIndex) < 0.999;
};
if (_accepted) then {
    private _shieldItem = ["kat_eyecovers_right","kat_eyecovers_left"] select _eyeIndex;
    private _existingHmd = hmd _patient;
    if (_existingHmd != "" && {_existingHmd != _shieldItem}) then {
        _patient unlinkItem _existingHmd;
        [_patient,_existingHmd] call ACEFUNC(common,addToInventory);
    };
    _private set [_id,[_request,"applying"]];
    missionNamespace setVariable [QGVAR(shieldDecisions),_private];
    _patient linkItem _shieldItem;
    _accepted = (hmd _patient) == _shieldItem;
    // Unknown native write is held, never converted into a refundable failure.
    if (!_accepted) exitWith {};
    if (_accepted) then {
        _patient setVariable [QGVAR(eyeShieldItem),_shieldItem,true];
        _patient setVariable [QGVAR(eyeShieldIndex),_eyeIndex,true];
        _patient setVariable [QGVAR(eyeShieldAppliedAt),CBA_missionTime,true];
        GVAR(activePatients) pushBackUnique _patient;
    };
};
if ((_private getOrDefault [_id,[]]) isEqualTo [_request,"applying"] && {!_accepted}) exitWith {};
_private set [_id,[_request,_accepted]];
missionNamespace setVariable [QGVAR(shieldDecisions),_private];
_all set [_id,[_request,_accepted]];
_patient setVariable [QGVAR(shieldReceipts),_all,true];
[_accepted] call _reply;
