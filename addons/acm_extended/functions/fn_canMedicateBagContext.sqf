// the central medication-carrier gate. medications may only be added to standard non-y crystalloid and drug
// carriers. never allow medication into blood or fwb, and never allow medication into either limb of a blood
// y-tubing set.
params [["_context", [], [[]]]];
if (_context isEqualTo []) exitWith {false};

_context params [
    ["_patient", objNull],
    ["_bodyPart", ""],
    ["_bagIndex", -1],
    ["_type", ""],
    ["_accessType", 0],
    ["_bagAccessSite", -1],
    ["_bagIV", true],
    ["_bloodType", -1],
    ["_volume", 0],
    ["_freshBloodID", -1],
    ["_remainingVolume", 0]
];

if (_remainingVolume <= 1) exitWith {false};
if (_type in ["Blood", "FreshBlood"]) exitWith {false};
if ([_context] call ACME_fnc_isYLineBagContext) exitWith {false};

// standard saline carriers accept an injected medication. premixed bags, meaning esmolol, HTS, magnesium and
// mannitol, are also valid carriers for their own premixed drug, registered through fn_syncpremixedbags, so they
// must pass this gate too. without this, a premixed type that is not plain saline, such as mannitol, is blocked
// and never registers as a running infusion.
// The dedicated emulsion carrier is admitted for its own registration only.
// infusionRegisterCore enforces Propofol and forbids injecting other solutions.
(_type == "ACME_Propofol") || {(_type in ACME_infusion_allowedBagTypes)} || {(toLowerANSI _type) in keys ACME_infusion_premixedByType}
