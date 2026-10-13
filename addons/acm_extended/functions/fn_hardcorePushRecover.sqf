/* Settle a stopped push after a local controlled-unit switch. Never resume flow.
 * The archive is evidence from this machine, not a provider ownership handoff.
 * A missing ACK remains unresolved; only its exact receipt can restore a rejected
 * aliquot. The unsent tail is known not to have reached medicationRequest.
 */
if (canSuspend) exitWith {private _result = false; isNil {_result = _this call ACME_fnc_hardcorePushRecover;}; _result};
params ["_medic",["_session","",[""]],["_requestId","",[""]],["_meta",[],[[]]],["_accepted",false,[false]]];
if (isNull _medic || {!local _medic}) exitWith {false};
private _retired = missionNamespace getVariable ["ACME_HCMedPushRetiredJobs",[]];
private _progress = false;
private _kept = [];
{
    private _entry = +_x;
    if (count _entry < 7 || {(_entry select 0) isNotEqualTo _medic}
        || {_session != "" && {(_entry select 1) != _session}}) then {_kept pushBack _entry; continue;};
    private _job = _entry select 2;
    private _receipts = _entry select 4;
    if !(_job isEqualType createHashMap && {_receipts isEqualType createHashMap}) then {_kept pushBack _entry; continue;};
    private _sid = _job getOrDefault ["stableId",""];
    private _epoch = _job getOrDefault ["providerLocalityEpoch",-1];
    private _kit = _job getOrDefault ["kitEpoch",-1];
    if (_sid == "" || {_epoch < 0} || {_kit < 0}
        || {_epoch != (_medic getVariable ["ACME_providerLocalityEpoch",0])}
        || {_kit != (_medic getVariable ["ACME_equipmentKitEpoch",0])}
        || {(_job getOrDefault ["providerOwner",-1]) != clientOwner}
        || {_job getOrDefault ["flowing",false]}) then {_kept pushBack _entry; continue;};
    private _store = _medic getVariable ["ACME_narcStore",[]];
    private _at = _store findIf {(_x param [11,"",[""]]) == _sid};
    // A new kit or another editor must not receive medication from this archive.
    if (_at < 0 || {(_store select _at) isNotEqualTo (_entry select 3)}) then {_kept pushBack _entry; continue;};
    private _ownedIds = (keys _receipts) select {
        private _receiptMeta = (_receipts get _x) param [5,[]];
        (_receiptMeta param [0,""]) == "hcPush" && {(_receiptMeta param [1,""]) == (_entry select 1)}
            && {(_receiptMeta param [2,""]) == _sid}
    };
    if (count _ownedIds != (_job getOrDefault ["pendingAcks",0])) then {_kept pushBack _entry; continue;};
    if (_requestId != "" && {!(_requestId in _ownedIds)
        || {((_receipts get _requestId) param [5,[]]) isNotEqualTo _meta}}) then {_kept pushBack _entry; continue;};
    private _tail = +(_job getOrDefault ["unsentDelta",[0,0,[]]]);
    private _tailMl = (_tail param [0,0]) + (_tail param [1,0]);
    if (_tailMl > 0.000001) then {
        if !([_medic,_sid,_tail] call ACME_fnc_hardcorePushRestoreDelta) then {_kept pushBack _entry; continue;};
        _job set ["unsentDelta",[0,0,[]]];
        _job set ["batchElapsed",0];
        _job set ["pushedMl",((_job getOrDefault ["pushedMl",0]) - _tailMl) max 0];
        _progress = true;
    };
    if (_requestId != "") then {
        // Consume the captured receipt before any store writer can re-enter.
        _receipts deleteAt _requestId;
        _job set ["pendingAcks",((_job getOrDefault ["pendingAcks",1]) - 1) max 0];
        if (!_accepted) then {
            private _delta = _meta param [3,[0,0,[]],[[]]];
            [_medic,_sid,_delta] call ACME_fnc_hardcorePushRestoreDelta;
            private _ml = (_delta param [0,0]) + (_delta param [1,0]);
            _job set ["pushedMl",((_job getOrDefault ["pushedMl",0]) - _ml) max 0];
        };
        _progress = true;
    };
    _store = _medic getVariable ["ACME_narcStore",[]];
    _at = _store findIf {(_x param [11,"",[""]]) == _sid};
    if (_at >= 0) then {_entry set [3,+(_store select _at)];};
    _entry set [2,_job]; _entry set [4,_receipts];
    if ((_job getOrDefault ["pendingAcks",0]) == 0 && {[_job] call ACME_fnc_hardcorePushFinalize}) then {
        _progress = true;
    } else {_kept pushBack _entry;};
} forEach _retired;
missionNamespace setVariable ["ACME_HCMedPushRetiredJobs",_kept];
_progress
