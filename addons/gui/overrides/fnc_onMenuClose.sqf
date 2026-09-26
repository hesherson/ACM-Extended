#include "..\script_component.hpp"
/*
 * Generation-safe ACE medical-menu close.
 *
 * The renderer PFH belongs to one concrete display generation. A stale display unload must never clear the PFH,
 * pending-reopen state, blur/background or uiNamespace handle of a newer display which has already replaced it.
 */

private _display = _this param [0, displayNull];

// Release only this display's provider pose ownership. The pose helper is already generation-scoped.
if (!isNull _display && {!isNil "ACME_fnc_menuPoseStop"}) then {
    private _owner = _display getVariable ["ACME_menuPoseOwner", []];
    if (count _owner == 2) then {
        [_owner select 0, false, _owner select 1] call ACME_fnc_menuPoseStop;
    };
};

private _currentDisplay = uiNamespace getVariable [QACEGVAR(medical_gui,menuDisplay), displayNull];
private _closingEpoch = if (isNull _display) then {-1} else {
    _display getVariable ["ACME_medicalMenuPFHEpoch", -1]
};
private _currentEpoch = missionNamespace getVariable ["ACME_medicalMenuPFHEpoch", -1];

// A late onUnload from an old display is expected during fast CPR/BVM/minigame handoffs. It owns nothing in the
// current menu lifecycle. Returning here is the critical invariant: never clear the new display's renderer PFH.
if (isNull _display || {_display isNotEqualTo _currentDisplay} || {_closingEpoch != _currentEpoch}) exitWith {};

if (ACEGVAR(interact_menu,menuBackground) == 1) then {
    [QACEGVAR(medical_gui,id), false] call ACEFUNC(common,blurScreen);
};
if (ACEGVAR(interact_menu,menuBackground) == 2) then {
    (uiNamespace getVariable [QACEGVAR(interact_menu,menuBackground), displayNull]) closeDisplay 0;
};

// This display is the current owner, so native close semantics are now safe.
ACEGVAR(medical_gui,pendingReopen) = false;

private _ownedPFH = _display getVariable ["ACME_medicalMenuPFH", -1];
private _currentPFH = missionNamespace getVariable [QACEGVAR(medical_gui,menuPFH), -1];
if (_ownedPFH isEqualType 0 && {_ownedPFH >= 0} && {_ownedPFH == _currentPFH}) then {
    [_ownedPFH] call CBA_fnc_removePerFrameHandler;
};
ACEGVAR(medical_gui,menuPFH) = -1;
uiNamespace setVariable [QACEGVAR(medical_gui,menuDisplay), displayNull];
