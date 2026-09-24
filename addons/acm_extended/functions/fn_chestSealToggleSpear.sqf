disableSerialization;
private _display = uiNamespace getVariable ["ACME_CS_DLG", displayNull];
if (isNull _display) exitWith {};

private _slotRect = uiNamespace getVariable ["ACME_CS_SpearSlotRect", []];
[_slotRect, true] call ACME_fnc_chestSealMouseCoords;

private _held = uiNamespace getVariable ["ACME_CS_SpearHeld", false];
if (_held) exitWith {
    uiNamespace setVariable ["ACME_CS_SpearHeld", false];
    uiNamespace setVariable ["ACME_CS_Dragging", false];
    playSound "ACME_NARSPEAR_Close";
    private _cursor = uiNamespace getVariable ["ACME_CS_CursorSpear", controlNull];
    if (!isNull _cursor) then {_cursor ctrlShow false;};
    [] call ACME_fnc_chestSealRefreshSpearSlot;
    [] call ACME_fnc_chestSealPrompt;
};

private _medic = uiNamespace getVariable ["ACME_CS_Medic", objNull];
if !([_medic, "ncd"] call ACME_fnc_procedureAllowed) exitWith {};
private _count = if (isNull _medic) then {0} else {[_medic, "ACME_NARSPEAR"] call ACME_fnc_itemCount};
uiNamespace setVariable ["ACME_CS_SpearsLeft", _count];
if (_count <= 0) exitWith {
    [] call ACME_fnc_chestSealRefreshSpearSlot;
    [] call ACME_fnc_chestSealPrompt;
};

if (uiNamespace getVariable ["ACME_CS_Held", false]) then {
    uiNamespace setVariable ["ACME_CS_Held", false];
    [] call ACME_fnc_chestSealRefreshSlot;
};

uiNamespace setVariable ["ACME_CS_SpearHeld", true];
uiNamespace setVariable ["ACME_CS_Dragging", false];
playSound "ACME_NARSPEAR_Open";

// give immediate cric-style pickup feedback instead of waiting for the next pfh frame. the tray is screen-right of
// the casualty, so the first in-hand texture is the patient's left-side SPEAR.
private _cursor = uiNamespace getVariable ["ACME_CS_CursorSpear", controlNull];
private _bodyRect = uiNamespace getVariable ["ACME_CS_BodyRect", []];
private _mouse = [[], false] call ACME_fnc_chestSealMouseCoords;
if (!isNull _cursor && {_bodyRect isEqualType []} && {count _bodyRect >= 4} && {_mouse isEqualType []} && {count _mouse >= 2}) then {
    _bodyRect params ["_bx", "_by", "_bw", "_bh"];
    _mouse params ["_mx", "_my"];
    if (
        (_bw isEqualType 0) && {finite _bw} && {_bw > 0} &&
        {(_bh isEqualType 0) && {finite _bh} && {_bh > 0}} &&
        {(_mx isEqualType 0) && {finite _mx}} &&
        {(_my isEqualType 0) && {finite _my}}
    ) then {
        _cursor ctrlSetText "\acm_extended\ui\items\nar_spear_left_ca.paa";
        _cursor ctrlSetTextColor [1,1,1,0.50];
        _cursor ctrlSetPosition [_mx - (_bw * 0.4502), _my - (_bh * 0.4971), _bw, _bh];
        _cursor ctrlCommit 0;
        _cursor ctrlShow true;
    };
};

[] call ACME_fnc_chestSealRefreshSpearSlot;
[] call ACME_fnc_chestSealPrompt;
