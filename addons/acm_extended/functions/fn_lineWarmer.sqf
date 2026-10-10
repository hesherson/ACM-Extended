/* B227: persistent inline equipment belongs to an exact access, not the lifetime of one bag.
 * Call on the owner to fit it; read-only calls are safe in the UI and native drainer. */
params ["_patient", "_part", "_iv", "_site", ["_fit", false], ["_medic", objNull]];
private _key = toLowerANSI format ["%1#%2#%3", _part, _iv, _site];
private _legacy = isNil {_patient getVariable "ACME_lineWarmers"};
private _lines = _patient getVariable ["ACME_lineWarmers", createHashMap];
if (_fit && {local _patient} && {!isNull _medic} && {alive _medic}
    && {!(_medic getVariable ["ACE_isUnconscious",false])}
    && {([_medic,_patient] call ACME_fnc_patientInteractionDistance) <= 5}
    && {([_medic, _patient, "ACME_BloodWarmer"] call ACME_fnc_treatmentSupplyCount) > 0}
    && {[_patient, _part, _iv, _site] call ACME_fnc_transfusionAccessValid}) then {
    if !(_lines getOrDefault [_key, false]) then {
        _lines set [_key, true];
        [_patient, "ACME_lineWarmers", _lines] call ACME_fnc_setVarNet;
    };
};
// Legacy data without an equipment map keeps its existing thermal behavior; once a
// line is explicitly tracked, an unrelated line cannot inherit the patient's warm flag.
_lines getOrDefault [_key, _legacy && {_patient getVariable ["ACME_warmedBlood", false]}]
