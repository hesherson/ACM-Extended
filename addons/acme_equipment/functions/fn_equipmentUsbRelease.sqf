/* Trusted server cleanup for either end of a physical USB connection. Wireless pairing is separate. */
params ["_device"];
if (canSuspend) exitWith {isNil {[_device] call ACME_fnc_equipmentUsbRelease;};};
if (!isServer || {isNull _device}) exitWith {};
private _kind=_device getVariable ["ACME_eq_kind",""];
private _ls=if (_kind=="ls") then {_device} else {_device getVariable ["ACME_eq_usbLs",objNull]};
if (!(_kind in ["pro","ls"]) || {isNull _ls}) exitWith {};
private _pro=_ls getVariable ["ACME_eq_usb",objNull];
if (_kind=="pro" && {_pro isNotEqualTo _device}) exitWith {
    // Another relationship owns that LS now; retire only this stale reverse claim.
    _device setVariable ["ACME_eq_usbLs",objNull,true];
};
if (!isNull _pro && {(_pro getVariable ["ACME_eq_usbLs",objNull]) isEqualTo _ls}) then {
    _pro setVariable ["ACME_eq_usbLs",objNull,true];
};
if (isNull _pro) exitWith {};
_ls setVariable ["ACME_eq_usb",objNull,true];
_ls setVariable ["ACME_eq_usbEpoch",(_ls getVariable ["ACME_eq_usbEpoch",0])+1,true];

