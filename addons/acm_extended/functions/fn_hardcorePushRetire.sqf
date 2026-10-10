/* Retire only the captured local controller when its provider can no longer settle it.
 * No dose is delivered/refunded here and no remote inventory is touched. Provider-local plunger state is not
 * an ownership-transfer protocol: retain unsettled evidence for diagnosis until the provider's fresh-kit reset.
 */
params ["_session",["_expectedPFH",-1],["_reason","provider-changed"]];
private _job = missionNamespace getVariable ["ACME_HCMedPushJob",createHashMap];
if !(_job isEqualType createHashMap && {count _job > 0}
    && {_session != ""} && {(_job getOrDefault ["session",""]) == _session}
    && {(missionNamespace getVariable ["ACME_HCMedPushPFH",-1]) == _expectedPFH}) exitWith {false};

private _medic = _job getOrDefault ["medic",objNull];
private _stable = _job getOrDefault ["stableId",""];
private _row = [];
private _escrow = createHashMap;
if (!isNull _medic) then {
    private _store = _medic getVariable ["ACME_narcStore",[]];
    private _index = _store findIf {(_x param [11,"",[""]]) == _stable};
    if (_index >= 0) then {
        _row = +(_store select _index);
        if (count _row > 5) then {_row set [5,(_row select 5) apply {+_x}];};
    };
    // Snapshot the map: a late ACK may remove its live record even though the old plunger job cannot migrate.
    private _liveEscrow = _medic getVariable ["ACME_medicationEscrow",createHashMap];
    {_escrow set [_x,+(_liveEscrow get _x)];} forEach (keys _liveEscrow);
};
_job set ["flowing",false];
_job set ["stopRequested",true];
_job set ["stopReason",_reason];
private _retired = missionNamespace getVariable ["ACME_HCMedPushRetiredJobs",[]];
private _alreadyRetired = (_retired findIf {(_x select 1) == _session}) >= 0;
// Start reserves space by refusing new jobs at 32 records. Never evict an unresolved transaction.
if (!_alreadyRetired && {count _retired < 32}) then {
    _retired pushBack [_medic,_session,_job,_row,_escrow,diag_tickTime,_reason];
    missionNamespace setVariable ["ACME_HCMedPushRetiredJobs",_retired];
    _alreadyRetired = true;
};
if (_expectedPFH >= 0) then {[_expectedPFH] call CBA_fnc_removePerFrameHandler;};
missionNamespace setVariable ["ACME_HCMedPushPFH",-1];
if (_alreadyRetired) then {
    missionNamespace setVariable ["ACME_HCMedPushJob",createHashMap];
} else {
    // Defensive capacity fallback retains the job in place but still stops its worker. Normal Start prevents it.
    missionNamespace setVariable ["ACME_HCMedPushJob",_job];
};
uiNamespace setVariable ["ACME_SK_InjectionBusy",false];
uiNamespace setVariable ["ACME_SK_CarouselBusy",false];
["clear"] call ACME_fnc_hardcorePushOverlay;
if (!isNull (findDisplay 84000)) then {
    private _d = findDisplay 84000;
    {private _c=_d displayCtrl _x; if (!isNull _c) then {_c ctrlEnable true;};} forEach [84150,84151,84154,84470,84831];
    call ACME_fnc_skRefreshDrawn;
    [0] call ACME_fnc_skCarouselRender;
    call ACME_fnc_skBodyActionRender;
};
true
