private _context = [] call ACME_fnc_getSelectedActiveBagContext;
if (_context isEqualTo []) exitWith {
    ["Select an active normal saline bag first.", 2, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};

_context params ["_patient", "_bodyPart", "_trueIndex", "_type", "_accessType", "_bagAccessSite", "_bagIV", "_bloodType", "_volume", "_freshBloodID", "_remainingVolume", "_selectedIV", "_accessSite"];

private _isYLineBag = [_context] call ACME_fnc_isYLineBagContext;
if ((_type in ["Blood", "FreshBlood"]) || {_isYLineBag}) exitWith {
    ["Do not infuse medications through blood bags or Y-tubing blood/saline lines.", 3, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};

if !(_type in ACME_infusion_allowedBagTypes) exitWith {
    ["Medication can only be infused into a normal saline bag.", 2, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};

if (_remainingVolume <= 1) exitWith {
    ["Selected bag is empty.", 2, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};

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
    ["You need a medication vial suitable for mixing into saline. Spike propofol bottles directly.", 2, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};


// The patient owner pauses only this exact bag/access episode. The menu opens
// immediately; a close that overtakes pause leaves a tombstone at the owner.
call ACME_fnc_restorePausedFlow;
private _flowSequence=1+(missionNamespace getVariable ["ACME_infusionMixFlowSequence",0]);
missionNamespace setVariable ["ACME_infusionMixFlowSequence",_flowSequence];
private _flowRequest=format ["mix-flow:%1:%2:%3",clientOwner,serverTime,_flowSequence];
private _flowArgs=["pause",_patient,ACE_player,_flowRequest,_bodyPart,_bagIV,_bagAccessSite,
    [_patient] call ACME_fnc_clinicalEpoch,[_patient,_bodyPart,_trueIndex] call ACME_fnc_bagIdentity,
    ACE_player getVariable ["ACME_equipmentKitEpoch",0],ACE_player getVariable ["ACME_providerLocalityEpoch",0]];
ACME_infusion_pendingPausedFlow=+_flowArgs;
ACE_player setVariable ["ACME_infusionMixFlowInput",[_flowRequest,_patient,_flowArgs select 7],true];
[_patient,"transfusionMixFlow",_flowArgs] call ACME_fnc_ownerDispatch;

ACME_infusion_pendingContext = [
    "active",
    _patient,
    _bodyPart,
    _trueIndex,
    _type,
    _accessType,
    _bagAccessSite,
    _bagIV,
    _bloodType,
    _volume,
    _freshBloodID,
    _remainingVolume,
    _size,
    _selectedIV,
    _accessSite, "", "", 0, ACE_player, objNull, "",
    [_patient, _bodyPart, _trueIndex] call ACME_fnc_bagIdentity
];

closeDialog 0;
[ACME_fnc_openDrawMenu, []] call CBA_fnc_execNextFrame;
