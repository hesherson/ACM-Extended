/* B121: stop flow without conflating UI state with treatment state. Closing/opening any menu never calls this.
   Explicit Stop Push and AED-leash/access/provider safety failures are the only normal callers. */
params [["_reason","manual",[""]]];
private _job = missionNamespace getVariable ["ACME_HCMedPushJob",createHashMap];
if !(_job isEqualType createHashMap && {count _job > 0}) exitWith {false};
if !(_job getOrDefault ["flowing",false]) exitWith {call ACME_fnc_hardcorePushFinalize};
_job set ["flowing",false];
_job set ["stopReason",_reason];
_job set ["stopRequested",true];
missionNamespace setVariable ["ACME_HCMedPushJob",_job];
uiNamespace setVariable ["ACME_SK_InjectionBusy",true];
uiNamespace setVariable ["ACME_SK_CarouselBusy",true];
// A manual stop happens while the provider is still connected: the amount already moved since the last batch
// is real and is submitted now. A leash/access/provider failure cannot safely submit more medication, so return
// only that unsent tail to the syringe before settlement.
if (_reason == "manual" || {_reason == "complete"}) then {
    [true] call ACME_fnc_hardcorePushSendBatch;
} else {
    private _delta = +(_job getOrDefault ["unsentDelta",[0,0,[]]]);
    private _ml = (_delta param [0,0]) + (_delta param [1,0]);
    if (_ml > 0) then {
        private _restored = [_job getOrDefault ["medic",objNull],_job getOrDefault ["stableId",""],_delta] call ACME_fnc_hardcorePushRestoreDelta;
        if (!_restored) exitWith {
            [_job getOrDefault ["session",""],missionNamespace getVariable ["ACME_HCMedPushPFH",-1],"unsettled-refund"] call ACME_fnc_hardcorePushRetire;
        };
        _job = missionNamespace getVariable ["ACME_HCMedPushJob",_job];
        _job set ["pushedMl",((_job getOrDefault ["pushedMl",0]) - _ml) max 0];
        _job set ["unsentDelta",[0,0,[]]];
        _job set ["batchElapsed",0];
        missionNamespace setVariable ["ACME_HCMedPushJob",_job];
    };
};
["clear"] call ACME_fnc_hardcorePushOverlay;
call ACME_fnc_hardcorePushFinalize;
true
