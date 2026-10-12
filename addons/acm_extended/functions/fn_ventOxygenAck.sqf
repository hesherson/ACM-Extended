/* Only the source's committed receipt can grant prepaid gas; duplicate ACK cannot grant twice. */
params [["_patient",objNull,[objNull]],["_source",objNull,[objNull]],["_session","",[""]],
    ["_sequence",0,[0]],["_kind","",[""]],["_ok",false,[false]],["_remaining",0,[0]]];
if (isNull _patient || {!local _patient} || {isNull _source}) exitWith {};
private _pending=_patient getVariable ["ACME_vent_o2Pending",[]];
if (count _pending!=4 || {(_pending select 0)!=_session} || {(_pending select 1)!=_sequence}
    || {(_pending select 2)!=_kind} || {(_patient getVariable ["ACME_vent_o2Session",""])!=_session}
    || {!((_patient getVariable ["ACME_vent_o2Source",objNull]) isEqualTo _source)}
    || {(_patient getVariable ["ACME_vent_o2Epoch",-1])!=([_patient] call ACME_fnc_clinicalEpoch)}
    || {(_patient getVariable ["ACME_vent_o2Custody",""])!=(_patient getVariable ["ACME_vent_custodyId",""])}) exitWith {};
private _receipt=(_source getVariable ["ACME_vent_o2DrawLedger",createHashMap]) getOrDefault [_session,[]];
if !(count _receipt==5 && {(_receipt select 0)==_sequence} && {(_receipt select 1)==_kind}
    && {(_receipt select 2) isEqualTo _ok} && {(_receipt select 3)==_remaining}
    && {(_receipt select 4) isEqualTo _patient}) exitWith {};
if (_ok && {_kind=="draw"}) then {
    _patient setVariable ["ACME_vent_o2Credit",(_patient getVariable ["ACME_vent_o2Credit",0])+(425/283),true];
};
_patient setVariable ["ACME_vent_o2ReserveUnits",_remaining,true];
_patient setVariable ["ACME_vent_o2Pending",[],true];
_patient setVariable ["ACME_vent_o2VerifiedUntil",if (_ok) then {serverTime+3} else {-1},true];
_patient setVariable ["ACME_vent_o2NextProbe",serverTime+1,false];
_patient setVariable ["ACME_vent_o2Status",if (_ok) then {"READY"} else {if (_remaining==0) then {"EMPTY"} else {"UNAVAILABLE"}},true];
