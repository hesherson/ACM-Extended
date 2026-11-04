/* Explicit physical USB connection; the existing Bluetooth pairing is retained on unplug. */
params ["_actor","_ls","_pro",["_on",true],["_expectedEpoch",-1]];
if (canSuspend) exitWith {isNil {[_actor,_ls,_pro,_on,_expectedEpoch] call ACME_fnc_equipmentLinkRequest;};};
if !(_actor isEqualType objNull && {_ls isEqualType objNull} && {_pro isEqualType objNull}) exitWith {};
if (!isServer || {isNull _actor} || {isNull _ls} || {!(_on isEqualType false)}) exitWith {};
if (isRemoteExecuted && {remoteExecutedOwner != owner _actor}) exitWith {};
if !(_expectedEpoch isEqualType 0) exitWith {};
if (_expectedEpoch<0 && {!isRemoteExecuted}) then {_expectedEpoch=_ls getVariable ["ACME_eq_usbEpoch",0];};
if (!finite _expectedEpoch || {_expectedEpoch<0} || {_expectedEpoch!=floor _expectedEpoch}
    || {_expectedEpoch!=(_ls getVariable ["ACME_eq_usbEpoch",0])}) exitWith {};
if (!alive _actor || {_actor getVariable ["ACE_isUnconscious",false]} || {!isNull objectParent _actor}
    || {_actor distance _ls > 3} || {_actor getVariable ["ACME_persistenceFrozen",false]}
    || {_ls getVariable ["ACME_eq_busy",false]} || {!(_ls isKindOf "ACME_TempusLS")}
    || {(_ls getVariable ["ACME_eq_kind",""]) != "ls"}
    || {(_actor getVariable ["ACME_equipmentWorldPending",""]) != ""}) exitWith {};
private _patient=_ls getVariable ["acme_tempusls_pat",objNull];
if (!isNull _patient && {_patient getVariable ["ACME_persistenceFrozen",false]}) exitWith {};
private _old=_ls getVariable ["ACME_eq_usb",objNull];
private _oldPatient=if (isNull _old) then {objNull} else {_old getVariable ["acme_tempus_pat",objNull]};
if (!isNull _oldPatient && {_oldPatient getVariable ["ACME_persistenceFrozen",false]}) exitWith {};
if (!_on) exitWith {
    if (isNull _old) exitWith {};
    if (!isNull _old && {(_old getVariable ["ACME_eq_usbLs",objNull]) isEqualTo _ls}) then {_old setVariable ["ACME_eq_usbLs",objNull,true];};
    _ls setVariable ["ACME_eq_usb",objNull,true];
    _ls setVariable ["ACME_eq_usbEpoch",_expectedEpoch+1,true];
};
if (isNull _pro || {!(_pro isKindOf "ACME_TempusPro")} || {_actor distance _pro > 3} || {_ls distance _pro > 2.3}
    || {(_pro getVariable ["ACME_eq_kind",""]) != "pro"}
    || {_pro getVariable ["ACME_eq_busy",false]} || {!isNull _old}
    || {!isNull (_pro getVariable ["ACME_eq_usbLs",objNull])}) exitWith {};
private _proPatient=_pro getVariable ["acme_tempus_pat",objNull];
if (!isNull _proPatient && {_proPatient getVariable ["ACME_persistenceFrozen",false]}) exitWith {};
if (!isNull _patient && {!isNull _proPatient} && {_patient isNotEqualTo _proPatient}) exitWith {};
_ls setVariable ["ACME_eq_usb",_pro,true];_pro setVariable ["ACME_eq_usbLs",_ls,true];
_ls setVariable ["ACME_eq_usbEpoch",_expectedEpoch+1,true];
_ls setVariable ["acme_tempusls_link",_pro,true];
if (!isNull _patient && {isNull _proPatient}) then {[_pro,_patient] call ACME_fnc_tempusConnect;};
