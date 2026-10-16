/* Item class -> charge, or decided charge -> physical returned item class.
 * Returned cells round downward to a whole percent, never creating energy. */
params [["_value", "", ["", 0]]];
if (_value isEqualType 0) exitWith {
    if (!finite _value) exitWith {""};
    private _charge = floor (_value max 0 min 100);
    if (_charge == 100) then {"ACME_VentBattery"} else {format ["ACME_VentBattery_%1", _charge]}
};
if !(_value in (call ACME_fnc_ventBatteryItems)) exitWith {-1};
getNumber (configFile >> "CfgWeapons" >> _value >> "ACME_batteryCharge")
