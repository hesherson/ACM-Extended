/* Stable B188: bridge persistent manual plate-carrier custody into Semi-Fowler support custody.
 *
 * "borrow" does NOT end the manual lease and does NOT duplicate gear. It exposes the existing chest-access
 * saved vest/prop through the head-elevation support variables so the normal Semi-Fowler lift can seat the
 * already-removed carrier behind the upper back.
 *
 * "release" retires only the head-elevation view of that custody, returns the same prop to the fixed chest-access
 * park above the casualty's head, and leaves the manual lease/saved vest intact.
 */
params [
    ["_patient", objNull, [objNull]],
    ["_mode", "borrow", [""]]
];

if (isNull _patient || {!local _patient}) exitWith {false};
_mode = toLowerANSI _mode;

private _borrowed = _patient getVariable ["ACME_headElev_manualCarrierBorrowed", false];

if (_mode == "release") exitWith {
    if (!_borrowed) exitWith {true};

    private _prop = _patient getVariable ["ACME_headElev_propObj", objNull];

    _patient setVariable ["ACME_headElev_manualCarrierBorrowed", false, true];
    _patient setVariable ["ACME_headElev_vestRemoved", false, true];
    _patient setVariable ["ACME_headElev_vestLoadout", [], true];
    _patient setVariable ["ACME_headElev_propVest", "", true];
    _patient setVariable ["ACME_headElev_propVestItems", [], true];
    _patient setVariable ["ACME_headElev_propObj", objNull, true];

    if (!isNull _prop) then {
        _prop setVariable ["ACME_chestFixedPark", nil, false];
    };
    [_patient] call ACME_fnc_chestAccessVestPark;
    true
};

if (_mode != "borrow") exitWith {false};
if (_borrowed) exitWith {true};

private _state = _patient getVariable ["ACME_manualPlateCarrierState", ""];
private _lease = _patient getVariable ["ACME_manualPlateCarrierLease", ""];
private _saved = +(_patient getVariable ["ACME_chestAccess_vestLoadout", []]);
private _prop = _patient getVariable ["ACME_chestAccess_vestProp", objNull];

if !(_state in ["off", "restoring"]) exitWith {false};
if (_lease == "" || {(count _saved) != 2} || {(vest _patient) != ""}) exitWith {false};

private _vestClass = _saved param [0, "", [""]];
if (_vestClass == "") exitWith {false};

_patient setVariable ["ACME_headElev_manualCarrierBorrowed", true, true];
_patient setVariable ["ACME_headElev_vestRemoved", true, true];
_patient setVariable ["ACME_headElev_vestLoadout", +_saved, true];
_patient setVariable ["ACME_headElev_vestLoadoutKitEpoch",
    _patient getVariable ["ACME_chestAccess_vestLoadoutKitEpoch", _patient getVariable ["ACME_equipmentKitEpoch", 0]], true];
_patient setVariable ["ACME_headElev_propVest", _vestClass, true];
_patient setVariable ["ACME_headElev_propVestItems", [], true];
_patient setVariable ["ACME_headElev_propObj", _prop, true];

if (!isNull _prop) then {
    // Release the fixed ground park. The normal Semi-Fowler lift will attach this exact prop after the patient rises.
    _prop setVariable ["ACME_chestFixedPark", nil, false];
};

true
