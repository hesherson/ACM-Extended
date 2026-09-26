// open the iv placement mini-game for a chosen limb and access site.
// call it as [_medic, _patient, _bodyPart, _site] call ACME_fnc_ivMinigameOpen.
// _bodyPart is "leftarm", "rightarm", "leftleg" or "rightleg".
// _site is "upper", "middle" or "lower".
params [["_medic", objNull, [objNull]], ["_patient", objNull, [objNull]], ["_bodyPart", "leftarm", [""]], ["_site", "lower", [""]]];
if (!hasInterface) exitWith {};
if (isNull _patient) exitWith {};

private _data = [_bodyPart, _site] call ACME_fnc_ivSiteData;
if (_data isEqualTo []) exitWith {
    [format ["No IV site mapped for %1 / %2.", _bodyPart, _site], 2, ACE_player] call ace_common_fnc_displayTextStructured;
};

// Close using the OLD context before replacing any UI patient variables.
private _old = uiNamespace getVariable ["ACME_IV_DLG", displayNull];
if (!isNull _old) then {_old closeDisplay 2;};
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
uiNamespace setVariable ["ACME_IV_Session", [_patient, [_patient] call ACME_fnc_clinicalEpoch, _serial]];
uiNamespace setVariable ["ACME_IV_Medic", _medic];
uiNamespace setVariable ["ACME_IV_Patient", _patient];
uiNamespace setVariable ["ACME_IV_BodyPart", toLower _bodyPart];
uiNamespace setVariable ["ACME_IV_Site", toLower _site];
[_patient, "ui:iv:" + str clientOwner, true] call ACME_fnc_ecgJostleRequest;
// This dialog supplies its own return. Suppress ACE's treatment-success reopen and retire the medical-menu PFH
// before replacing the menu. Without this handoff, a stale ACE menu tick can closeDialog the IV panel that was
// just created, which presents as a one-frame flash.
ace_medical_gui_pendingReopen = false;
call ACM_GUI_fnc_pauseMedicalMenuPFH;

// Close the medical menu first, so it is not fighting the dialog. It mirrors the chest-seal open.
private _med = uiNamespace getVariable ["ace_medical_gui_menuDisplay", displayNull];
if (isNull _med) then {_med = findDisplay 38580;};
if (!isNull _med) then {_med closeDisplay 2;};

private _session = +(uiNamespace getVariable ["ACME_IV_Session", []]);
[{
    params ["_session"];

    // A remote casualty can legitimately change clinical generation between callbackStart and this next-frame UI
    // handoff. The old path silently did nothing here, leaving ACE's menu closed and the provider apparently stuck.
    if !([_session] call ACME_fnc_ivUiValid) exitWith {
        private _patient = uiNamespace getVariable ["ACME_IV_Patient", objNull];
        if (!isNull _patient) then {[_patient, "ui:iv:" + str clientOwner, false] call ACME_fnc_ecgJostleRequest;};

        private _return = +(uiNamespace getVariable ["ACME_IV_ReturnMenu", []]);
        uiNamespace setVariable ["ACME_IV_Session", []];
        uiNamespace setVariable ["ACME_minigame_open", false];
        call ACM_GUI_fnc_resumeMedicalMenuPFH;

        // The captured IV session is intentionally omitted here because the generation changed. Restore only the
        // patient's captured page; the user may click the action again against the new generation.
        if (count _return == 3) then {_return call ACME_fnc_reopenMedicalMenu;};
    };

    ["ACME_IVMinigame_Dialog"] call ACME_fnc_minigameOpen;
}, _session] call CBA_fnc_execNextFrame;
