/* B123: one-way corpse physiology freeze.
 *
 * Engine death (alive == false) is the boundary. Cardiac arrest is NOT death and keeps normal medication,
 * sedation, TBI, resuscitation and post-ROSC physiology alive.
 *
 * This function clears only transient medication/sedation DRIVE state that would otherwise be useless on an
 * irreversibly dead casualty or could be replayed after an ownership edge. It intentionally does not touch wound
 * arrays, junctional evidence, IV/EJ/IO access, bags, chest seals/holes, thoracostomy/chest tubes, airway devices,
 * HPMK, AAJT/XStat, head-position evidence, or any other persistent intervention/corpse presentation state.
 */
params [["_patient", objNull, [objNull]]];
if (isNull _patient || {!local _patient} || {alive _patient}) exitWith {false};

// Local latch prevents repeated death/locality callbacks from rebroadcasting the same zeros.
if (_patient getVariable ["ACME_deadPhysiologyFrozenLocal", false]) exitWith {true};
_patient setVariable ["ACME_deadPhysiologyFrozenLocal", true, false];

// These are transient rate/sedation envelopes, not treatment evidence. Publish one final quiescent snapshot so a
// later owner cannot resurrect an old delivery queue or rapid-push load. After this, dead-patient delivery paths
// refuse to create new physiology state.
{
    _x params ["_name", "_value"];
    private _current = _patient getVariable [_name, nil];
    if (isNil "_current" || {!(_current isEqualTo _value)}) then {
        _patient setVariable [_name, _value, true];
    };
} forEach [
    ["ACME_medicationDriveQueue", []],
    ["ACME_vascularTransit", []],
    ["ACME_adenosineEpisodes", []],
    ["ACME_ketRapidLoad", 0],
    ["ACME_hcMed_rapidPropofol", 0],
    ["ACME_hcMed_rapidMidazolam", 0],
    ["ACME_hcMed_rapidOpioid", 0],
    ["ACME_hcMed_rapidRocuronium", 0],
    ["ACME_ket_sedated", false],
    ["ACME_midaz_onsetT0", -1],
    ["ACME_midaz_sedRamp", 0],
    ["ACME_midaz_sedEffective", 0],
    ["ACME_ket_sympatheticEffect", 0],
    ["ACME_sedation_hrAdjust", 0],
    ["ACME_sedation_resistAdjust", 0]
];
true
