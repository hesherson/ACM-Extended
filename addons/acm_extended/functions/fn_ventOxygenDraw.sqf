/* Real source-owner charge transaction. Public high-water receipts follow source locality.
   Probe reads reserve only; draw debits exactly one 425/283 L unit once. */
params [["_patient",objNull,[objNull]],["_source",objNull,[objNull]],["_session","",[""]],
    ["_sequence",0,[0]],["_kind","",[""]],["_hops",0,[0]]];
if (isNull _patient || {isNull _source} || {_session==""} || {_sequence<1}
    || {!(_kind in ["probe","draw"])}) exitWith {};
if (!local _source) exitWith {
    if (_hops<4) then {["ACME_ventOxygenDraw",[_patient,_source,_session,_sequence,_kind,_hops+1],_source] call CBA_fnc_targetEvent;};
};
private _ledger=_source getVariable ["ACME_vent_o2DrawLedger",createHashMap];
private _receipt=_ledger getOrDefault [_session,[]];
if (count _receipt>0 && {_sequence<=(_receipt select 0)}) exitWith {
    if (_sequence==(_receipt select 0) && {_kind==(_receipt select 1)} && {(_receipt select 4) isEqualTo _patient}) then {
        ["ACME_ownerCommand",[_patient,"ventOxygenAck",[_patient,_source,_session,_sequence,_kind,_receipt select 2,_receipt select 3]],_patient] call CBA_fnc_targetEvent;
    };
};
private _pending=_patient getVariable ["ACME_vent_o2Pending",[]];
if (count _pending!=4 || {(_pending select 0)!=_session} || {(_pending select 1)!=_sequence}
    || {(_pending select 2)!=_kind}
    || {(_patient getVariable ["ACME_vent_o2Session",""])!=_session}
    || {!((_patient getVariable ["ACME_vent_o2Source",objNull]) isEqualTo _source)}
    || {(_patient getVariable ["ACME_vent_o2Epoch",-1])!=([_patient] call ACME_fnc_clinicalEpoch)}
    || {(_patient getVariable ["ACME_vent_o2Custody",""])!=(_patient getVariable ["ACME_vent_custodyId",""])}
    || {!(_patient getVariable ["ACME_vent_onPatient",false])}
    || {!alive _patient}) exitWith {};
private _reserve=[_source] call ACME_fnc_ventOxygenReserve;
private _sourceNear=(_source isEqualTo _patient) || {[_source,_patient] call ACME_fnc_ventRecoveryNear};
private _available=(_reserve select 0) && {_sourceNear};
private _remaining=_reserve select 1;
private _ok=_available;
if (_kind=="probe") then {
    // A last paid charge remains usable even after the full cylinder becomes an empty item.
    if (!_ok && {_sourceNear} && {(_patient getVariable ["ACME_vent_o2Credit",0])>0}
        && {([_source,"ACM_OxygenTank_425_Empty"] call ACME_fnc_itemCount)>0}) then {_ok=true;};
} else {
    _ok=false;
    if (_available) then {
        if (_remaining>0) then {
            // ACM returns false when the last unit empties a cylinder although the debit succeeded.
            // Its owner-local, unscheduled cargo mutation therefore uses the positive pre-draw reserve.
            [_source] call ACM_breathing_fnc_useOxygenTankReserve;
            _remaining=(_remaining-1) max 0;
            _ok=true;
        } else {
            private _left=[_source,"ACM_OxygenTank_425"] call efak_medical_fnc_drawCharge;
            _ok=_left>=0;
            _remaining=_left max 0;
            if (_left==0) then {[_source,"ACM_OxygenTank_425_Empty"] call ace_common_fnc_addToInventory;};
        };
    };
};
// Retired sessions can never authorize another cargo draw. Keep every live/pending
// certificate without allowing repeated reconnects to grow each probe's payload.
{
    private _row=_ledger get _x;
    private _p=_row select 4;
    if (_x!=_session && {isNull _p || {(_p getVariable ["ACME_vent_o2Session",""])!=_x}}) then {_ledger deleteAt _x;};
} forEach keys _ledger;
_ledger set [_session,[_sequence,_kind,_ok,_remaining,_patient]];
_source setVariable ["ACME_vent_o2DrawLedger",_ledger,true];
["ACME_ownerCommand",[_patient,"ventOxygenAck",[_patient,_source,_session,_sequence,_kind,_ok,_remaining]],_patient] call CBA_fnc_targetEvent;
