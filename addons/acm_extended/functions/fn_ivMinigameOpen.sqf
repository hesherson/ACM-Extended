// open the iv placement mini-game for a chosen limb and access site.
// call it as [_medic, _patient, _bodyPart, _site] call ACME_fnc_ivMinigameOpen.
// _bodyPart is "leftarm", "rightarm", "leftleg" or "rightleg".
// _site is "upper", "middle" or "lower".
params [["_medic", objNull, [objNull]], ["_patient", objNull, [objNull]], ["_bodyPart", "leftarm", [""]], ["_site", "lower", [""]]];
if (!hasInterface) exitWith {};
if (isNull _patient || {isNull _medic} || {_medic isNotEqualTo (call ACME_fnc_controlledProvider)}
    || {!local _medic} || {!alive _medic} || {_medic getVariable ["ACE_isUnconscious", false]}) exitWith {};

private _data = [_bodyPart, _site] call ACME_fnc_ivSiteData;
if (_data isEqualTo []) exitWith {
    [format ["No IV site mapped for %1 / %2.", _bodyPart, _site], 2, _medic] call ace_common_fnc_displayTextStructured;
};

// Close using the OLD context before replacing any UI patient variables.
private _old = uiNamespace getVariable ["ACME_IV_DLG", displayNull];
if (!isNull _old) then {
    // Retire controls/PFH while their global context still belongs to this
    // concrete display; a delayed native Unload must not see the new context.
    [_old] call ACME_fnc_ivMinigameClose;
    _old closeDisplay 2;
};
// A second launch can arrive before the first display has an onUnload handler.
// Retire that exact pending launch before publishing the replacement context.
private _pending = uiNamespace getVariable ["ACME_IV_PendingLaunch", []];
if (_pending isNotEqualTo []) then {[displayNull, _pending, false] call ACME_fnc_ivMinigameClose;};
// Only the patient and page captured for this launch may become the return page.
// A scripted/interaction-menu launch has no previous page, so use its own body part.
private _launchPart = if ((toLower _bodyPart) == "ej") then {"head"} else {toLower _bodyPart};
private _selection = ["head", "body", "leftarm", "rightarm", "leftleg", "rightleg"] find _launchPart;
if (_selection < 0) then {_selection = 0;};
private _return = [_patient, "medication", _selection];
private _prepared = uiNamespace getVariable ["ACME_IV_PreparedMenu", []];
uiNamespace setVariable ["ACME_IV_PreparedMenu", []];
if (count _prepared == 6 && {(_prepared select 0) isEqualTo _medic}
    && {(_prepared select 1) isEqualTo _patient} && {(_prepared select 2) isEqualTo _launchPart}
    && {(_prepared select 4) == ([_patient] call ACME_fnc_clinicalEpoch)}
    && {CBA_missionTime - (_prepared select 5) >= 0} && {CBA_missionTime - (_prepared select 5) <= 5}) then {
    _return = +(_prepared select 3);
} else {
    private _menu = uiNamespace getVariable ["ace_medical_gui_menuDisplay", displayNull];
    if (!isNull _menu && {(missionNamespace getVariable ["ace_medical_gui_target", objNull]) isEqualTo _patient}) then {
        _return = [_patient, missionNamespace getVariable ["ace_medical_gui_selectedCategory", "medication"],
            missionNamespace getVariable ["ace_medical_gui_selectedBodyPart", _selection]];
    };
};
uiNamespace setVariable ["ACME_IV_ReturnMenu", _return];
uiNamespace setVariable ["ACME_medicalReturnSerial", (uiNamespace getVariable ["ACME_medicalReturnSerial", 0]) + 1];
private _serial = (uiNamespace getVariable ["ACME_IV_Serial", 0]) + 1;
uiNamespace setVariable ["ACME_IV_Serial", _serial];
private _session = [_patient, [_patient] call ACME_fnc_clinicalEpoch, _serial];
uiNamespace setVariable ["ACME_IV_Session", _session];
uiNamespace setVariable ["ACME_IV_Medic", _medic];
uiNamespace setVariable ["ACME_IV_Patient", _patient];
uiNamespace setVariable ["ACME_IV_BodyPart", toLower _bodyPart];
uiNamespace setVariable ["ACME_IV_Site", toLower _site];
// Independent keys keep a delayed release from an earlier launch from clearing
// a replacement launch's monitor-motion lease on the same patient.
private _ecgKey = "ui:iv:" + str clientOwner + ":" + str _serial;
uiNamespace setVariable ["ACME_IV_ECGKey", _ecgKey];
[_patient, _ecgKey, true] call ACME_fnc_ecgJostleRequest;
// This dialog supplies its own return. Suppress ACE's treatment-success reopen.
ace_medical_gui_pendingReopen = false;

// close the medical menu first, so it is not fighting the dialog. it mirrors the chest-seal open.
private _med = findDisplay 38580;
if (!isNull _med) then { _med closeDisplay 2; };
private _launch = [+_session, _medic, +_return,
    uiNamespace getVariable ["ACME_medicalMenuRendererEpoch", 0],
    missionNamespace getVariable ["ace_medical_gui_lastOpenedOn", -1], +allDisplays,
    uiNamespace getVariable ["ACME_medicalReturnSerial", 0], _ecgKey];
uiNamespace setVariable ["ACME_IV_PendingLaunch", _launch];
private _mayOpen = {
    params ["_launch"];
    if (_launch isNotEqualTo (uiNamespace getVariable ["ACME_IV_PendingLaunch", []])) exitWith {false};
    _launch params ["_session", "_medic", "_return", "_medicalEpoch", "_lastOpened", "_displays", "_returnSerial"];
    private _ownsUI = (uiNamespace getVariable ["ACME_medicalMenuRendererEpoch", 0]) == _medicalEpoch
        && {(missionNamespace getVariable ["ace_medical_gui_lastOpenedOn", -1]) == _lastOpened}
        && {(uiNamespace getVariable ["ACME_medicalReturnSerial", 0]) == _returnSerial}
        && {(allDisplays findIf {!(_x in _displays)}) < 0}
        && {!(uiNamespace getVariable ["ACME_minigame_open", false])}
        && {(uiNamespace getVariable ["ACME_minigame_reopen", ""]) == ""}
        && {!(missionNamespace getVariable ["ACME_flashlightMenuActive", false])};
    if (!_ownsUI || {!([_session] call ACME_fnc_ivUiValid)} || {isNull _medic}
        || {_medic isNotEqualTo (call ACME_fnc_controlledProvider)} || {!local _medic} || {!alive _medic}
        || {_medic getVariable ["ACE_isUnconscious", false]}) exitWith {
        [displayNull, _launch, _ownsUI] call ACME_fnc_ivMinigameClose;
        false
    };
    true
};
[{
    params ["_launch", "_mayOpen"];
    if ([_launch] call _mayOpen) then {
        ["ACME_IVMinigame_Dialog", _mayOpen, [_launch], {
            params ["_opened", "_args"];
            if (!_opened) then {[displayNull, _args select 0, true] call ACME_fnc_ivMinigameClose;};
        }] call ACME_fnc_minigameOpen;
    };
}, [_launch, _mayOpen]] call CBA_fnc_execNextFrame;
