/* B53 authoritative medication rows for the Narc Box and Prep Infusion.
 *
 * Keep the source path intentionally close to native ACM:
 *   1. ACM builds ACM_circulation_MedicationVialList once from CfgWeapons classes with ACM_isVial > 0.
 *   2. The syringe UI iterates that registry and asks the selected inventory for the count of each vial.
 *
 * ACME only adds the pieces native ACM does not have: exact partial-vial volume, the cardiac-epi alias,
 * infusion allow-list filtering, and the exact physical classname used by the extended vial session ledger.
 *
 * B52's row sorter used _forEachIndex inside apply. _forEachIndex belongs to forEach/forEachReversed, not apply.
 * In Arma that stale index came from the preceding registry loop (for example 67) while _rows only contained
 * about 11 carried medications. The final _raw select then went out of range and returned malformed row data.
 * Do not reintroduce an index-remap sorter here. sort supports same-structure nested string arrays directly.
 *
 * Return row: [displayName, medicationKey, picture, physicalVialClass]
 */
params [["_infusion", false, [false]]];

private _medic = missionNamespace getVariable ["ACM_circulation_SyringeDraw_Medic", objNull];
if (isNull _medic) then {_medic = call ACME_fnc_controlledProvider;};
private _holder = [_medic] call ACME_fnc_vialHolder;
if (isNull _holder) exitWith {[]};

// Native ACM registry first. ACME's immutable snapshot is only a repair source if another script mutates the live list.
private _source = [];
{
    if (_x isEqualType "" && {_x != ""}) then {_source pushBackUnique _x;};
} forEach (missionNamespace getVariable ["ACM_circulation_MedicationVialList", []]);
{
    if (_x isEqualType "" && {_x != ""}) then {_source pushBackUnique _x;};
} forEach (missionNamespace getVariable ["ACME_medicationVialRegistryFull", []]);

// Defensive startup fallback only. Config is finalized before postInit, so this should not be the normal refresh path.
if (_source isEqualTo []) then {
    {
        _source pushBackUnique (configName _x);
    } forEach ("getNumber (_x >> 'ACM_isVial') > 0" configClasses (configFile >> "CfgWeapons"));
};

private _allowedMeds = [];
if (_infusion) then {
    {
        if (_x isEqualType "" && {_x != ""}) then {_allowedMeds pushBackUnique _x;};
    } forEach (missionNamespace getVariable ["ACME_infusion_allowedMedications", []]);
    {
        private _m = [_x] call ACME_fnc_vialMedication;
        if (_m != "") then {_allowedMeds pushBackUnique _m;};
    } forEach (
        +(missionNamespace getVariable ["ACME_infusion_allowedVials", []])
        + (missionNamespace getVariable ["ACME_infusion_syringeExtraDrawItems", []])
    );
};

private _open = _holder getVariable ["ACME_infusion_openVials", createHashMap];
private _rows = [];
private _seenMed = [];

{
    private _class = _x;
    if !(_class isEqualType "") then {continue};

    private _cfg = configFile >> "CfgWeapons" >> _class;
    if !(isClass _cfg) then {continue};
    if ((getNumber (_cfg >> "ACM_isVial")) <= 0) then {continue};

    private _med = [_class] call ACME_fnc_vialMedication;
    if (_med == "" || {_med in _seenMed}) then {continue};
    if (_infusion && {!(_med in _allowedMeds)}) then {continue};

    // This is the same membership decision native ACM ultimately makes: registered vial + positive selected-stock count.
    private _sealed = [_holder, _class] call ACME_fnc_vialItemCount;
    if (_med == "EpinephrineCardiac") then {
        _sealed = ([_holder, "ACME_Vial_EpinephrineCardiac"] call ACME_fnc_vialItemCount)
            + ([_holder, "ACM_Vial_EpinephrineCardiac"] call ACME_fnc_vialItemCount);
    };
    private _openMl = (_open getOrDefault [_med, 0]) max 0;
    if (_sealed <= 0 && {_openMl <= 0.000001}) then {continue};

    private _displayClass = if (_med == "EpinephrineCardiac") then {"ACME_Vial_EpinephrineCardiac"} else {_class};
    private _displayCfg = configFile >> "CfgWeapons" >> _displayClass;
    if !(isClass _displayCfg) then {
        _displayClass = _class;
        _displayCfg = _cfg;
    };

    private _label = getText (_displayCfg >> "displayName");
    if (_label == "") then {_label = getText (_cfg >> "displayName");};
    if (_label == "") then {_label = _med;};

    private _picture = getText (_displayCfg >> "picture");
    if (_picture == "") then {_picture = getText (_cfg >> "picture");};

    _seenMed pushBack _med;
    _rows pushBack [_label, _med, _picture, _displayClass];
} forEach _source;

// An opened partial vial remains selectable after its physical item has been consumed from inventory.
{
    private _med = _x;
    if !(_med isEqualType "") then {continue};
    if (_med in _seenMed) then {continue};

    private _openMl = (_open getOrDefault [_med, 0]) max 0;
    if (_openMl <= 0.000001) then {continue};
    if (_infusion && {!(_med in _allowedMeds)}) then {continue};

    private _displayClass = [_med] call ACME_fnc_vialClass;
    private _cfg = configFile >> "CfgWeapons" >> _displayClass;
    private _label = if (isClass _cfg) then {getText (_cfg >> "displayName")} else {""};
    if (_label == "") then {_label = _med;};
    private _picture = if (isClass _cfg) then {getText (_cfg >> "picture")} else {""};

    _seenMed pushBack _med;
    _rows pushBack [_label, _med, _picture, _displayClass];
} forEach (keys _open);

// Every field is a string and every row has the same four-element shape, which is directly supported by SQF sort.
// The label is element zero, so this preserves deterministic alphabetical presentation without an index remap.
_rows sort true;
_rows
