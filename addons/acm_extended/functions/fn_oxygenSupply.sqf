/* Oxygen equipment advertises a real supply condition through ACE's public
 * gear config contract. Evaluate that condition for the patient being updated,
 * including AI/headless owners; ACE_player may be a different person or null.
 * An explicit mission/device supply state supports equipment outside ACE's
 * scanned goggles/headgear/vest classes. Appearance and class names confer
 * no oxygen. A condition must return Boolean true to provide supplied gas.
 */
params ["_patient"];
if (isNull _patient) exitWith {false};
private _supplied = _patient getVariable ["ACME_oxygenSupply", false];
if (_supplied isEqualType {}) then {
    private _result = _patient call _supplied;
    _supplied = !isNil "_result" && {_result isEqualType true} && {_result};
};
if (_supplied isEqualType true && {_supplied}) exitWith {true};
private _cache = missionNamespace getVariable ["ace_medical_vitals_oxygenSupplyConditionCache", createHashMap];
if !(_cache isEqualType createHashMap) exitWith {false};
([goggles _patient, headgear _patient, vest _patient] findIf {
    private _condition = _cache getOrDefault [_x, {false}];
    if (_condition isEqualType {}) then {
        private _result = _patient call _condition;
        !isNil "_result" && {_result isEqualType true} && {_result}
    } else {false}
}) >= 0
