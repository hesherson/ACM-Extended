private _context = [] call ACME_fnc_getSelectedActiveBagContext;
if (_context isEqualTo []) exitWith {
    ["Select an active saline or blood line first.", 2, ACE_player, 13] call ace_common_fnc_displayTextStructured;
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
    ["You need a supported infusion medication vial, including ketamine or propofol.", 2, ACE_player, 13] call ace_common_fnc_displayTextStructured;
};


private _partIndex = ACME_infusion_bodyParts find toLowerANSI _bodyPart;
private _oldFlow = -1;
if (_partIndex >= 0) then {
    if (_bagIV) then {
        private _flowArray = +( _patient getVariable ["ACM_circulation_FluidBagsFlow_IV", [[1,1,1],[1,1,1],[1,1,1],[1,1,1],[1,1,1],[1,1,1]]] );
        if (_partIndex < count _flowArray) then {
            private _partFlow = +(_flowArray select _partIndex);
            if (_bagAccessSite >= 0 && {_bagAccessSite < count _partFlow}) then {
                _oldFlow = _partFlow select _bagAccessSite;
                if (_oldFlow > 0) then {
                    _partFlow set [_bagAccessSite, 0];
                    _flowArray set [_partIndex, _partFlow];
                    [_patient, [["fluidBagsFlowIV", _flowArray]], true] call ACM_circulation_fnc_setRuntimeState;
                };
            };
        };
    } else {
        private _flowArray = +( _patient getVariable ["ACM_circulation_FluidBagsFlow_IO", [1,1,1,1,1,1]] );
        if (_partIndex < count _flowArray) then {
            _oldFlow = _flowArray select _partIndex;
            if (_oldFlow > 0) then {
                _flowArray set [_partIndex, 0];
                [_patient, [["fluidBagsFlowIO", _flowArray]], true] call ACM_circulation_fnc_setRuntimeState;
            };
        };
    };
};
ACME_infusion_pendingPausedFlow = [_patient, _partIndex, _bagIV, _bagAccessSite, _oldFlow];

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
