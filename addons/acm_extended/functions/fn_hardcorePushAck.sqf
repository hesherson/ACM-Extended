/* B121: settlement hook for one incremental push request. Rejected slices go back into the SAME stable syringe,
   never as a duplicate store row. */
params ["_medic",["_meta",[],[[]]],"_accepted",["_reason","",[""]]];
if (isNull _medic || {!local _medic} || {(_meta param [0,""]) != "hcPush"}) exitWith {false};
private _session = _meta param [1,"",[""]];
private _stable = _meta param [2,"",[""]];
private _delta = _meta param [3,[0,0,[]],[[]]];
private _job = missionNamespace getVariable ["ACME_HCMedPushJob",createHashMap];
if !(_job isEqualType createHashMap && {count _job > 0} && {(_job getOrDefault ["session",""]) == _session}) exitWith {false};
private _localityEpoch = _job getOrDefault ["providerLocalityEpoch",-1];
if (_localityEpoch >= 0 && {(_medic getVariable ["ACME_providerLocalityEpoch",0]) != _localityEpoch}) exitWith {
    [_session,missionNamespace getVariable ["ACME_HCMedPushPFH",-1],"provider-epoch-changed"] call ACME_fnc_hardcorePushRetire;
    false
};
_job set ["pendingAcks",((_job getOrDefault ["pendingAcks",1]) - 1) max 0];
if (!_accepted) then {
    [_medic,_stable,_delta] call ACME_fnc_hardcorePushRestoreDelta;
    private _ml = (_delta param [0,0]) + (_delta param [1,0]);
    _job set ["pushedMl",((_job getOrDefault ["pushedMl",0]) - _ml) max 0];
    // Any plunger travel that has not yet been submitted belongs back in the syringe once a prior batch proves
    // the line is no longer valid. Do not leave an unsent tail stranded in a stopped transaction.
    private _unsent = +(_job getOrDefault ["unsentDelta",[0,0,[]]]);
    private _unsentMl = (_unsent param [0,0]) + (_unsent param [1,0]);
    if (_unsentMl > 0) then {
        [_medic,_stable,_unsent] call ACME_fnc_hardcorePushRestoreDelta;
        _job set ["pushedMl",((_job getOrDefault ["pushedMl",0]) - _unsentMl) max 0];
        _job set ["unsentDelta",[0,0,[]]];
        _job set ["batchElapsed",0];
    };
    _job set ["flowing",false];
    _job set ["stopRequested",true];
    _job set ["stopReason",format ["rejected:%1",_reason]];
};
missionNamespace setVariable ["ACME_HCMedPushJob",_job];
if (!_accepted) then {["clear"] call ACME_fnc_hardcorePushOverlay;};
if !(_job getOrDefault ["flowing",false]) then {call ACME_fnc_hardcorePushFinalize;};
true
