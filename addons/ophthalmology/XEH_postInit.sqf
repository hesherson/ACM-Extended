#include "script_component.hpp"

if (missionNamespace getVariable [QGVAR(runtimeInstalled), false]) exitWith {};
GVAR(runtimeInstalled) = true;

// Presentation worker exists only on clients.
if (hasInterface && {isNil QGVAR(visualEffectsPFH)}) then {
    GVAR(visualEffectsPFH) = [LINKFUNC(updateVisualEffects), 0.25, []] call CBA_fnc_addPerFrameHandler;
};

if (isNil QGVAR(activePatients)) then {GVAR(activePatients) = [];};
if (isNil QGVAR(lastDiscovery)) then {GVAR(lastDiscovery) = -1;};

// Owner-authoritative shield placement. The treatment callback may originate on another medic,
// but the patient's HMD slot and durable ocular state are mutated only where that patient is local.
[QGVAR(applyEyeShield), LINKFUNC(shieldCommit)] call CBA_fnc_addEventHandler;
[QGVAR(shieldResult), {["result",_this] call FUNC(shieldSource);}] call CBA_fnc_addEventHandler;
[QGVAR(shieldCleanup), {["cleanup",_this] call FUNC(shieldSource);}] call CBA_fnc_addEventHandler;
[QGVAR(shieldDecisionQuery), {["proofQuery",_this select 0] call FUNC(shieldCommit);}] call CBA_fnc_addEventHandler;
[QGVAR(shieldDecisionProof), {["proof",_this select 0,0,_this select 1] call FUNC(shieldCommit);}] call CBA_fnc_addEventHandler;
[QGVAR(shieldSettled), {["settled",_this select 0,0,_this select 1] call FUNC(shieldCommit);}] call CBA_fnc_addEventHandler;
[QGVAR(shieldClosed), {["closed",_this] call FUNC(shieldSource);}] call CBA_fnc_addEventHandler;
[QGVAR(shieldTerminalClosed), {["terminalClosed",_this select 0,0,_this select 1] call FUNC(shieldCommit);}] call CBA_fnc_addEventHandler;

[QGVAR(clearEyeInjury), LINKFUNC(clearEyeInjury)] call CBA_fnc_addEventHandler;

// One locality-safe ocular worker per machine. Active structural casualties tick every second;
// a slow discovery fallback recovers locality migration/JIP and restored persistent state.
if (isNil QGVAR(structuralPFH)) then {
    GVAR(structuralPFH) = [{
        private _active = GVAR(activePatients) select {!isNull _x && {alive _x || {count (_x getVariable [QGVAR(shieldIncoming),createHashMap]) > 0}}};

        {
            if (local _x) then {
                [_x] call FUNC(shieldRecover);
                if (alive _x) then {[_x] call FUNC(structuralTick);};
            };
        } forEach _active;

        _active = _active select {
            local _x && {(alive _x || {count (_x getVariable [QGVAR(shieldIncoming),createHashMap]) > 0})} && {
                private _eyes = _x getVariable [QGVAR(eyeInjuries),[1,1]];
                (_eyes isEqualType [] && {count _eyes == 2} && {({_x < 0.999} count _eyes) > 0})
                || {(_x getVariable [QGVAR(eyeShieldItem),""]) != ""}
                || {_x getVariable [QGVAR(ocularPermanent),false]}
                || {count (_x getVariable [QGVAR(shieldIncoming),createHashMap]) > 0}
            }
        };

        if (GVAR(lastDiscovery) < 0 || {CBA_missionTime - GVAR(lastDiscovery) >= 10}) then {
            GVAR(lastDiscovery) = CBA_missionTime;
            {
                private _patient = _x;
                if (local _patient && {_patient isKindOf "CAManBase"}) then {
                    private _eyes = _patient getVariable [QGVAR(eyeInjuries),[1,1]];
                    private _needs = (_eyes isEqualType [] && {count _eyes == 2} && {({_x < 0.999} count _eyes) > 0})
                        || {(_patient getVariable [QGVAR(eyeShieldItem),""]) != ""};
                    _needs = _needs || {_patient getVariable [QGVAR(ocularPermanent),false]};
                    _needs = _needs || {count (_patient getVariable [QGVAR(shieldIncoming),createHashMap]) > 0};
                    if (_needs) then {_active pushBackUnique _patient;};
                };
            } forEach (allUnits + allDeadMen);
        };

        GVAR(activePatients) = _active;
    }, 1, []] call CBA_fnc_addPerFrameHandler;
};

["CBA_settingsInitialized", {
    // Register once even when initially disabled; each injury handler checks the live setting.
    // Enabling/disabling this setting during a mission must not require a new postInit.
    if (missionNamespace getVariable [QGVAR(injuryEventsInstalled),false]) exitWith {};
    GVAR(injuryEventsInstalled) = true;
    // Dust/rotor-wash effects are local presentation events.
    if (hasInterface) then {
        [QACEGVAR(goggles,effect), LINKFUNC(handleDustInjury)] call CBA_fnc_addEventHandler;
    };

    // Explosion injury state must exist for every casualty, not only ACE_player.
    ["CAManBase", "explosion", LINKFUNC(handleExplosion)] call CBA_fnc_addClassEventHandler;
}] call CBA_fnc_addEventHandler;

[QACEGVAR(medical_treatment,fullHealLocalMod), LINKFUNC(fullHealLocal)] call CBA_fnc_addEventHandler;
[QACEGVAR(medical_gui,updateInjuryListPart), LINKFUNC(gui_updateInjuryListPart)] call CBA_fnc_addEventHandler;
