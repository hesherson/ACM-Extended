params [["_position", 0.5], ["_silent", false], ["_dropSet", -1], ["_closing", false]];

_position = (_position max 0) min 1;

// keep the dialog visuals coherent no matter what happens with the data side.
uiNamespace setVariable ["ACME_RollerClamp_Position", _position];
[_position] call ACME_fnc_playClampSfx;

private _result = call ACME_fnc_getSelectedInfusionEntryIndexes;
if (_result isEqualTo []) exitWith {
    if (!_silent) then {["Select an active medication saline bag first.", 2, ACE_player, 13] call ace_common_fnc_displayTextStructured;};
    call ACME_fnc_updateClampDialog;
    false
};

_result params ["_patient", "_indexes"];
if (_indexes isEqualTo []) exitWith {
    if (!_silent) then {["Selected saline bag has no medication additive.", 2, ACE_player, 13] call ace_common_fnc_displayTextStructured;};
    call ACME_fnc_updateClampDialog;
    false
};

private _entries = _patient getVariable ["ACME_infusion_BagMedications", []];
private _ids = _indexes apply {(_entries select _x) select 0};
private _bagId = (_entries select (_indexes select 0)) param [23, ""];
private _epoch = [_patient] call ACME_fnc_clinicalEpoch;
private _args = [_patient, _ids, _epoch, _position, _dropSet];
private _display = uiNamespace getVariable ["ACME_RollerClamp_DLG", displayNull];
private _session = uiNamespace getVariable ["ACME_RollerClamp_Session", []];
if (count _session == 4 && {(_session select 0) isNotEqualTo _display
    || {(_session select 1) isNotEqualTo ACE_player}}) exitWith {false};
// Only this display (or its own unload) may create a new input request.
// Preserve the existing endpoint for callers without a clamp session.
private _liveSession = count _session == 4 && {(_session select 0) isEqualTo _display}
    && {(_session select 1) isEqualTo ACE_player} && {(!isNull _display) || {_closing}}
    && {_bagId != ""};
if (_liveSession && {_dropSet < 0}) then {
    _dropSet = uiNamespace getVariable ["ACME_RollerClamp_DropSet", (_entries select (_indexes select 0)) param [20,20]];
};
private _edit = uiNamespace getVariable ["ACME_RollerClamp_Edit",[]];
// A stationary drag and an unchanged final release reuse the in-flight edit.
// Receipt publication must not turn the drag PFH into an idle network sender.
if (_liveSession && {count _edit == 10} && {(_edit select 0) isEqualTo _display}
    && {(_edit select 1) isEqualTo ACE_player} && {(_edit select 2) isEqualTo _patient}
    && {(_edit select 3) == _epoch} && {(_edit select 4) == _bagId}
    && {(_edit select 6) == _position} && {(_edit select 7) == _dropSet}) exitWith {
    call ACME_fnc_updateClampDialog;
    true
};
if (_liveSession) then {
    private _ordinal = _session select 2;
    if ((_session select 3) == 0) then {
        // A restored bag can retain receipts from a previous mission session.
        _ordinal = missionNamespace getVariable ["ACME_RollerClamp_SessionCounter", 0];
        {
            {
                if ((_x param [0,-1]) == clientOwner) then {_ordinal = _ordinal max (_x param [1,0]);};
            } forEach (_x param [28,[]]);
        } forEach _entries;
        _ordinal = _ordinal + 1;
        missionNamespace setVariable ["ACME_RollerClamp_SessionCounter", _ordinal];
    };
    private _sequence = (_session select 3) + 1;
    _session set [2,_ordinal]; _session set [3,_sequence];
    uiNamespace setVariable ["ACME_RollerClamp_Session", _session];
    private _stamp = [clientOwner,_ordinal,_sequence];
    uiNamespace setVariable ["ACME_RollerClamp_Edit", [_display,ACE_player,_patient,_epoch,_bagId,_stamp,_position,_dropSet,false,[]]];
    _args set [4,_dropSet];
    _args pushBack [ACE_player,_stamp,_bagId];
};
[_patient, "infusionClamp", _args] call ACME_fnc_ownerDispatch;

call ACME_fnc_updateTransfusionControls;
call ACME_fnc_updateClampDialog;
true
