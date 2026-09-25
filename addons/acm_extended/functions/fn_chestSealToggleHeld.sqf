// the cric-style chest-seal tray interaction. click the seal icon to pick one up, and click it again while holding
// a seal to return it to the tray. the inventory item is not consumed until the seal is actually placed on the
// body.
disableSerialization;

private _display = uiNamespace getVariable ["ACME_CS_DLG", displayNull];
if (isNull _display) exitWith {};

// clicking the known tray rectangle is also a reliable coordinate calibration point.
private _slotRect = uiNamespace getVariable ["ACME_CS_SlotRect", []];
[_slotRect, true] call ACME_fnc_chestSealMouseCoords;

private _held = uiNamespace getVariable ["ACME_CS_Held", false];
if (_held) exitWith {
    uiNamespace setVariable ["ACME_CS_Held", false];
    uiNamespace setVariable ["ACME_CS_Dragging", false];
    [] call ACME_fnc_chestSealRefreshSlot;
    [] call ACME_fnc_chestSealPrompt;
};

private _medic = uiNamespace getVariable ["ACME_CS_Medic", objNull];
private _patient = uiNamespace getVariable ["ACME_CS_Patient", objNull];
private _count = if (isNull _medic) then {0} else {[_medic, uiNamespace getVariable ["ACME_CS_Patient", objNull], "ACM_ChestSeal"] call ACME_fnc_treatmentSupplyCount};
uiNamespace setVariable ["ACME_CS_SealsLeft", _count];
if (_count <= 0) exitWith {
    [] call ACME_fnc_chestSealRefreshSlot;
    [] call ACME_fnc_chestSealPrompt;
};

if (uiNamespace getVariable ["ACME_CS_SpearHeld", false]) then {
    uiNamespace setVariable ["ACME_CS_SpearHeld", false];
    [] call ACME_fnc_chestSealRefreshSpearSlot;
};

// the peel and open sound. it is kept attached to the provider, so the death of the patient cannot suppress it.
private _now = CBA_missionTime;
private _lastSfx = uiNamespace getVariable ["ACME_CS_lastApplySfx", -1e6];
private _cooldown = missionNamespace getVariable ["ACME_CS_applySfxCooldown", 2.2];
if !(_lastSfx isEqualType 0 && {finite _lastSfx}) then { _lastSfx = -1e6; };
if !(_cooldown isEqualType 0 && {finite _cooldown} && {_cooldown >= 0}) then { _cooldown = 2.2; };
if (_now isEqualType 0 && {finite _now} && {_now - _lastSfx >= _cooldown}) then {
    uiNamespace setVariable ["ACME_CS_lastApplySfx", _now];
    if (!isNull _patient) then { [_patient, _cooldown] call ACME_fnc_markImportantSfx; };
    if (!isNull _medic) then {
        [_medic, "ACM_ChestSeal_Apply"] remoteExec ["ACME_fnc_remoteSay3D", 0];
    } else {
        [] call ACME_fnc_chestSealSnd;
    };
};

uiNamespace setVariable ["ACME_CS_Held", true];
uiNamespace setVariable ["ACME_CS_Dragging", false];
[] call ACME_fnc_chestSealRefreshSlot;
[] call ACME_fnc_chestSealPrompt;
