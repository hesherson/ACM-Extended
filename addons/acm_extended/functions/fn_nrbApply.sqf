// apply a non-rebreather mask, an NRB, to a patient. it is reusable equipment: it requires the mask in inventory
// and does not consume it. placement takes about 1 s, the treatmenttime on ACME_ApplyNRB.
// the oxygen requirement: an NRB is useless without an o2 source, so by default you cannot place it unless the
// provider carries an ACM oxygen tank, ACM_OxygenTank_425, with reserve. with no tank the attempt is refused with
// a prompt and nothing goes on.
// the NRB-hardcore setting, ACME_hcEff_nrb, flips this: there is no prompt, and a no-o2 mask still goes on and
// stays silent and gives no SpO2 support.
// _this is the ACE callback [_medic, _patient, _bodyPart].
params ["_medic", "_patient"];
if (isNull _patient) exitWith {};
if (_patient getVariable ["ACME_nrb_on", false]) exitWith {
    ["NRB is already on this patient.", 2, _medic] call ace_common_fnc_displayTextStructured;
};

// Hard runtime gate as well as the medical-menu condition. This closes the race where an advanced airway can be
// placed after the action becomes visible but before callbackSuccess executes.
if !([_patient] call ACME_fnc_nrbAirwayCompatible) exitWith {
    ["Cannot apply NRB with an i-gel, ET tube, or surgical airway in place. Use BVM or ventilator support.", 3, _medic] call ace_common_fnc_displayTextStructured;
};

// does the provider have an oxygen tank with reserve? it mirrors ACM's own tank lookup: an ACM_OxygenTank_425
// magazine in any worn container with ammo above 0.
private _hasO2 = false;
{
    {
        _x params ["_mag", "_count"];
        if (_mag == "ACM_OxygenTank_425" && {_count > 0}) exitWith { _hasO2 = true; };
    } forEach (magazinesAmmoCargo _x);
    if (_hasO2) exitWith {};
} forEach [uniformContainer _medic, vestContainer _medic, backpackContainer _medic];
// a tank packed in a kit counts too (ACME_fnc_itemCount); it is drawn from there by useOxygenTankReserve.
if (!_hasO2) then {_hasO2 = ([_medic, "ACM_OxygenTank_425"] call ACME_fnc_itemCount) > 0;};

private _hardcore = missionNamespace getVariable ["ACME_hcEff_nrb", false];

// normal mode with no o2: refuse with a prompt, and the mask does not go on.
if (!_hasO2 && {!_hardcore}) exitWith {
    ["No oxygen source. Need an ACM oxygen tank.", 3, _medic] call ace_common_fnc_displayTextStructured;
    if (!isNil "ace_medical_treatment_fnc_addToLog") then {
        [_patient, "activity", "NRB not placed: no oxygen source", "NRB not placed, no O2 source", []] call ACME_fnc_medLog;
    };
};

// Authoritative patient state is applied on its owner; medic cargo stays on the medic owner.
["ACME_ownerCommand", [_patient, "nrbState", [_patient, _medic, true, _hasO2]], _patient] call CBA_fnc_targetEvent;
