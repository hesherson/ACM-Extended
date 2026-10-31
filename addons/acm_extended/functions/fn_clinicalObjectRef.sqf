/* Mission adapters bind their own unique durable IDs before restoring patients.
 * ["bind",object,id] registers on the machine performing the restore and marks
 * the object publicly. A resolver callback ACME_clinicalObjectResolver may
 * instead accept [id] and return an already marked object. No netId is trusted
 * across mission incarnations. Unknown/legacy references deliberately detach. */
params ["_mode", "_value", ["_context", ""]];
private _session = missionNamespace getVariable ["ACME_clinicalPersistenceSession", ""];
if !(_session isEqualType "") then {_session = "";};
if (_mode == "encode") exitWith {
    if (isNull _value) exitWith {["0:0", "", ""]};
    private _stable = _value getVariable ["ACME_persistenceId", ""];
    if !(_stable isEqualType "" && {count _stable <= 256}) then {_stable = "";};
    [netId _value, _session, _stable]
};
if (_mode == "bind") exitWith {
    if (isNull _value || {!(_context isEqualType "")} || {_context == ""} || {count _context > 256}) exitWith {false};
    private _bindings = missionNamespace getVariable ["ACME_clinicalObjectBindings", createHashMap];
    private _other = _bindings getOrDefault [_context, objNull];
    if (!isNull _other && {_other isNotEqualTo _value}) exitWith {false};
    private _previous = _value getVariable ["ACME_persistenceId", ""];
    if (_previous isEqualType "" && {_previous != ""} && {_previous != _context}
        && {(_bindings getOrDefault [_previous, objNull]) isEqualTo _value}) then {_bindings deleteAt _previous;};
    _value setVariable ["ACME_persistenceId", _context, true];
    _bindings set [_context, _value];
    missionNamespace setVariable ["ACME_clinicalObjectBindings", _bindings];
    true
};
if (_mode != "decode") exitWith {objNull};
// A caller may explicitly attest that a legacy netId-only snapshot belongs
// to the current mission. Never infer this from a coincidentally live netId.
private _ref = if (_value isEqualType "") then {[_value, _context, ""]} else {_value};
if !(_ref isEqualType [] && {count _ref == 3}
    && {_ref isEqualTypeAll ""}
    && {count (_ref select 0) <= 128} && {count (_ref select 1) <= 256} && {count (_ref select 2) <= 256}) exitWith {objNull};
_ref params ["_net", "_savedSession", "_stable"];
if (_net in ["", "0:0"] && {_stable == ""}) exitWith {objNull};
private _resolved = objNull;
if (_session != "" && {_savedSession == _session}) then {
    private _live = objectFromNetId _net;
    if (!isNull _live && {_stable == "" || {(_live getVariable ["ACME_persistenceId", ""]) isEqualTo _stable}}) then {_resolved = _live;};
};
if (!isNull _resolved || {_stable == ""}) exitWith {_resolved};
private _bindings = missionNamespace getVariable ["ACME_clinicalObjectBindings", createHashMap];
private _bound = _bindings getOrDefault [_stable, objNull];
if (!isNull _bound && {(_bound getVariable ["ACME_persistenceId", ""]) isNotEqualTo _stable}) then {_bound = objNull;};
private _resolver = missionNamespace getVariable ["ACME_clinicalObjectResolver", {objNull}];
if (_resolver isEqualType {}) then {
    private _candidate = [_stable] call _resolver;
    if (!isNil "_candidate" && {_candidate isEqualType objNull} && {!isNull _candidate}
        && {(_candidate getVariable ["ACME_persistenceId", ""]) isEqualTo _stable}) then {
        if (!isNull _bound && {_candidate isNotEqualTo _bound}) then {_bound = objNull;} else {_bound = _candidate;};
    };
};
_bound
