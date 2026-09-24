/* Shared ETT/i-gel attachment eligibility. Attaching the monitor is patient contact.
   Do not require an earlier assessment to make the attachment action appear. */
params [["_medic", objNull, [objNull]], ["_patient", objNull, [objNull]], ["_required", "", [""]]];
if (isNull _medic || {isNull _patient}) exitWith {false};
if (_patient isEqualTo _medic || {!(_patient isKindOf "CAManBase")}) exitWith {false};
if !(missionNamespace getVariable ["ACME_sys_emma", true]) exitWith {false};
private _airway = [_patient] call ACME_fnc_emmaAirwayKind;
if (_airway == "" || {_required != "" && {_airway != _required}}) exitWith {false};
if (_patient getVariable ["ACME_emma_igelAttached", false]) exitWith {false};
private _range = missionNamespace getVariable ["ACME_emma_igelRange", 5];
private _sameVehicle = (vehicle _medic != _medic) && {(vehicle _medic) isEqualTo (vehicle _patient)};
if (!_sameVehicle && {(_medic distance _patient) > _range}) exitWith {false};
(_medic getVariable ["ACME_emma_bvmAttached", false]) || {
    ([_medic, "ACM_EMMA"] call ACME_fnc_itemCount) > 0
}
