/* Restore a captured medical page after a minigame unload.
   Existing callers may pass [patient, category]; IV additionally supplies the
   prior body selection and its session. Dropdown choices are restored by the
   renderer's patient cache, never overwritten by a stale snapshot here. */
params [["_patient", objNull, [objNull]], ["_category", "airway", [""]],
    ["_bodyPart", -1, [0]], ["_ivSession", [], [[]]]];
if (!hasInterface || {isNull _patient}) exitWith {};
if ((uiNamespace getVariable ["ACME_minigame_reopen", ""]) != "") exitWith {};
if (missionNamespace getVariable ["ACME_flashlightMenuActive", false]) exitWith {};
private _request = (uiNamespace getVariable ["ACME_medicalReturnSerial", 0]) + 1;
uiNamespace setVariable ["ACME_medicalReturnSerial", _request];
private _lastOpened = missionNamespace getVariable ["ace_medical_gui_lastOpenedOn", -1];
private _displays = +allDisplays;
// ACE openMenu accepts only the patient. Its own onLoad preserves category/body.
// Wait for teardown once; do not restamp later over a selection the user just made.
[{
    params ["_patient", "_category", "_bodyPart", "_ivSession", "_request", "_lastOpened", "_displays"];
    if (isNull _patient || {isNil "ace_medical_gui_fnc_openMenu"}) exitWith {};
    if (_request != (uiNamespace getVariable ["ACME_medicalReturnSerial", -1])) exitWith {};
    if (_ivSession isNotEqualTo [] && {!([_ivSession] call ACME_fnc_ivUiValid)}) exitWith {};
    if ((missionNamespace getVariable ["ace_medical_gui_lastOpenedOn", -1]) != _lastOpened) exitWith {};
    if (dialog || {uiNamespace getVariable ["ACME_minigame_open", false]}) exitWith {};
    if ((uiNamespace getVariable ["ACME_minigame_reopen", ""]) != "") exitWith {};
    if (missionNamespace getVariable ["ACME_flashlightMenuActive", false]) exitWith {};
    if (uiNamespace getVariable ["ace_interact_menu_cursorMenuOpened", false]) exitWith {};
    // This also protects third-party createDisplay menus, which are not dialogs.
    if ((allDisplays findIf {!(_x in _displays)}) >= 0) exitWith {};
    if (!isNil "ace_medical_gui_fnc_canOpenMenu" && {!([call ACME_fnc_controlledProvider, _patient] call ace_medical_gui_fnc_canOpenMenu)}) exitWith {};
    ace_medical_gui_selectedCategory = _category;
    if (_bodyPart >= 0 && {_bodyPart <= 5} && {_bodyPart == floor _bodyPart}) then {
        ace_medical_gui_selectedBodyPart = _bodyPart;
    };
    [_patient] call ace_medical_gui_fnc_openMenu;
}, [_patient, _category, _bodyPart, +_ivSession, _request, _lastOpened, _displays], 0.1] call CBA_fnc_waitAndExecute;
