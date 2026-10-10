/* B213: observer-local rate for a finite pressure exit. This never sends animation commands.
 * Atomic public episode + per-receiver record reject late start/stop packets independently of delivery order.
 * A pending start waits for the actual medicEnd; it never accelerates an unrelated animation on receipt.
 */
params ["_medic", "_episode", "_poseEpoch", "_duration", "_active"];
if (isNull _medic || {local _medic} || {!hasInterface}) exitWith {};
_episode params ["_sentAt", "_serial", "_owner"];
if (serverTime - _sentAt > (_duration + 3) || {_sentAt > serverTime + 1}) exitWith {};
private _record = _medic getVariable ["ACME_DP_ExitRemote", []];
// Exit from the function, not the nested comparison scope.
if (_record isNotEqualTo [] && {((_record select 0) select 0) > _sentAt
    || {((_record select 0) select 0) == _sentAt && {((_record select 0) select 1) > _serial}}
    || {(_record select 0) isEqualTo _episode && {!(_record select 1)}}}) exitWith {};
if (!_active && {_record isNotEqualTo []} && {(_record select 0) isEqualTo _episode}) exitWith {
    // Matching stop delegates cleanup to the already-running tagged receiver.
    _record set [1, false];
};
if (_active && {_record isNotEqualTo []} && {(_record select 0) isEqualTo _episode}) exitWith {};
private _inheritedOwnership = _record isNotEqualTo [] && {_record select 3};
private _priorRate = 1;
// No inherited locomotion coefficient: a retired medical exit always releases to 1.
// A newer stop may overtake its start while the preceding observer still owns1.5.
// Carry that ownership into a bounded tombstone cleanup; dropping the old record alone would leak its rate.
_record = [_episode, _active, -1, _inheritedOwnership, _priorRate];
_medic setVariable ["ACME_DP_ExitRemote", _record, false];
private _pfh = [{
    params ["_args", "_pfh"];
    _args params ["_m", "_episode", "_poseEpoch", "_duration"];
    _episode params ["_sentAt", "_serial", "_owner"];
    if (isNull _m) exitWith {[_pfh] call CBA_fnc_removePerFrameHandler;};
    private _record = _m getVariable ["ACME_DP_ExitRemote", []];
    if (_record isEqualTo [] || {!((_record select 0) isEqualTo _episode)}) exitWith {
        [_pfh] call CBA_fnc_removePerFrameHandler;
    };
    private _public = _m getVariable ["ACME_DP_ExitEpisode", []];
    private _known = count _public >= 4 && {(_public select [0,3]) isEqualTo _episode};
    private _newer = count _public >= 4 && {!_known} && {(_public select 0) >= _sentAt};
    private _poseChanged = (_m getVariable ["ACME_treatmentPoseEpoch", 0]) != _poseEpoch;
    private _transferred = local _m || {isServer && {owner _m != _owner}};
    private _current = toLowerANSI animationState _m;
    private _inExit = _current == "ainvpknlmstpsnonwnondnon_medicend";
    private _expired = serverTime - _sentAt > _duration + 2;
    private _inactive = !(_record select 1) || {_known && {!(_public select 3)}};
    private _unavailable = !alive _m || {_m getVariable ["ACE_isUnconscious", false]} || {!isNull objectParent _m};
    private _left = (_record select 3) && {!_inExit};
    // Public state can overtake both packets for the next exit. Keep the old ownership token passively until
    // its new receiver inherits it, or visible movement permits cleanup. Never reassert rate for that successor.
    private _publicExpired = _newer && {serverTime - (_public select 0) > _duration + 2};
    if (_newer && {_record select 3} && {!_poseChanged} && {!_transferred} && {!_unavailable}
        && {_inExit} && {!_publicExpired}) exitWith {};
    if (_newer || {_poseChanged} || {_transferred} || {_expired} || {_inactive} || {_unavailable} || {_left}) exitWith {
        _record set [1, false];
        [_pfh] call CBA_fnc_removePerFrameHandler;
        // Restore the exact tagged rate even when the next state is armed locomotion.
        // A newer explicit rate/freeze owner wins; never restore a captured acceleration.
        if ((_record select 3) && {!_newer || {!_inExit} || {_publicExpired} || {_transferred} || {_unavailable}} && {!([_m] call ACME_fnc_providerAnimSpeedOwned)}
            && {abs ((getAnimSpeedCoef _m) - 1.5) < 0.01}) then {
            _m setAnimSpeedCoef 1;
        };
        _record set [3, false];
    };
    // Unknown public state is pending replication, not authorization to touch the provider yet.
    if (_known && {_inExit} && {!([_m] call ACME_fnc_providerAnimSpeedOwned)}) then {
        _record set [3, true];
        if (abs ((getAnimSpeedCoef _m) - 1.5) > 0.01) then {_m setAnimSpeedCoef 1.5;};
    };
}, 0, [_medic, _episode, _poseEpoch, _duration]] call CBA_fnc_addPerFrameHandler;

_record set [2, _pfh];
