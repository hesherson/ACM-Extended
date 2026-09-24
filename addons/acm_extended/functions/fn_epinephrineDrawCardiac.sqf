/* Draw cardiac-strength source into a native syringe; the filled magazine owns its mL.
   The Narc Box injects it via the same native Epinephrine_IV medication path. */
params [["_type", 0]];
private _d = findDisplay 84000;
if (isNull _d) exitWith {};
if (_type != 0) exitWith {["Draw the cardiac syringe, then select a real IV/IO icon on Body Map to administer it.", 3, ACE_player] call ace_common_fnc_displayTextStructured;};
private _size = missionNamespace getVariable ["ACM_circulation_SyringeDraw_Size", 10];
private _ml = (round ((missionNamespace getVariable ["ACM_circulation_SyringeDraw_DrawnAmount", 0]) * 100)) / 100;
if (!(_size in [1,3,5,10]) || {_ml <= 0} || {_ml > _size}) exitWith {};
private _empty = format ["ACM_Syringe_%1", _size];
if (([ACE_player, _empty] call ACME_fnc_itemCount) < 1) exitWith {["An empty syringe is required.", 2, ACE_player] call ace_common_fnc_displayTextStructured;};
if !([ACE_player, _ml] call ACME_fnc_epinephrineTakeSource) exitWith {["Not enough 1:10,000 epinephrine in your kit.", 3, ACE_player] call ace_common_fnc_displayTextStructured;};
if !(missionNamespace getVariable ["ACM_circulation_reusableSyringe", false]) then {[ACE_player, _empty] call ACME_fnc_itemTake;};
private _class = format ["ACM_Syringe_%1_EpinephrineCardiac", _size];
private _result = [ACE_player, _class, "", round (_ml * 100)] call ace_common_fnc_addToInventory;
if !(_result param [0, false]) exitWith {
    [] call ACME_fnc_skWasteEnd;
    ["Cardiac syringe placed on the ground: inventory full. Retrieve it before use.", 4, ACE_player] call ace_common_fnc_displayTextStructured;
};
call ACME_fnc_skPendingTagCommit;
private _autoLabel = format ["Epinephrine 1:10,000: %1 mL = %2 mg (IV/IO)", _ml toFixed 2, (_ml * 0.1) toFixed 3];
private _customName = [_d, false] call ACME_fnc_skFinalName;
private _label = if (_customName == "") then {_autoLabel} else {_customName};
private _store = ACE_player getVariable ["ACME_narcStore", []];
private _entry = [["EpinephrineCardiac", _size, _ml, _label, 0]] call ACME_fnc_skApplyPendingTag;
_store pushBack _entry;
[ACE_player, _store] call ACME_fnc_narcStoreCommit;
[] call ACME_fnc_skWasteEnd;
call ACME_fnc_skRefreshDrawn;
call ACME_fnc_skAfterSaveOpenBody;
[_d, true] call ACME_fnc_skFinalName;
[format ["Drew %1", _label], 3, ACE_player] call ace_common_fnc_displayTextStructured;
