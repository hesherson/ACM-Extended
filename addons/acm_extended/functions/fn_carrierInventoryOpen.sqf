/* Opens vanilla Gear on the live ground container, after the medical UI has actually finished closing.
   Native actionNow avoids the old Gear action's provider-animation preparation silently eating the request. */
params ["_medic", "_patient", ["_requestedCargo",objNull]];
if (isNull _medic || {!local _medic} || {!alive _medic}
    || {_medic getVariable ["ACE_isUnconscious",false]}
    || {isNull _patient}) exitWith {false};
private _cargo = [_patient] call ACME_fnc_carrierInventoryGet;
if (isNull _cargo || {(!isNull _requestedCargo) && {_cargo isNotEqualTo _requestedCargo}}
    || {_medic distance _cargo > 3.2}) exitWith {false};
private _menu = uiNamespace getVariable ["ace_medical_gui_menuDisplay",displayNull];
// Do not close a different equipment dialog or queue a surprise inventory over it.
if (dialog && {isNull _menu}) exitWith {false};
private _token = (_medic getVariable ["ACME_carrierOpenToken",0]) + 1;
_medic setVariable ["ACME_carrierOpenToken",_token,false];
ace_medical_gui_pendingReopen = false;
if (!isNull _menu) then {closeDialog 0;};
[{
    params ["_medic","_patient","_cargo","_token"];
    if (isNull _medic || {!local _medic} || {!alive _medic}
        || {_medic getVariable ["ACE_isUnconscious",false]}
        || {(_medic getVariable ["ACME_carrierOpenToken",-1]) != _token}
        || {isNull _cargo} || {_cargo getVariable ["ACME_carrierClosing",false]}
        || {([_patient] call ACME_fnc_carrierInventoryGet) isNotEqualTo _cargo}
        || {_medic distance _cargo > 3.2} || {dialog}) exitWith {};
    _medic actionNow ["Gear",_cargo];
},[_medic,_patient,_cargo,_token],0.15] call CBA_fnc_waitAndExecute;
true
