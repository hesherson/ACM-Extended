/* Reload/initial PageLoaded creates a fresh session; old messages cannot inherit this view. */
params ["_control"];
private _display = ctrlParent _control;
if (isNull _display || {!(_display isEqualTo findDisplay 89300)}) exitWith {};
private _context = _display getVariable ["ACME_reactContext",[]];
if !([_context] call ACME_fnc_reactMedicalValid) exitWith {};
private _serial = (missionNamespace getVariable ["ACME_reactSerial",0]) + 1;
missionNamespace setVariable ["ACME_reactSerial",_serial];
private _session = format ["ui:%1:%2",clientOwner,_serial];
_display setVariable ["ACME_reactSerial",_serial];
_display setVariable ["ACME_reactSession",_session];
_display setVariable ["ACME_reactRequestSequence",0];
_display setVariable ["ACME_reactStateSequence",0];
_display setVariable ["ACME_reactReady",false];
_display setVariable ["ACME_reactDeadline",diag_tickTime + 6];
_display setVariable ["ACME_reactSignature",""];
private _hello = createHashMapFromArray [
    ["version",1],["session",_session],
    ["patientRef",["encode",_context select 1] call ACME_fnc_clinicalObjectRef],
    ["epoch",_context select 4]
];
_control ctrlWebBrowserAction ["ExecJS",format ["window.ACMEUI && window.ACMEUI.bootstrap(%1);",toJSON _hello]];
