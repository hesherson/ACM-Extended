#include "script_component.hpp"

// Reset burn-owned state on full heal. CBRN-owned inflammation is never cleared here.
[QACEGVAR(medical_treatment,fullHealLocalMod), LINKFUNC(fullHealLocal)] call CBA_fnc_addEventHandler;

// Burn wound intake. The wound system supplies depth, location and magnitude. We retain the worst
// depth/magnitude seen on each adult body region and derive one bounded whole-body burden from it.
// This replaces the old flat "subtract 0.2/0.3 L blood per burn" model.
[QGVAR(burnApplied), {
    params ["_patient", "_bodyPart", "_woundType", ["_magnitude",0.25]];
    if (!GVAR(burnsEnabled) || {isNull _patient} || {!local _patient} || {!alive _patient}) exitWith {};

    private _parts = ["head","body","leftarm","rightarm","leftleg","rightleg"];
    private _idx = _parts find (toLowerANSI _bodyPart);
    if (_idx < 0) exitWith {};

    private _surface = _patient getVariable [QGVAR(BurnSurface), [0,0,0,0,0,0]];
    if !(_surface isEqualType [] && {count _surface == 6}) then {_surface = [0,0,0,0,0,0];};

    private _depth = if (_woundType isEqualTo "Burn3") then {1.0} else {0.65};
    private _mag = linearConversion [0.05,1.0,_magnitude,0.45,1,true];
    private _regional = (_depth * _mag) max 0 min 1;
    _surface set [_idx, (_surface select _idx) max _regional];

    // Adult surface-area weighting. This is a bounded gameplay burden used for physiology;
    // it is deliberately not exposed as a bedside TBSA calculator.
    private _weights = [0.09,0.36,0.09,0.09,0.18,0.18];
    private _burden = 0;
    { _burden = _burden + ((_surface select _forEachIndex) * _x); } forEach _weights;
    _burden = _burden max 0 min 1;

    _patient setVariable [QGVAR(BurnSurface),_surface,true];
    _patient setVariable [QGVAR(BurnBurden),_burden,true];
    _patient setVariable [QGVAR(SystemicBurden),(_patient getVariable [QGVAR(SystemicBurden),0]) max _burden,true];
    _patient setVariable [QGVAR(LastBurnAt),CBA_missionTime,true];
    _patient setVariable [QGVAR(InfectionRiskMult),1 + (1.5 * _burden),true];

    // Airway injury is source-separated from CBRN. The burn worker progressively develops edema;
    // a later CBRN reset can no longer erase the burn, and healing a burn cannot erase chemical inflammation.
    if (
        _idx == 0 &&
        {!(_patient getVariable [QGVAR(AirwayBurned),false])} &&
        {random 1 < GVAR(headBurnAirwayChance)}
    ) then {
        _patient setVariable [QGVAR(AirwayBurned),true,true];
        _patient setVariable [QGVAR(AirwayBurnOnset),CBA_missionTime,true];
    };

    [_patient] call FUNC(tickPatient);
}] call CBA_fnc_addEventHandler;

// One locality-safe worker. No per-casualty PFH survives ownership migration.
if (isNil QGVAR(runtimePFH)) then {
    GVAR(runtimePFH) = [{
        {
            if (local _x && {alive _x} && {_x isKindOf "CAManBase"}) then {
                private _needs = (_x getVariable [QGVAR(BurnBurden),0]) > 0.001
                    || {(_x getVariable [QGVAR(AirwayInflammation),0]) > 0.001}
                    || {_x getVariable [QGVAR(PermanentInjury),false]};
                if (_needs) then {[_x] call FUNC(tickPatient);};
            };
        } forEach allUnits;
    }, 2, []] call CBA_fnc_addPerFrameHandler;
};

// ACE fire already produces burns. Add nearby explosion burns from the engine/CBA per-unit event.
["CBA_settingsInitialized", {
    if (!GVAR(sourcesEnabled)) exitWith {};
    ["CAManBase", "explosion", LINKFUNC(handleExplosion)] call CBA_fnc_addClassEventHandler;
}] call CBA_fnc_addEventHandler;
