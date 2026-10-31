/* Opt-in initial React slice. Native controls remain available outside Chromium. */
params ["_medic","_patient","_part",["_returnAccess",[],[[]]]];
if (!hasInterface || {!isNull findDisplay 89300} || {!isNull findDisplay 86000}) exitWith {false};
private _context = [_medic,_patient,toLowerANSI _part,+_returnAccess,
    [_patient] call ACME_fnc_clinicalEpoch,_patient getVariable ["ACME_equipmentKitEpoch",0],
    _medic getVariable ["ACME_equipmentKitEpoch",0],_medic getVariable ["ACME_providerLocalityEpoch",0],owner _patient];
if !([_context] call ACME_fnc_reactMedicalValid) exitWith {false};
if (dialog) then {closeDialog 0;};
if !(createDialog "ACME_ReactMedicalDialog") exitWith {false};
private _display = findDisplay 89300;
if (isNull _display) exitWith {false};
_display setVariable ["ACME_reactContext",_context];
_display setVariable ["ACME_reactDeadline",diag_tickTime + 6];
// Also install a generation for the browser-blocked path that never emits PageLoaded.
private _serial = (missionNamespace getVariable ["ACME_reactSerial",0]) + 1;
missionNamespace setVariable ["ACME_reactSerial",_serial];
_display setVariable ["ACME_reactSerial",_serial];
private _control = _display displayCtrl 89301;
_display setVariable ["ACME_reactPFH",[ACME_fnc_reactMedicalTick,0.5,[_display]] call CBA_fnc_addPerFrameHandler];
_control ctrlWebBrowserAction ["LoadFile","acm_extended\ui\react\index.html"];
true
