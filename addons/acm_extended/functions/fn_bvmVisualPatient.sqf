// Both client HUDs use the native target when available and share a short fallback scan.
params ["_provider"];
private _target = missionNamespace getVariable ["ACM_breathing_BVMTarget", objNull];
if (!isNull _target && {(_target getVariable ["ACM_breathing_BVM_Medic", objNull]) isEqualTo _provider
    || {_provider getVariable ["ACM_breathing_isUsingBVM", false]}}) exitWith {_target};

private _cached = _provider getVariable ["ACME_bvmVisualSearch", [0, objNull]];
_cached params ["_next", "_patient"];
if (diag_tickTime < _next) exitWith {
    if (!isNull _patient && {alive _patient} && {_provider distance _patient <= 10}
        && {(_patient getVariable ["ACM_breathing_BVM_Medic", objNull]) isEqualTo _provider}) then {_patient} else {objNull}
};
_patient = objNull;
{
    if ((_x getVariable ["ACM_breathing_BVM_Medic", objNull]) isEqualTo _provider) exitWith {_patient = _x;};
} forEach (_provider nearEntities ["CAManBase", 10]);
_provider setVariable ["ACME_bvmVisualSearch", [diag_tickTime + 0.25, _patient]];
_patient
