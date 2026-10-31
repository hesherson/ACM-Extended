/* B121: stop flow without conflating UI state with treatment state. Closing/opening any menu never calls this.
   Explicit Stop Push and AED-leash/access/provider safety failures are the only normal callers. */
params [["_reason","manual",[""]]];
private _job = missionNamespace getVariable ["ACME_HCMedPushJob",createHashMap];
if !(_job isEqualType createHashMap && {count _job > 0}) exitWith {false};
if !(_job getOrDefault ["flowing",false]) exitWith {call ACME_fnc_hardcorePushFinalize};
private _session = _job getOrDefault ["session",""];
private _handler = missionNamespace getVariable ["ACME_HCMedPushPFH",-1];
private _sameJob = {
    private _live = missionNamespace getVariable ["ACME_HCMedPushJob",createHashMap];
    _live isEqualType createHashMap && {count _live > 0}
        && {(_live getOrDefault ["session",""]) == _session}
        && {(missionNamespace getVariable ["ACME_HCMedPushPFH",-1]) == _handler}
};
_job set ["flowing",false];
_job set ["stopReason",_reason];
_job set ["stopRequested",true];
missionNamespace setVariable ["ACME_HCMedPushJob",_job];
uiNamespace setVariable ["ACME_SK_InjectionBusy",true];
uiNamespace setVariable ["ACME_SK_CarouselBusy",true];
// A manual stop happens while the provider is still connected: the amount already moved since the last batch
// is real and is submitted now. A leash/access/provider failure cannot safely submit more medication, so return
// only that unsent tail to the syringe before settlement.
private _submit = _reason == "manual" || {_reason == "complete"};
private _sent = false;
if (_submit) then {_sent = [true] call ACME_fnc_hardcorePushSendBatch;};
// A synchronous local ACK may already have finalized or retired this session.
// Never clear another controller's overlay or finalize its inventory.
if !(call _sameJob) exitWith {true};
_job = missionNamespace getVariable ["ACME_HCMedPushJob",_job];
if (_submit && {!_sent}) then {_job set ["stopReason","batch-not-submitted"];};
private _unsettled = false;
if (!_submit || {!_sent}) then {
    // A batch rejected BEFORE dispatch still belongs to the syringe. Without
    // this fallback a stopped job can retain an unsent tail forever.
    private _delta = +(_job getOrDefault ["unsentDelta",[0,0,[]]]);
    private _ml = (_delta param [0,0]) + (_delta param [1,0]);
    if (_ml > 0) then {
        private _restored = [_job getOrDefault ["medic",objNull],_job getOrDefault ["stableId",""],_delta] call ACME_fnc_hardcorePushRestoreDelta;
        if (!_restored) then {_unsettled = true;} else {
            _job set ["pushedMl",((_job getOrDefault ["pushedMl",0]) - _ml) max 0];
            _job set ["unsentDelta",[0,0,[]]];
            _job set ["batchElapsed",0];
            missionNamespace setVariable ["ACME_HCMedPushJob",_job];
        };
    };
};
if (_unsettled) exitWith {
    [_session,_handler,"unsettled-refund"] call ACME_fnc_hardcorePushRetire;
    false
};
if !(call _sameJob) exitWith {true};
["clear"] call ACME_fnc_hardcorePushOverlay;
call ACME_fnc_hardcorePushFinalize;
true
