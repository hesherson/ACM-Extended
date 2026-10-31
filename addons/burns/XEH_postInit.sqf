#include "script_component.hpp"

// Post-init replay must not duplicate pain callbacks, wound intake or workers.
if (missionNamespace getVariable [QGVAR(postInitRegistered),false]) exitWith {};
GVAR(postInitRegistered) = true;

// Reset burn-owned state on full heal. CBRN-owned inflammation is never cleared here.
[QACEGVAR(medical_treatment,fullHealLocalMod), LINKFUNC(fullHealLocal)] call CBA_fnc_addEventHandler;

// Burn wound intake. The wound system supplies depth, location and magnitude. We retain the worst
// depth/magnitude seen on each adult body region and derive one bounded whole-body burden from it.
// This replaces the old flat "subtract 0.2/0.3 L blood per burn" model.
[QGVAR(burnApplied), {
    params ["_patient", "_bodyPart", "_woundType", ["_magnitude",0.25]];
    if (!GVAR(burnsEnabled) || {isNull _patient} || {!local _patient} || {!alive _patient}) exitWith {};
    if !(_woundType in ["Burn2","Burn3"]) exitWith {};

    private _parts = ["head","body","leftarm","rightarm","leftleg","rightleg"];
    private _idx = _parts find (toLowerANSI _bodyPart);
    if (_idx < 0) exitWith {};

    private _surface = _patient getVariable [QGVAR(BurnSurface), [0,0,0,0,0,0]];
    if !(_surface isEqualType [] && {count _surface == 6}) then {_surface = [0,0,0,0,0,0];};
    private _protected = _patient getVariable [QGVAR(BurnProtected), [false,false,false,false,false,false]];
    if !(_protected isEqualType [] && {count _protected == 6}) then {_protected = [false,false,false,false,false,false];};
    _protected set [_idx,false];

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
    _patient setVariable [QGVAR(BurnProtected),_protected,true];
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

    if (isNil QGVAR(activePatients)) then {GVAR(activePatients) = [];};
    GVAR(activePatients) pushBackUnique _patient;
    [_patient] call FUNC(tickPatient);
}] call CBA_fnc_addEventHandler;

// Improper burn care still matters. A 2nd/3rd-degree burn covered with a generic dressing
// instead of the silver nylon dressing or burn cream produces additional pain. This preserves
// the imported treatment distinction without letting the dressing callback own systemic physiology.
[QACEGVAR(medical_treatment,bandageLocal), {
    params ["_patient", "_bodyPart", "_bandageClass"];
    if (!GVAR(burnsEnabled) || {isNull _patient} || {!local _patient}) exitWith {};
    private _woundNames = ACEGVAR(medical_damage,woundClassNames);
    private _partKey = toLowerANSI _bodyPart;
    private _open = (_patient getVariable [VAR_OPEN_WOUNDS, createHashMap]) getOrDefault [_partKey, []];
    if (_bandageClass in ["ACM_SilverNylonDressing", "ACM_BurnCream"]) exitWith {
        private _parts = ["head","body","leftarm","rightarm","leftleg","rightleg"];
        private _idx = _parts find _partKey;
        if (_idx >= 0) then {
            private _protected = _patient getVariable [QGVAR(BurnProtected), [false,false,false,false,false,false]];
            if !(_protected isEqualType [] && {count _protected == 6}) then {_protected = [false,false,false,false,false,false];};
            // ACE's native bandage handler has already applied the item. Cream
            // on a mixed superficial/deep burn and a partial silver dressing
            // must not protect the whole region while deep burns remain open.
            private _deepOpen = (_open findIf {(_x param [1,0]) > 0 && {
                (_woundNames param [floor ((_x select 0) / 10), ""]) in ["Burn2", "Burn3"]
            }}) >= 0;
            _protected set [_idx,!_deepOpen];
            _patient setVariable [QGVAR(BurnProtected),_protected,true];
            if (!isNil QGVAR(activePatients)) then {GVAR(activePatients) pushBackUnique _patient;};
        };
    };

    private _wounds = _open
                    + ((_patient getVariable [VAR_BANDAGED_WOUNDS, createHashMap]) getOrDefault [_partKey, []]);

    if ((_wounds findIf {(_x param [1,0]) > 0 && {(_woundNames param [floor ((_x select 0) / 10), ""]) in ["Burn2", "Burn3"]}}) > -1) then {
        [_patient, BURN_WRONG_DRESSING_PAIN] call ACEFUNC(medical_status,adjustPainLevel);
    };
}] call CBA_fnc_addEventHandler;

// One locality-safe worker. Active casualties tick frequently; healthy units receive no burn integration.
// A slow discovery fallback recovers JIP/locality migration and any state restored by ACME clinical persistence.
if (isNil QGVAR(activePatients)) then {GVAR(activePatients) = [];};
if (isNil QGVAR(lastDiscovery)) then {GVAR(lastDiscovery) = -1;};
if (isNil QGVAR(runtimePFH)) then {
    GVAR(runtimePFH) = [{
        private _active = GVAR(activePatients) select {!isNull _x && {alive _x}};

        {
            private _patient = _x;
            if (local _patient) then {
                [_patient] call FUNC(tickPatient);
            };
        } forEach _active;

        _active = _active select {
            GVAR(burnsEnabled) && {local _x} && {
                (_x getVariable [QGVAR(SystemicBurden),_x getVariable [QGVAR(BurnBurden),0]]) > 0
                || {(_x getVariable [QGVAR(AirwayInflammation),0]) > 0.001}
                || {_x getVariable [QGVAR(AirwayBurned),false]}
                || {_x getVariable [QGVAR(PermanentInjury),false]}
            }
        };

        if (GVAR(lastDiscovery) < 0 || {CBA_missionTime - GVAR(lastDiscovery) >= 10}) then {
            GVAR(lastDiscovery) = CBA_missionTime;
            {
                if (GVAR(burnsEnabled) && {local _x} && {alive _x} && {
                    (_x getVariable [QGVAR(SystemicBurden),_x getVariable [QGVAR(BurnBurden),0]]) > 0
                    || {(_x getVariable [QGVAR(AirwayInflammation),0]) > 0.001}
                    || {_x getVariable [QGVAR(AirwayBurned),false]}
                    || {_x getVariable [QGVAR(PermanentInjury),false]}
                }) then {
                    _active pushBackUnique _x;
                };
            } forEach allUnits;
        };

        GVAR(activePatients) = _active;
    }, 2, []] call CBA_fnc_addPerFrameHandler;
};

// ACE fire already produces burns. Add nearby explosion burns from the engine/CBA per-unit event.
["CBA_settingsInitialized", {
    // Admission belongs to handleExplosion so changing this setting later works.
    ["CAManBase", "explosion", LINKFUNC(handleExplosion)] call CBA_fnc_addClassEventHandler;
}] call CBA_fnc_addEventHandler;
