/* Stable server coordinator for DISCRETE wound edits; physiology still executes on
   the patient owner. No cursor/animation frames pass through this coordinator.
   Each hole has a sealed-field revision: unrelated concurrent edits can commute,
   while stale same-hole edits (including seal/peel/seal ABA) are rejected. */
params ["_patient", "_medic", "_viewer", "_id", "_epoch", "_expected", "_op", "_payload", "_issued", "_replyOwner"];
if (!isServer || {!(_replyOwner isEqualType 0)} || {!finite _replyOwner} || {_replyOwner != floor _replyOwner}) exitWith {};
// Single-player has no network client ID. Its local provider/viewer can legitimately submit zero;
// replies target the viewer object, so accepting this local-only case cannot broadcast an ACK.
private _singlePlayerLocal = !isMultiplayer && {_replyOwner == 0} && {clientOwner == 0}
    && {!isNull _medic} && {local _medic} && {!isNull _viewer} && {local _viewer};
if (_replyOwner < 2 && {!_singlePlayerLocal}) exitWith {};
private _prior = ACME_CS_editResults getOrDefault [_id, []];
if (count _prior > 0) exitWith {
    _prior params ["_at", "_ok", "_message", "_originalPatient", "_originalOwner"];
    if (_replyOwner == _originalOwner && {_patient == _originalPatient}) then {
        ["ACME_CS_ack", [_patient, _id, _ok, _message, _patient getVariable ["ACME_CS_netSnapshot", []]], _viewer] call CBA_fnc_targetEvent;
    };
};
private _ok = false;
private _changed = false;
private _message = "";
private _effect = [];
private _data = [];
private _wasted = [];
private _ncd = [];
private _revisions = createHashMap;
private _editedKey = "";
call {
    if (isNull _patient || {isNull _medic}) exitWith { _message = "Treatment target is no longer available."; };
    // Definitive rejection runs through the existing receipt/refund path. Effects
    // accepted here finish even if a setting changes while forwarding to the owner.
    if (_op in ["ncd", "miss"] && {!([_medic, "ncd"] call ACME_fnc_procedureAllowed)}) exitWith {
        _message = "This procedure is unavailable for this provider.";
    };
    // B72: _issued comes from the requesting client. CBA_missionTime is not a cross-machine authority, so comparing
    // the client's stamp to the dedicated/listen server clock can reject a brand-new rake/reveal request instantly.
    // Freshness/conflict safety is already provided by epoch + snapshot revision + per-hole revision + idempotent ID.
    // Keep only type/finite validation here; never age a client packet against the server's local mission clock.
    if (!(_issued isEqualType 0) || {!finite _issued}) exitWith { _message = "Invalid treatment request; no new change was applied."; };
    private _snapshot = _patient getVariable ["ACME_CS_netSnapshot", []];
    if (count _snapshot < 5 || {_epoch != (_snapshot select 0)}) exitWith { _message = "Patient state was reset. The current chest has been refreshed."; };
    if (!(_expected isEqualType 0) || {_expected > (_snapshot select 1)}) exitWith { _message = "Chest state changed. Please retry on the refreshed wound."; };
    _data = (_snapshot select 2) apply {+_x};
    _wasted = (_snapshot select 3) apply {+_x};
    _ncd = +(_snapshot select 4);
    _revisions = _patient getVariable ["ACME_CS_sealRevisions", createHashMap];
    switch (_op) do {
        case "reveal": {
            if !(_payload isEqualType []) exitWith {};
            {
                private _key = _x;
                private _i = _data findIf {([_x] call ACME_fnc_chestSealKey) isEqualTo _key};
                if (_i >= 0 && {!((_data select _i) select 3)}) then { (_data select _i) set [3, true]; _changed = true; };
            } forEach _payload;
            _ok = true;
        };
        case "seal";
        case "peel": {
            private _i = _data findIf {([_x] call ACME_fnc_chestSealKey) isEqualTo _payload};
            if (_i < 0) exitWith { _message = "That wound is no longer present."; };
            private _hole = _data select _i;
            private _key = str _payload;
            if ((_revisions getOrDefault [_key, 0]) > _expected) exitWith { _message = "Another provider changed this seal. Your view has been refreshed."; };
            private _want = _op == "seal";
            if ((_hole select 4) == _want || {!(_hole select 3)}) exitWith { _message = "That wound has already changed. Your view has been refreshed."; };
            _hole set [4, _want];
            _editedKey = _key;
            _ok = true; _changed = true;
            _effect = [_patient, _medic, _op, [(_data findIf {_x select 4}) >= 0]];
            _message = if (_want) then {"Chest seal applied."} else {"Seal removed. The chest is open again."};
        };
        case "waste";
        case "miss": {
            if !(_payload isEqualType [] && {count _payload == 3}) exitWith {};
            _payload params ["_side", "_x", "_y"];
            if (!(_side in ["front", "back"]) || {!(_x isEqualType 0)} || {!(_y isEqualType 0)} || {!finite _x} || {!finite _y} || {_x < 0} || {_x > 1} || {_y < 0} || {_y > 1}) exitWith {};
            if (_op == "waste") then { _wasted pushBack (+_payload); }
            else {
                _data pushBack [_side, _x, _y, true, false, "\acm_extended\ui\holes\hole1_ca.paa"];
                _effect = [_patient, _medic, "miss", []];
            };
            _ok = true; _changed = true;
        };
        case "ncd": {
            private _side = _payload param [0, ""];
            if !(_side in ["left", "right"]) exitWith {};
            if (_side in _ncd) exitWith { _message = "Another provider has already placed a NAR SPEAR on that side."; };
            _ncd pushBack _side;
            _effect = [_patient, _medic, "ncd", [_side]];
            _ok = true; _changed = true;
            _message = "NAR SPEAR placed.";
        };
        default { _message = "Unsupported chest action."; };
    };
};
if (_ok && {_changed}) then {
    if (_editedKey != "") then {
        _revisions set [_editedKey, (_patient getVariable ["ACME_CS_holeVer", 0]) + 1];
        _patient setVariable ["ACME_CS_sealRevisions", _revisions, false];
    };
    // Legacy readers retain live shared state. No client writes a whole snapshot.
    // _data/_wasted/_ncd are independent copies, not aliases of the comparison values.
    private _legacy = _data apply {_x select [0, 6]};
    if !(_legacy isEqualTo (_patient getVariable ["ACME_CS_holeData", []])) then { _patient setVariable ["ACME_CS_holeData", _legacy, true]; };
    if !(_wasted isEqualTo (_patient getVariable ["ACME_CS_wastedData", []])) then { _patient setVariable ["ACME_CS_wastedData", _wasted, true]; };
    if !(_ncd isEqualTo (_patient getVariable ["ACME_CS_ncdPlacedSides", []])) then { _patient setVariable ["ACME_CS_ncdPlacedSides", _ncd, true]; };
    [_patient, _data] call ACME_fnc_chestSealBumpVer;
};
if (!_ok && {_message == ""}) then { _message = "Invalid chest action; no change was applied."; };
// Record the decision BEFORE effects and acknowledgements; duplicate delivery is inert.
ACME_CS_editResults set [_id, [CBA_missionTime, _ok, _message, _patient, _replyOwner, false]];
if (_ok && {count _effect > 0}) then {
    _effect append [_epoch, _issued, _patient getVariable ["ACME_CS_holeVer", -1]];
    ["ACME_ownerCommand", [_patient, "chestEffect", _effect], _patient] call CBA_fnc_targetEvent;
};
["ACME_CS_ack", [_patient, _id, _ok, _message, _patient getVariable ["ACME_CS_netSnapshot", []]], _viewer] call CBA_fnc_targetEvent;
