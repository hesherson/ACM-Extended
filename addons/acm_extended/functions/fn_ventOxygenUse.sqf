/* Gas mixing gameplay model, not a device flow prescription.
   Return delivered FiO2. Delivered gas is inspiratory liters after pressure/volume limiting.
   Cylinder gas = delivered liters * (requested fraction - 0.21)/0.79.
   One outstanding prepaid charge bounds network lag; no delivery borrows future oxygen. */
params [["_patient",objNull,[objNull]],["_deliveredLiters",0,[0]],["_requested",21,[0]]];
if (isNull _patient || {!local _patient} || {!finite _deliveredLiters} || {!finite _requested}) exitWith {21};
_requested=_requested max 21 min 95;
if (_deliveredLiters<=0 || {_requested<=21}) exitWith {21};
private _usable=([_patient] call ACME_fnc_ventOxygenState) select 1;
if (!_usable) exitWith {21};
private _need=_deliveredLiters*((_requested/100)-0.21)/0.79;
private _credit=(_patient getVariable ["ACME_vent_o2Credit",0]) max 0;
if (_credit+0.000001<_need) exitWith {
    [_patient,true] call ACME_fnc_ventOxygenTick;
    21
};
_patient setVariable ["ACME_vent_o2Credit",(_credit-_need) max 0,true];
_requested
