/* Menu-only policy. The original treatment configuration and callbacks stay intact.
   Run once during action collection, not once per rendered frame.
   Return: visible category, stable dropdown/ordering key, hide-from-menu flag. */
params ["_config"];
private _name = toLower (configName _config);
private _category = getText (_config >> "category");
private _lineage = [];
private _base = _config;
while {isClass _base && {count _lineage < 64}} do {
    private _key = toLower (configName _base);
    if (_key in _lineage) exitWith {};
    _lineage pushBack _key;
    _base = inheritsFrom _base;
};
// Hide only ACM's redundant draw-entry actions. The syringe implementation is still used.
if ("usesyringe_10" in _lineage) exitWith {[_category, "", true]};
if (_name == "acme_syringekit_drawpatient") exitWith {["medication", "narc_box", false]};
if (_name in ["acme_removeej", "acme_burpchestseal"]) exitWith {[_category, "", true]};
// Exact actions only. BVM inherits UseStethoscope, so class lineage cannot decide its category: route every
// BVM variant into Breathing before the stethoscope re-category runs.
if (_name in ["usebvm", "usebvm_oxygen", "usebvm_vehicleoxygen", "usebvm_portableoxygen"]) exitWith {["airway", "ventilation", false]};
if (_name in ["checkbreathing", "acme_measurerespirations"]) exitWith {["airway", "ventilation", false]};
if (_name in ["acme_inspectchest", "usestethoscope"]) exitWith {["airway", "ventilation", false]};
if (_name == "slapawake") then {_category = "examine";};
// Dog tags are a standalone final Examine action, never a dropdown child.
if (_name == "checkdogtags") exitWith {["examine", "", false]};
if (_category == "examine") exitWith {
    private _groups = missionNamespace getVariable ["ACME_menuExamineGroups", []];
    if (_groups isEqualTo []) then {_groups = [] call ACME_fnc_menuExamineGroups;};
    private _index = _groups findIf {_name in (_x select 2)};
    private _bucket = "";
    if (_index >= 0) then {_bucket = (_groups select _index) select 0;};
    [_category, _bucket, false]
};
private _iv = (_category == "advanced") && {
    _name in ["acme_removeio_fast1", "acme_removeio_ez"] || {
    (_lineage findIf {_x in [
        "insertiv_16_upper", "removeiv_16_upper", "insertio_fast1", "removeio_fast1",
        "opentransfusionmenu", "bloodiv", "acme_place18g_upper", "acme_ivminigamestart",
        "acme_establishej", "acme_removeej"
    ]}) >= 0 || {
        // Include the legacy 18g declarations and native gauge/site variants.
        (_name find "insertiv_") == 0 || {(_name find "removeiv_") == 0} || {
            (_name find "insertio_") == 0 || {(_name find "removeio_") == 0}
        }
    }}
};
if (_iv) exitWith {["medication", "iv_access", false]};
if (_name in [
    "acme_applychestseal", "acme_performnarspear", "acme_performthoracostomy", "acme_adjustthoracostomy",
    "acme_insertchesttube", "acme_drainfluid_accuvac", "acme_drainfluid_suctionbag",
    "acme_resealchesttube", "acme_closeincision", "acme_suturechesttube"
]) exitWith {["airway", "ventilation", false]};
if (_name in ["recoveryposition", "cancelrecoveryposition"]) exitWith {["airway", "adjuncts", false]};
if (_name in ["checkairway", "headturn", "beginheadtiltchinlift"] || {(_lineage findIf {_x in [
    "usesuctionbag", "drainfluid_accuvac", "acme_drainfluid_accuvac"
]}) >= 0}) exitWith {["airway", "adjuncts", false]};
if (_name in ["acme_attachemma", "acme_removeemma", "acme_attachemmaett", "acme_removeemmaett",
    "acme_attachemmaigel", "acme_removeemmaigel"]) exitWith {["airway", "capno", false]};
// Specific routes must precede Paracetamol: ACM derives its inhalants and lozenge from it.
if ("fentanyllozenge" in _lineage) exitWith {[_category, "route_buc", false]};
if ((_lineage findIf {_x in ["penthrox", "ammoniainhalant", "naloxone"]}) >= 0) exitWith {
    [_category, "route_in", false]
};
if ((_lineage findIf {_x in ["paracetamol", "painkillers"]}) >= 0) exitWith {
    [_category, "route_po", false]
};
[_category, "", false]
