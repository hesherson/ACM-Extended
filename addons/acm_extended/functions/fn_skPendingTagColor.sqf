/* B62: select the optional tag for the syringe currently being prepared. Single-click selection is backed by
   both LBSelChanged and MouseButtonUp in fn_skInject, and the row is always cleared for same-color reuse. */
disableSerialization;
params ["_ctrl", "_row"];
if (_row < 0) exitWith {};
private _id = _ctrl lbData _row;
if (_id == "") then {_id = "none";};
uiNamespace setVariable ["ACME_SK_PendingTagColor", _id];
_ctrl lbSetCurSel -1;
_ctrl ctrlShow false;
call ACME_fnc_skPendingTagRender;
// Capture the preparation display now, not whichever dialog exists on the next frame.
// None still invalidates pending focus even though it does not schedule a new request.
private _d = findDisplay 84000;
if (isNull _d) exitWith {};
private _colorEpoch = (_d getVariable ["ACME_SK_PendingTagColorEpoch", 0]) + 1;
_d setVariable ["ACME_SK_PendingTagColorEpoch", _colorEpoch];
if !(_id in ["","none"]) then {
    [{
        disableSerialization;
        params ["_d", "_medic", "_id", "_colorEpoch"];
        if (isNull _d || {!((findDisplay 84000) isEqualTo _d)}
            || {!(ACE_player isEqualTo _medic)}
            || {(uiNamespace getVariable ["ACME_SK_View", "syringe"]) != "syringe"}
            || {(_d getVariable ["ACME_SK_PendingTagColorEpoch", -1]) != _colorEpoch}
            || {(uiNamespace getVariable ["ACME_SK_PendingTagColor", "none"]) != _id}) exitWith {};
        private _focusCtrl = _d displayCtrl 84601;
        if (!isNull _focusCtrl) then {ctrlSetFocus _focusCtrl;};
    },[_d,ACE_player,_id,_colorEpoch],0.01] call CBA_fnc_waitAndExecute;
};
