/* Temporary mixing pauses belong to exact patient-owner access/bag episodes.
 * Resume-before-pause closes the request permanently. Manual toggles retire all
 * pauses on that site; cleanup cannot later overwrite a clinician's decision. */
if (canSuspend) exitWith {isNil {_this call ACME_fnc_transfusionMixFlowLocal;};};
params ["_mode","_patient","_medic","_request","_part","_iv","_site","_epoch","_uid","_kit","_locality"];
if (isNull _patient || {!local _patient} || {_request==""}
    || {!(_mode in ["pause","resume","expire"])} || {_epoch!=([_patient] call ACME_fnc_clinicalEpoch)}) exitWith {false};
_part=toLowerANSI _part;
private _pi=ACME_infusion_bodyParts find _part;
if (_pi<0 || {_iv && {!(_site in [0,1,2])}}) exitWith {false};
private _leases=_patient getVariable ["ACME_infusionMixFlowLeases",createHashMap];
// A retired request may be forgotten only after every possible late pause is
// outside admission. Keep active leases, bound short-lived tombstones, and use
// server time rather than a client-local performance clock in the request ID.
private _now = serverTime;
private _parts = _request splitString ":";
private _issued = -1;
private _validRequest = false;
if (count _parts == 4 && {(_parts select 0) == "mix-flow"} && {count _request <= 128}) then {
    private _client = parseNumber (_parts select 1);
    _issued = parseNumber (_parts select 2);
    private _sequence = parseNumber (_parts select 3);
    _validRequest = finite _issued && {_issued >= 0}
        && {finite _client} && {_client >= 0} && {_client == floor _client}
        && {finite _sequence} && {_sequence > 0} && {_sequence == floor _sequence};
};
private _admissible = _validRequest && {_now - _issued <= 10} && {_issued <= _now + 2};
{
    private _old = _leases get _x;
    private _oldIssued = _old param [12, _old param [7, -1]];
    if ((_old param [0, ""]) != "active" && {_oldIssued < 0 || {_now - _oldIssued > 12}}) then {_leases deleteAt _x;};
} forEach keys _leases;
private _lease=_leases getOrDefault [_request,[]];
private _schedule={
    private _args=+_this;_args set [0,"expire"];
    [{params ["_args"];private _patient=_args select 1;if (!isNull _patient) then {[_patient,"transfusionMixFlow",_args] call ACME_fnc_ownerDispatch;};},[_args],30] call CBA_fnc_waitAndExecute;
};
private _write={
    params ["_value"];
    if (_iv) then {
        private _flow=+(_patient getVariable ["ACM_circulation_FluidBagsFlow_IV",[[1,1,1],[1,1,1],[1,1,1],[1,1,1],[1,1,1],[1,1,1]]]);
        private _row=+(_flow select _pi);_row set [_site,_value];_flow set [_pi,_row];
        [_patient,[["fluidBagsFlowIV",_flow]],true] call ACM_circulation_fnc_setRuntimeState;
    } else {
        private _flow=+(_patient getVariable ["ACM_circulation_FluidBagsFlow_IO",[1,1,1,1,1,1]]);
        _flow set [_pi,_value];[_patient,[["fluidBagsFlowIO",_flow]],true] call ACM_circulation_fnc_setRuntimeState;
    };
};
private _flow=if (_iv) then {
    ((_patient getVariable ["ACM_circulation_FluidBagsFlow_IV",[[1,1,1],[1,1,1],[1,1,1],[1,1,1],[1,1,1],[1,1,1]]]) param [_pi,[]]) param [_site,-1]
} else {(_patient getVariable ["ACM_circulation_FluidBagsFlow_IO",[1,1,1,1,1,1]]) param [_pi,-1]};
private _bags=(_patient getVariable ["ACM_circulation_IV_Bags",createHashMap]) getOrDefault [_part,[]];
private _bagCurrent=_uid!="" && {(_bags findIf {(_x param [8,""])==_uid
    && {(_x param [3,-1])==_site} && {(_x param [4,false]) isEqualTo _iv}})>=0};
if (_mode=="pause") exitWith {
    if (_lease isNotEqualTo [] || {!_admissible} || {count _leases >= 128}) exitWith {false};
    // Even rejected input is terminal; a delayed retry cannot become valid in
    // a later ownership period or after another clinician installs a new line.
    _lease=["closed",_medic,_part,_iv,_site,_epoch,_uid,_issued];
    private _identity=[_patient,_part,[_site,-1] select (!_iv)] call ACME_fnc_medicationLineIdentity;
    private _valid=!isNull _medic && {alive _medic} && {!(_medic getVariable ["ACE_isUnconscious",false])}
        && {_medic distance _patient<=5 || {!isNull objectParent _medic && {objectParent _medic isEqualTo objectParent _patient}}}
        && {!(_patient getVariable ["ACME_persistenceFrozen",false])} && {!(_medic getVariable ["ACME_persistenceFrozen",false])}
        && {_kit==(_medic getVariable ["ACME_equipmentKitEpoch",0])}
        && {_locality==(_medic getVariable ["ACME_providerLocalityEpoch",0])}
        && {_bagCurrent} && {_flow>=0} && {_identity isNotEqualTo []};
    if (_valid) then {
        private _oldFlow=_flow;
        {
            private _other=_leases get _x;
            if ((_other select 0)=="active" && {(_other select 2)==_part} && {(_other select 3) isEqualTo _iv}
                && {(_other select 4)==_site} && {(_other select 5)==_epoch}) exitWith {_oldFlow=_other select 7;};
        } forEach keys _leases;
        _lease=["active",_medic,_part,_iv,_site,_epoch,_uid,_oldFlow,_identity,_kit,_locality,owner _medic,_issued];
        if (_flow>0) then {[0] call _write;};
    };
    _leases set [_request,_lease];_patient setVariable ["ACME_infusionMixFlowLeases",_leases,true];
    if (_valid) then {_this call _schedule;};
    _valid
};
if (_lease isEqualTo []) exitWith {
    if (!_admissible || {count _leases >= 128}) exitWith {false};
    _leases set [_request,["closed",_medic,_part,_iv,_site,_epoch,_uid,_issued]];
    _patient setVariable ["ACME_infusionMixFlowLeases",_leases,true];false
};
if ((_lease select 0)!="active" || {(_lease select [1,6]) isNotEqualTo [_medic,_part,_iv,_site,_epoch,_uid]}) exitWith {false};
if (_mode=="expire" && {!isNull _medic} && {alive _medic} && {owner _medic==(_lease select 11)}
    && {_kit==(_medic getVariable ["ACME_equipmentKitEpoch",0])}
    && {_locality==(_medic getVariable ["ACME_providerLocalityEpoch",0])}
    && {(_medic getVariable ["ACME_infusionMixFlowInput",[]]) isEqualTo [_request,_patient,_epoch]}) exitWith {
    _this call _schedule;true
};
_lease set [0,"closed"];_leases set [_request,_lease];_patient setVariable ["ACME_infusionMixFlowLeases",_leases,true];
private _otherActive=((values _leases) findIf {(_x select 0)=="active" && {(_x select 2)==_part}
    && {(_x select 3) isEqualTo _iv} && {(_x select 4)==_site} && {(_x select 5)==_epoch}})>=0;
if (!_otherActive && {_bagCurrent} && {_flow==0} && {(_lease select 7)>0}
    && {(_lease select 8) isEqualTo ([_patient,_part,[_site,-1] select (!_iv)] call ACME_fnc_medicationLineIdentity)}) then {
    [_lease select 7] call _write;
};
true
