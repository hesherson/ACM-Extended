params [["_requestedId", "", [""]]];
private _display = findDisplay 86000;
if (isNull _display) exitWith {};

private _patient = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target", objNull];
if (isNull _patient) exitWith {};

private _bodyPart = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart", ""];
private _selectedIV = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_SelectIV", true];
private _accessSite = missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite", -1];
if !([_patient,_bodyPart,_selectedIV,_accessSite] call ACME_fnc_transfusionAccessValid) exitWith {
    ["Establish and select an IV/IO access site first.", 2, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};

private _selectedPrepared = call ACME_fnc_getSelectedPreparedInfusion;
_selectedPrepared params ["_preparedIndex", "_prepared"];
if (_requestedId != "") then {
    private _list = ACE_player getVariable ["ACME_infusion_PreparedBags", []];
    _preparedIndex = _list findIf {(_x param [0, ""]) == _requestedId};
    _prepared = if (_preparedIndex >= 0) then {_list select _preparedIndex} else {[]};
};

// backward compatibility: if the custom prepared list is not selected, fall back to the old native inventory-row
// match.
if (_preparedIndex < 0) then {
    private _invContext = call ACME_fnc_getSelectedInventoryBagContext;
    if !(_invContext isEqualTo []) then {
        _invContext params ["_pPatient", "_pBodyPart", "_pSelectedIV", "_pAccessSite", "_pInventoryMode", "_pTarget", "_itemClass", "_actionClass"];
        _preparedIndex = [_itemClass, _actionClass] call ACME_fnc_findPreparedBagIndex;
        if (_preparedIndex >= 0) then {
            _prepared = (ACE_player getVariable ["ACME_infusion_PreparedBags", []]) select _preparedIndex;
        };
    };
};

if (_preparedIndex < 0 || {_prepared isEqualTo []}) exitWith {
    ["Select a prepared infusion first.", 2, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};

_prepared params [
    "_uid",
    "_itemClass",
    ["_actionClass", ""],
    ["_medication", ""],
    ["_doseMg", 0],
    ["_durationSeconds", 600],
    ["_dropSet", ACME_infusion_defaultDropSet],
    ["_dropsPerMinute", 60],
    ["_clampPosition", -1],
    ["_preparedAt", CBA_missionTime],
    ["_volume", -1],
    ["_inventoryMode", missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_Inventory", 0]],
    ["_target", objNull],
    ["_vehicle", objNull]
];
if (_clampPosition > 1) then {_clampPosition = -1};
if (_volume <= 0 && {(_prepared param [15, ""]) == ""}) then {_volume = [_itemClass, _actionClass] call ACME_fnc_getSalineVolumeFromItem};
if (_volume <= 0) exitWith {[ACE_player, "This prepared bag is empty."] call ACME_fnc_clinicalNotice;};
if (isNull _vehicle) then {_vehicle = objectParent ACE_player};
if (isNull _target) then {_target = [ACE_player, _patient, _vehicle] select (_inventoryMode max 0 min 2)};
if (_inventoryMode == 2 && {isNull _vehicle}) exitWith {
    ["Prepared infusion was stored in vehicle inventory, but no vehicle is available.", 2, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};

private _available = 0;
if (_inventoryMode == 2) then {
    private _cargo = getItemCargo _vehicle;
    private _idx = (_cargo select 0) findIf {_x == _itemClass};
    if (_idx >= 0) then {_available = (_cargo select 1) select _idx};
} else {
    _available = [_target, _itemClass] call ACME_fnc_itemCount;
};

private _stagedId = _prepared param [15, ""];
private _isStaged = _stagedId != "";
if (_isStaged) then {_available = if (((ACE_player getVariable ["ACME_preparedIVSets", []]) findIf {(_x select 0) == _stagedId}) >= 0) then {1} else {0};};
if (_available < 1) exitWith {
    ["The prepared saline bag item is no longer available.", 2, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};

private _label = [_prepared] call ACME_fnc_formatPreparedLabel;
private _medName = localize (format ["STR_ACM_Circulation_Medication_%1", _medication]);
if (_medName == "") then {_medName = _medication};
private _doseText = [_medication, _doseMg] call ACME_fnc_formatDose;
private _medic = ACE_player;

if ([_patient, _bodyPart, _selectedIV, _accessSite] call ACME_fnc_isYLineAccess) exitWith {
    ["Do not hang medication infusions through a blood Y-tubing line.", 3, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};

if (!_isStaged) then {
    if (_inventoryMode == 2) then {_vehicle addItemCargoGlobal [_itemClass, -1];} else {[_target, _itemClass] call ACME_fnc_itemTake;};
};

[[_medic, _patient, _target, _itemClass, _actionClass, _vehicle, _bodyPart, _selectedIV, _accessSite, _volume, _prepared, _preparedIndex, _label], {
    [_this] call ACME_fnc_preparedAttachRequest;
}, {
    params ["_medic", "_patient", "_target", "_itemClass", "_actionClass", "_vehicle", "", "", "", "", "_prepared"];
    if ((_prepared param [15, ""]) == "") then {
    if ((_prepared param [11, 0]) == 2) then {
        _vehicle addItemCargoGlobal [_itemClass, 1];
    } else {
        [_target, _itemClass] call ace_common_fnc_addToInventory;
    };
    };
    closeDialog 0;
    [_medic, _patient, missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart", ""]] call ACM_circulation_fnc_openTransfusionMenu;
}, format ["Starting %1", _label], 5] call ACM_core_fnc_progressBarAction;
