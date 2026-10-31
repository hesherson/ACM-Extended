// The transfusion-only Hang Bag action rechecks the current row before starting its animation.
// only one bag may be up at once, whether an infusion or a transfusion, so it refuses if the medic is already
// holding one.
private _display = findDisplay 86000;
if (isNull _display || {(_display getVariable ["ACME_txActivePane", "transfusion"]) != "transfusion"}) exitWith {};
private _ctx = ["transfusion"] call ACME_fnc_getSelectedActiveBagContext;
if (_ctx isEqualTo []) exitWith {};
_ctx params ["_patient", "_bodyPart", "_bagIndex", "_type", "", "_accessSite"];
if !(_type in ["Blood", "FreshBlood", "Saline", "Plasma", "PlasmaLyte"]) exitWith {};
if ((_ctx param [10, 0]) <= 0.5 || {_bagIndex < 0}) exitWith {};
private _bag = ((_patient getVariable ["ACM_circulation_IV_Bags", createHashMap]) getOrDefault [_bodyPart, []]) param [_bagIndex, []];
private _id = _bag param [8, ""];
if (((_patient getVariable ["ACME_infusion_BagMedications", []]) findIf {(_x param [23, ""]) == _id && {_id != ""}}) >= 0) exitWith {};
private _medic = (call ACME_fnc_controlledProvider);
if (isNull _patient || {isNull _medic}) exitWith {};

if (_medic getVariable ["ACME_hang_Active", false]) exitWith {
    ["Already holding a bag. Lower it first.", 2, _medic] call ace_common_fnc_displayTextStructured;
};
if (!isNull objectParent _medic) exitWith {
    ["Can't hold a bag up from inside a vehicle.", 2, _medic] call ace_common_fnc_displayTextStructured;
};


// there must be a bag to raise.
if (!([_medic, _patient] call ACME_fnc_hangBagCanStart)) exitWith {
    ["No hung IV bag on this patient to raise.", 2, _medic] call ace_common_fnc_displayTextStructured;
};

private _fluidType = [_patient, _bodyPart, _accessSite] call ACME_fnc_hangBagFluidType;

closeDialog 0;

// a smooth weapon stow up front, then a short raise countdown, then the bag goes up with the right color.
[_medic] call ACME_fnc_hangBagPrep;
[
    (missionNamespace getVariable ["ACME_hang_raiseTime", 1.5]),
    [_medic, _patient, _bodyPart, _fluidType],
    { (_this select 0) call ACME_fnc_hangBagStart },
    { [((_this select 0) select 0)] call ACME_fnc_hangBagPrepStop },
    "Raising the bag...",
    { alive (_this select 0 select 1) }
] call ace_common_fnc_progressBar;
