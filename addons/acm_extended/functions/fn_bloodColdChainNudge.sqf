// Batch changed holders before reconciling, so a hand-off can release before it acquires.
params [["_holder", objNull, [objNull]]];
if (!isServer || {isNull _holder} || {!(_holder isKindOf "CAManBase")}
    || {isRemoteExecuted && {owner _holder != remoteExecutedOwner}}
    || {!(["enabled"] call ACME_fnc_bloodTiming)}) exitWith {};
private _queued = missionNamespace getVariable ["ACME_ccQueuedHolders", []];
_queued pushBackUnique _holder;
missionNamespace setVariable ["ACME_ccQueuedHolders", _queued];
if (missionNamespace getVariable ["ACME_coldChainNudgePending", false]) exitWith {};
ACME_coldChainNudgePending = true;
[{
    private _queued = missionNamespace getVariable ["ACME_ccQueuedHolders", []];
    ACME_ccQueuedHolders = [];
    ACME_coldChainNudgePending = false;
    [0, objNull, _queued] call ACME_fnc_bloodColdChainTick;
}, [], 0.5] call CBA_fnc_waitAndExecute;
