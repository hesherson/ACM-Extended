#include "..\script_component.hpp"
/* NA4: native single-cell IV/IO setter, with conservative bag custody on removal.
   The native source's return-volume typo is corrected. A medicated/special bag
   cannot be converted into an unmedicated inventory item without losing its dose
   or donor identity; keep that exact disconnected bag and its ledger instead. */
params ["_medic", "_patient", "_bodyPart", "_type", "_iv", "_accessSite", ["_epoch", -1]];
private _acmeBinding = "NA4:setIVLocal";
if (isNull _patient) exitWith {};
if (!local _patient) exitWith {[QGVAR(setIVLocal), _this, _patient] call CBA_fnc_targetEvent;};
if (_epoch >= 0 && {_epoch != ([_patient] call ACME_fnc_clinicalEpoch)}) exitWith {};
_bodyPart = toLowerANSI _bodyPart;
private _part = ALL_BODY_PARTS find _bodyPart;
if (_part < 0 || {_iv && {!(_accessSite in [0,1,2])}}) exitWith {};
// Every placement/removal changes the physical line. Pending drug belongs to the old line,
// not whichever catheter later occupies the same menu slot. Generic legacy queues are discarded too.
private _generations = _patient getVariable ["ACME_medicationLineGenerations", createHashMap];
private _generationKey = format ["%1:%2",_bodyPart,if (_iv) then {_accessSite} else {-1}];
_generations set [_generationKey,(_generations getOrDefault [_generationKey,0]) + 1];
_patient setVariable ["ACME_medicationLineGenerations",_generations,true];
private _queue = _patient getVariable ["ACME_pendingFlush", []];
private _line = if (_iv) then {_accessSite} else {-1};
private _kept = _queue select {!((toLowerANSI (_x param [0, ""])) == _bodyPart && {(_x param [5, -2]) in [_line, -2]})};
if !(_kept isEqualTo _queue) then {
    private _discard = _patient getVariable ["ACME_medicationDiscarded",createHashMap];
    {if !(_x in _kept) then {_discard set [_x select 1,(_discard getOrDefault [_x select 1,0]) + (_x select 2)];};} forEach _queue;
    _patient setVariable ["ACME_medicationDiscarded",_discard,true];
    _patient setVariable ["ACME_pendingFlush",_kept,true];
};
if (_iv) then {
    private _state = GET_IV(_patient);
    private _row = +(_state select _part);
    _row set [_accessSite, _type];
    _state set [_part, _row];
    _patient setVariable [QGVAR(IV_Placement), _state, true];
} else {
    private _state = GET_IO(_patient);
    _state set [_part, _type];
    _patient setVariable [QGVAR(IO_Placement), _state, true];
};
if (_type != 0) exitWith {};
private _map = _patient getVariable [QGVAR(IV_Bags), createHashMap];
private _bags = _map getOrDefault [_bodyPart, []];
private _keep = [];
private _detached = +(_patient getVariable ["ACME_detachedBags", []]);
private _entries = _patient getVariable ["ACME_infusion_BagMedications", []];
private _doseChanged = false;
private _retained = false;
{
    private _bag = _x;
    _bag params ["_bagType", "_volume", "_accessType", "_site", "_bagIV", "_bloodType"];
    if (_bagIV isNotEqualTo _iv || {_site != _accessSite}) then {_keep pushBack _bag; continue;};
    private _uid = [_patient, _bodyPart, _forEachIndex] call ACME_fnc_bagIdentity;
    // bagIdentity stamps the source bag in place; fetch it to retain the UID.
    _bag = (_map get _bodyPart) select _forEachIndex;
    private _drug = (_entries findIf {(_x param [23, ""]) == _uid}) >= 0;
    private _special = _bagType in ["FreshBlood","FBTK","ACME_SalineY","ACME_Empty","ACME_EmptySaline"];
    private _returnVolume = [_volume] call FUNC(getReturnVolume);
    private _item = if (_returnVolume > 0 && {!_drug} && {!_special}) then {
        [_bagType, _returnVolume, _bloodType] call FUNC(formatFluidBagName)
    } else {""};
    if (_drug || {_special} || {_returnVolume > 0 && {!isClass (configFile >> "CfgWeapons" >> _item)}}) then {
        // Settle ONLY drug already admitted systemically. Remaining bag dose stays
        // in the disconnected bag; it is not administered or discarded on removal.
        {
            if ((_x param [23, ""]) == _uid) then {
                [_patient, _x, true] call ACME_fnc_infusionDeliver;
                _doseChanged = true;
            };
        } forEach _entries;
        _detached pushBackUnique _uid;
        _keep pushBack _bag;
        _retained = true;
    } else {
        if (_returnVolume > 0) then {[_medic, _item] call ACEFUNC(common,addToInventory);};
        _detached = _detached - [_uid];
    };
} forEach _bags;
_map set [_bodyPart, _keep];
[_patient, _map, true] call FUNC(setIVBagsState);
[_patient, "ACME_detachedBags", _detached] call ACME_fnc_setVarNet;
if (_doseChanged) then {[_patient, "ACME_infusion_BagMedications", _entries] call ACME_fnc_setVarNet;};
_patient setVariable [format ["ACME_clampRate_%1_%2_%3", _part, _iv, _accessSite], -1, false];
[_patient, _bodyPart] call FUNC(updateActiveFluidBags);
if (_retained) then {
    [_medic, "Access removed. Identified medication/blood bags remain disconnected at the site; their contents were not discarded."] call ACME_fnc_clinicalNotice;
};
