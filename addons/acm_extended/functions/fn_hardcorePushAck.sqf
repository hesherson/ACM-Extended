/* B121: settlement hook for one incremental push request. Rejected slices go back into the SAME stable syringe,
   never as a duplicate store row. */
params ["_medic",["_meta",[],[[]]],"_accepted",["_reason","",[""]],["_requestId","",[""]]];
if (isNull _medic || {!local _medic} || {(_meta param [0,""]) != "hcPush"}) exitWith {false};
private _session = _meta param [1,"",[""]];
private _stable = _meta param [2,"",[""]];
private _delta = _meta param [3,[]];
if (_session == "" || {_stable == ""}) exitWith {false};
private _job = missionNamespace getVariable ["ACME_HCMedPushJob",createHashMap];
if !(_job isEqualType createHashMap && {count _job > 0} && {(_job getOrDefault ["session",""]) == _session}) exitWith {
    if (_requestId == "") exitWith {false};
    [_medic,_session,_requestId,_meta,_accepted] call ACME_fnc_hardcorePushRecover
};
// Session text alone cannot authorize a refund into another provider or syringe.
if ((_job getOrDefault ["medic",objNull]) isNotEqualTo _medic
    || {(_job getOrDefault ["stableId",""]) != _stable}) exitWith {false};
private _localityEpoch = _job getOrDefault ["providerLocalityEpoch",-1];
private _kit = _medic getVariable ["ACME_equipmentKitEpoch",0];
if ((_localityEpoch >= 0 && {(_medic getVariable ["ACME_providerLocalityEpoch",0]) != _localityEpoch})
    || {(_job getOrDefault ["providerOwner",clientOwner]) != clientOwner}
    || {(_job getOrDefault ["kitEpoch",_kit]) != _kit}) exitWith {
    [_session,missionNamespace getVariable ["ACME_HCMedPushPFH",-1],"provider-epoch-changed"] call ACME_fnc_hardcorePushRetire;
    false
};
if ((_job getOrDefault ["pendingAcks",0]) <= 0) exitWith {false};
// Non-local-validation receipts must still name the exact canonical request.
if (_requestId != "" && {
    private _receipt = (_medic getVariable ["ACME_medicationEscrow",createHashMap]) getOrDefault [_requestId,[]];
    count _receipt < 6 || {(_receipt select 0) isNotEqualTo (_job getOrDefault ["patient",objNull])}
        || {(_receipt param [5,[]]) isNotEqualTo _meta}
}) exitWith {false};
private _restored = true;
private _knownRejected = [];
if (!_accepted) then {
    // Any plunger travel that has not yet been submitted belongs back in the syringe once a prior batch proves
    // the line is no longer valid. Prove both refunds atomically before discarding either piece of evidence.
    private _unsent = _job getOrDefault ["unsentDelta",[0,0,[]]];
    private _combined = [0,0,[]];
    private _valid = true;
    private _store = _medic getVariable ["ACME_narcStore",[]];
    private _at = _store findIf {(_x param [11,"",[""]]) == _stable};
    private _hasParts = _at >= 0 && {count ((_store select _at) param [5,[]]) > 0};
    {
        private _slice = _x;
        if !(_slice isEqualType [] && {count _slice == 3}) exitWith {_valid = false;};
        private _sliceDrug = _slice select 0;
        private _sliceNs = _slice select 1;
        if !(_sliceDrug isEqualType 0 && {finite _sliceDrug} && {_sliceDrug >= 0}
            && {_sliceNs isEqualType 0} && {finite _sliceNs} && {_sliceNs >= 0}
            && {(_slice select 2) isEqualType []}) exitWith {_valid = false;};
        private _seen = []; private _componentMl = 0;
        private _parts = _combined select 2;
        {
            if !(_x isEqualType [] && {count _x == 3}) exitWith {_valid = false;};
            _x params ["_ci","_source","_ml"];
            if !(_ci isEqualType 0 && {finite _ci} && {_ci >= 0}
                && {_ci == floor _ci} && {!(_ci in _seen)}
                && {_source isEqualType ""} && {_source != ""}
                && {_ml isEqualType 0} && {finite _ml} && {_ml >= 0}) exitWith {_valid = false;};
            _seen pushBack _ci; _componentMl = _componentMl + _ml;
            private _partAt = _parts findIf {(_x select 0) == _ci};
            if (_partAt < 0) then {_parts pushBack +_x;} else {
                private _part = +(_parts select _partAt);
                if ((_part select 1) != _source) then {_valid = false;} else {
                    _part set [2,(_part select 2) + _ml]; _parts set [_partAt,_part];
                };
            };
        } forEach (_slice select 2);
        if ((_hasParts || {count (_slice select 2) > 0}) && {abs (_componentMl - (_slice select 0)) > 0.001}) then {_valid = false;};
        _combined set [0,(_combined select 0) + (_slice select 0)];
        _combined set [1,(_combined select 1) + (_slice select 1)];
        _combined set [2,_parts];
    } forEach [_delta,_unsent];
    if (_valid) then {_knownRejected = +_combined;};
    _restored = _valid && {[_medic,_stable,_combined] call ACME_fnc_hardcorePushRestoreDelta};
    if (_restored) then {
        private _ml = (_delta param [0,0]) + (_delta param [1,0]);
        private _unsentMl = (_unsent param [0,0]) + (_unsent param [1,0]);
        _job set ["pushedMl",((_job getOrDefault ["pushedMl",0]) - _ml - _unsentMl) max 0];
        _job set ["unsentDelta",[0,0,[]]];
        _job set ["batchElapsed",0];
    };
    _job set ["flowing",false];
    _job set ["stopRequested",true];
    _job set ["stopReason",format ["rejected:%1",_reason]];
};
if (!_restored) exitWith {
    // medicationAck retains the exact live receipt until this helper succeeds.
    // Retire snapshots it alongside the unchanged count and rejected/unsent volume.
    if (_requestId == "" && {!(_knownRejected isEqualTo [])}) then {
        // Local validation rejected this slice before any patient request existed.
        // It is known unsent evidence, rather than an ACK that can ever arrive.
        _job set ["unsentDelta",_knownRejected];
        _job set ["pendingAcks",((_job getOrDefault ["pendingAcks",1]) - 1) max 0];
    };
    [_session,missionNamespace getVariable ["ACME_HCMedPushPFH",-1],"unsettled-refund"] call ACME_fnc_hardcorePushRetire;
    false
};
_job set ["pendingAcks",((_job getOrDefault ["pendingAcks",1]) - 1) max 0];
missionNamespace setVariable ["ACME_HCMedPushJob",_job];
if (!_accepted) then {["clear"] call ACME_fnc_hardcorePushOverlay;};
if !(_job getOrDefault ["flowing",false]) then {call ACME_fnc_hardcorePushFinalize;};
true
