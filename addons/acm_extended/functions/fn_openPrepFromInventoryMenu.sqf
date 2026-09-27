/* Editing never unspikes the set or consumes its carrier again. */
private _preparedMode = uiNamespace getVariable ["ACME_preparedListMode", false];
if (!_preparedMode) exitWith {
    ["Open Prepared IV sets and select a saline set first.", 2.5, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};

private _pSets = ACE_player getVariable ["ACME_preparedIVSets", []];
private _useIdx = -1;
private _display = findDisplay 86000;
private _setList = if (!isNull _display) then {_display displayCtrl 86145} else {controlNull};
private _row = if (!isNull _setList) then {lbCurSel _setList} else {-1};
private _setId = if (_row >= 0) then {_setList lbData _row} else {""};
if (_setId == "") exitWith {
    ["Select a staged saline set first.", 2.5, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};

_useIdx = _pSets findIf {(_x param [0, ""]) isEqualTo _setId};
if (_useIdx < 0) exitWith {
    uiNamespace setVariable ["ACME_preparedRowSig", "__force__"];
    ["That staged set is no longer available.", 2.5, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};

private _selectedRec = _pSets select _useIdx;
if !(((_selectedRec param [8, "yset"]) isEqualTo "saline")
    && {[_selectedRec param [1, ""], _selectedRec param [2, ""]] call ACME_fnc_isSalineItem}) exitWith {
    ["Only a selected normal saline set can be prepared into an infusion.", 2.5, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};

(_pSets select _useIdx) params [["_sid", ""], ["_itemClass", ""], ["_actionClass", ""]];
if !([_itemClass, _actionClass] call ACME_fnc_isSalineItem) exitWith {
    ["Only saline bags can be prepared with medication.", 2, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};

// the kit checks come before un-staging, so a failed check leaves the staged set exactly where it was.
private _patient = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target",objNull];
private _size = [ACE_player,_patient] call ACME_fnc_findBestSyringe;
if (_size < 0) exitWith {
    ["You need an empty ACM syringe.", 2, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};

private _allowedVials = missionNamespace getVariable ["ACME_infusion_allowedVials", []];
if (_allowedVials isEqualTo []) then {
    _allowedVials = (missionNamespace getVariable ["ACME_infusion_allowedMedications", ["Amiodarone","Epinephrine","Norepinephrine","Lidocaine","Ketamine","TXA","HTS3"]]) apply {[_x] call ACME_fnc_vialClass};
};
private _hasAllowedMedication = false;
{
    private _med = [_x] call ACME_fnc_vialMedication;
    if ((([ACE_player,_patient] call ACME_fnc_treatmentSupplyOrder) findIf {([_x,_med] call ACME_fnc_infusionVialVolume) > 0}) >= 0) exitWith {_hasAllowedMedication = true};
} forEach _allowedVials;

if (!_hasAllowedMedication) exitWith {
    ["You need a supported infusion medication vial, including ketamine or propofol.", 2, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};

// The spiked set remains in custody until attachment succeeds.
private _pending = missionNamespace getVariable ["ACME_preparedPending", createHashMap];
if (((values _pending) findIf {(!(_x select 2)) && {(((_x select 0) select 10) select 0) == _sid}}) >= 0) exitWith {};

private _bodyPart   = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart", ""];
private _selectedIV = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_SelectIV", true];
private _accessSite = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite", -1];
private _inventoryMode = 0;
private _target = ACE_player;
private _vehicle = objectParent ACE_player;

private _volume = [_itemClass, _actionClass] call ACME_fnc_getSalineVolumeFromItem;

ACME_infusion_pendingContext = [
    "prepared",
    _patient,
    _bodyPart,
    -1,
    "Saline",
    "",
    _accessSite,
    _selectedIV,
    -1,
    _volume,
    -1,
    _volume,
    _size,
    _selectedIV,
    _accessSite,
    _itemClass,
    _actionClass,
    _inventoryMode,
    _target,
    _vehicle,
    _sid
];

closeDialog 0;
[ACME_fnc_openDrawMenu, []] call CBA_fnc_execNextFrame;
