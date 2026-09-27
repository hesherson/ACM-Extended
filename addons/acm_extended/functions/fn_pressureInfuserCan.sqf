params ["_context", ["_infusion", false]];
if (count _context < 11) exitWith {false};
_context params ["_patient", "_part", "_index", "_type", "", "_site", "_iv"];
if (isNull _patient || {_index < 0}) exitWith {false};
private _bag = ((_patient getVariable ["ACM_circulation_IV_Bags", createHashMap]) getOrDefault [_part, []]) param [_index, []];
private _id = _bag param [8, ""];
if (_id == "" || {(_bag param [1, 0]) <= 0.5}) exitWith {false};
private _hasDrug = ((_patient getVariable ["ACME_infusion_BagMedications", []]) findIf {(_x param [23, ""]) == _id}) >= 0;
private _eligible = _type in ["Blood", "FreshBlood", "Saline", "Plasma", "PlasmaLyte"] || {(toLowerANSI _type) in keys (missionNamespace getVariable ["ACME_infusion_premixedByType", createHashMap])};
_eligible && {_hasDrug == _infusion} && {(_id in (_patient getVariable ["ACME_piCuffs", createHashMap])) || {([ACE_player, _patient, "ACME_PressureInfuser"] call ACME_fnc_treatmentSupplyCount) > 0}}
