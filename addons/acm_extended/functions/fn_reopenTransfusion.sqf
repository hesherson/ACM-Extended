/* Local return after the source dialog has unloaded. Never replace a newer dialog. */
params ["_return"];
_return params ["_medic", "_patient", "_part", ["_iv", true], ["_site", -1]];
if (isNull _patient || {isNull _medic}) exitWith {};
ace_medical_gui_pendingReopen = false;
[{
    params ["_medic", "_patient", "_part", "_iv", "_site"];
    if (isNull _patient || {isNull _medic} || {!alive _medic} || {dialog}) exitWith {};
    if (!isNull (findDisplay 84000) || {!isNull (findDisplay 86200)}) exitWith {};
    // The opener validates and selects this route before its first inventory/filter/UI paint.
    [_medic, _patient, _part, [_iv,_site]] call ACM_circulation_fnc_openTransfusionMenu;
}, [_medic, _patient, _part, _iv, _site], 0.15] call CBA_fnc_waitAndExecute;
