// commit the accumulated compound components to the drawn list, consuming the vials.
// it is shared by the "Save" button, fn_skcompoundsave, which then reopens a fresh syringe, and by the dialog unload
// auto-save, which does not. it does not clear the state or reopen, because the caller decides what happens next.
// it returns true if something was saved.
// call ACME_fnc_skCompoundCommit, which returns a bool.
private _components = uiNamespace getVariable ["ACME_SK_CompoundComponents", []];
if (!(_components isEqualType []) || {_components isEqualTo []}) exitWith {false};

private _cap = uiNamespace getVariable ["ACME_SK_WasteCap", 10];
// B38: all configured vial sources can share a syringe at arbitrary ratios.
// Labels recognize named recipes only; they never grant or deny preparation.
// Each component retains its own source concentration and measured volume.
// Validate capacity and the whole batch before consuming any component.
private _totalDrugMl = 0;
private _valid = _cap isEqualType 0 && {finite _cap} && {_cap in [1, 3, 5, 10]};
{
    if (!(_x isEqualType []) || {count _x != 2} || {!((_x select 0) isEqualType "")} || {(_x select 0) == ""} || {!((_x select 1) isEqualType 0)} || {!finite (_x select 1)} || {(_x select 1) <= 0}) then {_valid = false;} else {_totalDrugMl = _totalDrugMl + (_x select 1);};
} forEach _components;
if (!_valid || {_totalDrugMl > _cap + 0.001}) exitWith {false};
// B25: verify the staged batch against the provider's explicit per-vial selections. The generic source ledger
// can span vials for other preparation systems, but the Narc Box must not auto-roll through identical vials.
private _dlgVial = findDisplay 84000;
private _sessionOK = true;
if (!isNull _dlgVial) then {
    private _needByMed = createHashMap;
    {_x params ["_m","_ml"]; _needByMed set [_m, (_needByMed getOrDefault [_m,0]) + _ml];} forEach _components;
    {if (_y > (["limit", _x, _y, _dlgVial] call ACME_fnc_vialSession) + 0.0005) then {_sessionOK = false;};} forEach _needByMed;
};
if (!_sessionOK) exitWith {false};
private _barrel = format ["ACME_Syringe_%1", _cap];
if !([ACE_player, _components, _barrel, !(missionNamespace getVariable ["ACM_circulation_reusableSyringe", false])] call ACME_fnc_medicationTakeSources) exitWith {
    ["Insufficient source solution or an empty syringe. Nothing was consumed or saved.", 3, ACE_player] call ace_common_fnc_displayTextStructured;
    false
};

// the label and the total drug volume. the compound stores its primary drug, the first component, as the injectable
// class and the total drug ml as the dose, and the full component list and label ride along for display and
// dosing.
private _autoLabel = [_cap, _components, 0] call ACME_fnc_skCompoundLabel;
private _customName = "";
private _label = if (_customName == "") then {_autoLabel} else {_customName};
private _primary = (_components select 0) select 0;


// it stores [med, size, drugml, label, nsml, components].
private _store = ACE_player getVariable ["ACME_narcStore", []];
private _entry = [[_primary, _cap, _totalDrugMl, _label, 0, _components, "compoundB13"]] call ACME_fnc_skApplyPendingTag;
_store pushBack _entry;
[ACE_player, _store] call ACME_fnc_narcStoreCommit;

// A second Save/unload cannot commit the same pending draw twice.
uiNamespace setVariable ["ACME_SK_CompoundComponents", []];
uiNamespace setVariable ["ACME_SK_CompoundVials", []];
private _dlgB25 = findDisplay 84000; if (!isNull _dlgB25) then {["clear", "", 0, _dlgB25] call ACME_fnc_vialSession;};
true
