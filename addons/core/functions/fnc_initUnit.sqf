#include "..\script_component.hpp"
/*
 * Author: Blue
 * Init unit.
 *
 * Arguments:
 * 0: Patient <OBJECT>
 *
 * Return Value:
 * None
 *
 * Example:
 * [player] call ACM_core_fnc_initUnit;
 *
 * Public: No
 */

params ["_patient"];

[_patient] call EFUNC(airway,initUnit);
[_patient] call EFUNC(circulation,initUnit);

[{
    params ["_patient"];

    // B387: the init event runs on every machine, also on each that joins later. Randomised values written public
    // from each of them raced (measured on a dedicated server: body weight 85.5 kg on the server, 79.3 kg on a
    // client), and a player joining re-rolled them for every AI. Only the unit's own machine rolls them; a player's
    // values come from the Steam ID and are the same wherever they are computed.
    if (local _patient || {isMultiplayer && {isPlayer _patient}}) then {
        [_patient] call FUNC(generateTargetVitals);
    };
}, [_patient], 0.5] call CBA_fnc_waitAndExecute;
