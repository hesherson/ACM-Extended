/* Owner-local, immutable and bounded import retry. Failed/expired funding stays
 * visibly unresolved; it is never silently replaced by a fresh-zero ledger. */
params ["_holder","_snapshot"];
if (isNull _holder || {!local _holder} || {!([_snapshot] call ACME_fnc_bloodExposureSnapshotValid)}) exitWith {false};
if (isServer) exitWith {
    private _ok = [_holder,_snapshot] call ACME_fnc_bloodExposureRestore;
    _holder setVariable ["ACME_bloodLastRestoreOK",_ok,false];
    _ok
};
private _kit = _holder getVariable ["ACME_equipmentKitEpoch",0];
private _locality = _holder getVariable ["ACME_providerLocalityEpoch",0];
private _past = _holder getVariable ["ACME_bloodRestoreOutbox",[]];
if (_past isNotEqualTo [] && {(_past select 1) != _kit || {(_past select 2) != _locality}}) then {
    if ((_past select 7) >= 0) then {[_past select 7] call CBA_fnc_removePerFrameHandler;};
    _holder setVariable ["ACME_bloodRestoreRetired",_past,false];
    _holder setVariable ["ACME_bloodRestoreOutbox",[],false];
    _past = [];
};
if (_past isNotEqualTo [] && {(_past select 0) isNotEqualTo _snapshot}) exitWith {false};
if (_past isNotEqualTo [] && {(_past select 7) >= 0}) exitWith {true};
private _sequence = 1 + (missionNamespace getVariable ["ACME_bloodRestoreSequence",0]);
missionNamespace setVariable ["ACME_bloodRestoreSequence",_sequence];
private _request = [clientOwner,_sequence];
private _state = [[1,(_snapshot select 1) apply {+_x}],_kit,_locality,clientOwner,_request,-1,diag_tickTime + 30,-1];
_holder setVariable ["ACME_bloodRestoreOutbox",_state,false];
_holder setVariable ["ACME_bloodRestoreUnresolved",[_kit,_locality,_request],true];
_holder setVariable ["ACME_bloodLastRestoreOK",false,false];
private _pfh = [{
    params ["_args","_pfh"];
    _args params ["_holder","_request"];
    if (isNull _holder) exitWith {[_pfh] call CBA_fnc_removePerFrameHandler;};
    private _state = _holder getVariable ["ACME_bloodRestoreOutbox",[]];
    if (_state isEqualTo [] || {(_state select 4) isNotEqualTo _request}) exitWith {[_pfh] call CBA_fnc_removePerFrameHandler;};
    if (!local _holder || {(_state select 1) != (_holder getVariable ["ACME_equipmentKitEpoch",0])}
        || {(_state select 2) != (_holder getVariable ["ACME_providerLocalityEpoch",0])} || {diag_tickTime >= (_state select 6)}) exitWith {
        _state set [7,-1];
        if ((_state select 1) != (_holder getVariable ["ACME_equipmentKitEpoch",0]) || {(_state select 2) != (_holder getVariable ["ACME_providerLocalityEpoch",0])}) then {
            _holder setVariable ["ACME_bloodRestoreRetired",_state,false];
            _holder setVariable ["ACME_bloodRestoreOutbox",[],false];
        } else {_holder setVariable ["ACME_bloodRestoreOutbox",_state,false];};
        [_pfh] call CBA_fnc_removePerFrameHandler;
    };
    if (diag_tickTime - (_state select 5) < 1) exitWith {};
    _state set [5,diag_tickTime]; _holder setVariable ["ACME_bloodRestoreOutbox",_state,false];
    ["ACME_bloodPersistenceImport",[_holder,_state select 0,_state select 1,_state select 2,_state select 3,_request]] call CBA_fnc_serverEvent;
},0.25,[_holder,_request]] call CBA_fnc_addPerFrameHandler;
_state set [7,_pfh]; _holder setVariable ["ACME_bloodRestoreOutbox",_state,false];
true
