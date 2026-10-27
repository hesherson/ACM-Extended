/* Edit exactly one certified cooler; an absent continuation safely returns it. */
if (canSuspend) exitWith {private _ok=false; isNil {_ok=_this call ACME_fnc_coolerMutate;}; _ok};
params ["_owner","_sid","_code",["_args",[]],["_completion",[]]];
private _finish={params ["_accepted","_completion"]; if (_completion isNotEqualTo []) then {[_accepted,_completion param [1,[]]] call (_completion select 0);};};
if (isNull _owner || {!local _owner} || {_sid == ""}) exitWith {[false,_completion] call _finish; false};
private _sequence = (missionNamespace getVariable ["ACME_coolerActionSequence",0])+1;
missionNamespace setVariable ["ACME_coolerActionSequence",_sequence];
private _request = format ["cooler-edit:%1:%2:%3",clientOwner,diag_tickTime,_sequence];
private _receipt = [_owner,"cooler",_sid,_request] call ACME_fnc_inventoryLedgerReserve;
if (_receipt isEqualTo []) exitWith {[false,_completion] call _finish; false};
private _intents = _owner getVariable ["ACME_coolerIntents",createHashMap];
_intents set [_request,["mutation",serverTime]];
_owner setVariable ["ACME_coolerIntents",_intents,true];
[_owner,_request,{
    params ["_accepted","_continuation"];
    _continuation params ["_owner","_sid","_request","_code","_args","_completion","_finish"];
    private _held = (_owner getVariable ["ACME_inventoryEscrow",createHashMap]) getOrDefault [_request,[]];
    if (_held isEqualTo []) exitWith {[false,_completion] call _finish;};
    if (!_accepted) exitWith {[_owner,_request,false] call ACME_fnc_inventoryLedgerSettle; [false,_completion] call _finish;};
    private _state = [(_held select 1) select 1,serverTime] call ACME_fnc_coolerAdvance;
    private _result = [_owner,_sid,_state,_args,_request] call _code;
    private _validResult=_result isNotEqualTo [];
    if (_result isEqualTo []) then {_result=[false,_state];};
    _result params ["_consume","_nextState"];
    // Native side effects and their exact resulting state are journaled in this
    // unscheduled pass before waiting for the terminal server acknowledgement.
    private _intents=_owner getVariable ["ACME_coolerIntents",createHashMap];
    _intents set [_request,["mutationResult",serverTime,_consume,[_sid,_nextState]]];
    _owner setVariable ["ACME_coolerIntents",_intents,true];
    private _queued=[_owner,_request,_consume,[_sid,_nextState]] call ACME_fnc_inventoryLedgerSettle;
    [_validResult && {_queued},_completion] call _finish;
},[_owner,_sid,_request,_code,_args,_completion,_finish]] call ACME_fnc_inventoryLedgerClaim;
true
