// the narc box body view: inject the selected drawn syringe into the clicked body part, using the current route,
// which is vascular iv or io, or im. _this is [bodypart]. it consumes both the filled syringe magazine, because
// syringe_inject removes the ACM_Syringe_<size>_<med> the draw created, and the matching ACME_narcStore record
// kept here.
params ["_bodyPart", ["_pushSec", 3], ["_confirmedEpiMl", -1, [0]]];
if !(_pushSec isEqualType 0 && {finite _pushSec} && {_pushSec > 0}) then {_pushSec = 3;};
_pushSec = (_pushSec max 1) min 300;
private _display = findDisplay 84000;
if (isNull _display) exitWith {};
private _patient = uiNamespace getVariable ["ACME_SK_Patient", objNull];
if (isNull _patient) then { _patient = ACE_player; };
private _route = uiNamespace getVariable ["ACME_SK_Route", "vascular"];
// which site on that limb was clicked, so the log and the triage card can say where it actually went rather than
// just naming the limb. it uses the same naming helper the body map tooltips use, so they cannot disagree.
private _siteIdx = uiNamespace getVariable ["ACME_SK_SiteIdx", -1];
private _siteName = if (_siteIdx >= 0) then { [_bodyPart, _siteIdx, false] call ACME_fnc_skSiteName } else { "" };
// _bodyPart is the raw internal string, "leftarm", so it must go through ACM's display-name helper or the
// log and the triage card read "leftarm Median Cubital". that is wrong in BOTH registers, not just hardcore.
private _partName = [_bodyPart, "short"] call ACME_fnc_bodyPartName;
private _where = if (_siteName != "") then { format ["%1 %2", _partName, _siteName] } else { _partName };
private _iv = _route != "im";

private _store = [ACE_player] call ACME_fnc_skStoreEnsureIds;
private _storeIdx = [_store] call ACME_fnc_skSelectedIndex;
if (_storeIdx < 0 || {_storeIdx >= count _store}) exitWith {
    ["Choose a prepared syringe in Syringe Menu first.", 2, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};
private _refundRow = +(_store select _storeIdx);
private _refundMags = [];
(_store select _storeIdx) params ["_med", ["_size", 10], ["_amt", 0], ["_lbl", ""], ["_nsMl", 0], ["_components", []]];

if (_iv && {!([_patient, _bodyPart, 0] call ACM_circulation_fnc_hasIV)} && {!([_patient, _bodyPart, 0] call ACM_circulation_fnc_hasIO)}) exitWith {
    ["No IV/IO at that site. Switch Route to IM, or pick a limb with a line.", 2, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};
if (_iv && {[_patient,_bodyPart,_siteIdx] call ACME_fnc_medicationLineBloodBusy}) exitWith {
    ["Blood is present in that line. Finish or remove the blood bag before pushing medication.",3,ACE_player,13] call ace_common_fnc_displayTextStructured;
};

private _virtual = ((_store select _storeIdx) param [6, ""]) in ["compoundB13", "dilutionB13"];

// Source-funded compounds retain each source's actual strength, including both
// epinephrine strengths. Chemical pair/recipe restrictions do not apply.
if (_med == "EpinephrineCardiac" && {!_iv} && {!_virtual}) exitWith {
    ["The cardiac-strength syringe and its diluted pressor are IV/IO only. Use the existing 1:1,000 product for IM.", 4, ACE_player] call ace_common_fnc_displayTextStructured;
};
if (((_store select _storeIdx) param [6, ""]) == "epiMixB12") exitWith {
    private _total = _amt + _nsMl;
    // Normal timed confirmation supplies its captured amount. Legacy direct calls
    // retain the live selector; the measured worker still rejects insufficient solution.
    private _ml = _confirmedEpiMl;
    if (_ml == -1) then {
        private _choice = uiNamespace getVariable ["ACME_SK_EpiDoseChoice", 0];
        _ml = ([1, 2, _total] select _choice) min _total;
    };
    if ([ACE_player, _patient, _bodyPart, _storeIdx, _ml, _siteIdx, _pushSec] call ACME_fnc_epinephrinePushStored) then {
        if (_ml >= _total - 0.001) then {
            [_storeIdx] call ACME_fnc_skAfterStoredRemoval;
        } else {
            uiNamespace setVariable ["ACME_SK_SiteIdx", -1];
            call ACME_fnc_skRefreshDrawn;
            call ACME_fnc_skBuildHotspots;
        };
    };
};
// a compound syringe: deliver the dose of every component, the concentration times ml, in turn, then clear the
// record. each component is pushed as its own medication, so the physiology of both drugs registers, and ketofol
// for instance delivers both effects. Each IV component follows the same selected-line flush rules.
// B13: virtual entries must have been source-funded by the current commit path.
if ((_nsMl > 0 || {!(_components isEqualTo [])}) && {!_virtual}) exitWith {
    ["This older mixture has no verified source-volume record. Discard it and prepare a fresh syringe.", 4, ACE_player] call ace_common_fnc_displayTextStructured;
};
// B13: prevalidate every component before consuming any syringe or sending any event.
if (!(_size isEqualType 0) || {!finite _size} || {!(_size in [1, 3, 5, 10])}
    || {!(_amt isEqualType 0)} || {!finite _amt} || {_amt <= 0}
    || {!(_nsMl isEqualType 0)} || {!finite _nsMl} || {_nsMl < 0}
    || {_amt + _nsMl > _size + 0.001} || {!(_components isEqualType [])}) exitWith {};
private _sourceParts = if (_components isEqualTo []) then {[[_med, _amt]]} else {+_components};
if ((_sourceParts findIf {!(_x isEqualType []) || {count _x != 2} || {!((_x select 0) isEqualType "")}}) >= 0) exitWith {};
private _doses = [];
private _valid = true;
private _componentMl = 0;
{
    _x params ["_source", "_ml"];
    private _class = if (_iv) then {_source + "_IV"} else {_source};
    // Legacy IM stubs have no real dose/effect calibration; use the complete
    // definition while retaining the chosen injection route in delivery metadata.
    if (_virtual && {_source in ["Adenosine", "Amiodarone", "Rocuronium"]}) then {_class = _source + "_IV";};
    // An injectable source without an opposite-route variant still uses its real
    // medication definition; the delivery context supplies the actual route.
    if (_virtual && {!isClass (configFile >> "ACM_Medication" >> "Medications" >> _class)}) then {
        _class = if (isClass (configFile >> "ACM_Medication" >> "Medications" >> _source)) then {_source} else {_source + "_IV"};
    };
    private _conc = getNumber (configFile >> "ACM_Medication" >> "Concentration" >> _source >> "concentration");
    if (!(_ml isEqualType 0) || {!finite _ml} || {_ml <= 0} || {_conc <= 0} || {!([_class, _iv, true, _virtual] call ACME_fnc_medicationRouteAllowed)}) then {_valid = false;} else {
        _doses pushBack [_class, _conc * _ml, _iv, _lbl];
        _componentMl = _componentMl + _ml;
    };
} forEach _sourceParts;
if (abs (_componentMl - _amt) > 0.001) then {_valid = false;};
// B115: use the provider-selected IV/IO push duration for rate-sensitive pharmacology. IM callers retain the
// original 3-second default because the duration box is only exposed after selecting a vascular access site.
{_x pushBack _pushSec; _x pushBack _virtual;} forEach _doses;
if (!_valid) exitWith {
    ["This syringe has an unsupported component or route. Nothing was administered or consumed.", 4, ACE_player] call ace_common_fnc_displayTextStructured;
};
private _selectedPresent = !_iv || {if (_siteIdx >= 0) then {[_patient, _bodyPart, 0, _siteIdx] call ACM_circulation_fnc_hasIV} else {[_patient, _bodyPart, 0] call ACM_circulation_fnc_hasIO}};
if (!_selectedPresent || {ACE_player distance _patient > 5 && {isNull objectParent ACE_player || {objectParent ACE_player != objectParent _patient}}}) exitWith {};
// Compounds are virtual entries whose vial inventory was consumed at commit. Single drugs are physical magazines.
if (!_virtual) then {
    private _magClass = format ["ACM_Syringe_%1_%2", _size, _med];
    private _ammo = round (_amt * 100);
    private _container = objNull;
    {
        if (!isNull _x && {((magazinesAmmoCargo _x) findIf {(_x select 0) == _magClass && {(_x select 1) == _ammo}}) >= 0}) exitWith {_container = _x;};
    } forEach [uniformContainer ACE_player, vestContainer ACE_player, backpackContainer ACE_player];
    if (isNull _container || {_ammo <= 0}) then {_valid = false;} else {
        _container addMagazineAmmoCargo [_magClass, -1, _ammo];
        _refundMags pushBack [_magClass,_ammo];
        // Dose follows the actual magazine quanta, not a stale unrounded UI float.
        (_doses select 0) set [1, getNumber (configFile >> "ACM_Medication" >> "Concentration" >> _med >> "concentration") * (_ammo / 100)];
    };
};
if (!_valid) exitWith {["That exact syringe is no longer in your inventory. Reopen Syringe Menu.", 3, ACE_player] call ace_common_fnc_displayTextStructured;};
_store deleteAt _storeIdx;
[ACE_player, _store] call ACME_fnc_narcStoreCommit;
[ACE_player, _patient, _bodyPart, _doses, "administer", _siteIdx, [_refundMags,[_refundRow],[]]] call ACME_fnc_medicationRequest;
// B18: no transaction-status helper text. The owner acknowledgement/refund path remains fully functional,
// but submission/confirmation is intentionally silent. Providers are expected to use the patient, monitor,
// medication log and their own technique rather than an out-of-band helper popup.
[_storeIdx] call ACME_fnc_skAfterStoredRemoval;
call ACME_fnc_skBuildHotspots;
