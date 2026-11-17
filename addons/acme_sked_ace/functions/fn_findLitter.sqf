/*
 * The nearest laid out SKED within 3.5 m of a unit that nobody is moving.
 * Arguments: 0: unit. Returns: object (objNull if none).
 */
params ["_unit", ["_skedOnly", false]];
((nearestObjects [_unit, ["ACME_SKED_Open"], 3.5]) select {
    (!_skedOnly || {typeOf _x == "ACME_SKED_Open"}) && {isNull attachedTo _x}
        && {!(_x getVariable ["acme_talon_busy", false])}
        && {isNull (_x getVariable ["ace_common_owner", objNull])}
}) param [0, objNull]
