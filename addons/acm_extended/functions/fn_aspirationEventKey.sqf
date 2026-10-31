/* Immutable episode identity. Native clearing cannot change an explicit emesis receipt.
 * New explicit events carry [id, count, stage, clinical epoch, monotonic serial]. The bounded high-water
 * rejects older events without evicting receipts. Legacy three-field events can only use stable id/count.
 */
params ["_patient", ["_mode","read"], ["_id",""], ["_count",0], ["_stage",2]];
private _epoch = [_patient] call ACME_fnc_clinicalEpoch;
private _state = [_patient] call ACME_fnc_aspirationState;
if (_state isEqualTo []) exitWith {if (_mode == "make") then {[]} else {["",2,false,0]}};
private _event = _patient getVariable ["ACME_laryngo_emesis", []];
if (_mode == "make") exitWith {
    if (isNull _patient || {!local _patient} || {!alive _patient} || {_patient getVariable ["ACME_clinicalRestoring",false]}) exitWith {[]};
    if !(_id isEqualType "" && {_id != ""} && {_count isEqualType 0} && {finite _count} && {_count >= 0}
        && {_stage isEqualType 0} && {finite _stage}) exitWith {[]};
    private _previous = _state select 4;
    if (_event isEqualType [] && {count _event == 5}) then {
        private _n = _event select 4;
        if ((_event select 3) isEqualTo _epoch && {_n isEqualType 0} && {finite _n} && {_n >= 0} && {_n == floor _n}) then {_previous = _previous max _n;};
    };
    private _next = _previous + (1 max ceil (abs _previous * 0.0000002));
    if (!finite _next || {_next <= _previous}) exitWith {[]};
    // A replica which sees emesis first waits for this initial authority packet.
    [_patient,"ACME_aspiration_State",_state] call ACME_fnc_setVarNet;
    [_id,_count,_stage,_epoch,_next]
};
if (_event isEqualType [] && {count _event >= 3}) exitWith {
    _event params ["_eventId","_eventCount","_eventStage"];
    private _validId = _eventId isEqualType "" && {_eventId != ""};
    if (count _event == 3 && {_eventId isEqualType 0} && {finite _eventId}) then {_validId = true;};
    if !(_validId && {_eventCount isEqualType 0} && {finite _eventCount}
        && {_eventCount >= 0} && {_eventStage isEqualType 0} && {finite _eventStage}) exitWith {["",2,false,0]};
    private _serial = 0;
    if (count _event > 3) then {
        if (count _event != 5 || {!((_event select 3) isEqualTo _epoch)}) exitWith {_serial = -1;};
        _serial = _event select 4;
        if !(_serial isEqualType 0 && {finite _serial} && {_serial > 0} && {_serial == floor _serial}) exitWith {_serial = -1;};
        if ((_patient getVariable ["ACME_aspiration_State",[]]) isEqualTo [] || {_serial <= (_state select 4)}) then {_serial = -1;};
    };
    if (_serial < 0) exitWith {["",2,false,0]};
    [format ["explicit:%1:%2:%3",_eventId,_eventCount,_serial],_eventStage,true,_serial]
};
// Native obstruction/grace fields replicate independently and also change during clearing.
// Only a producer receipt establishes a new lung exposure; native-only writes still affect the airway.
["",2,false,0]
