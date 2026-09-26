#include "script_component.hpp"

// Presentation worker exists only on clients.
if (hasInterface && {isNil QGVAR(visualEffectsPFH)}) then {
    GVAR(visualEffectsPFH) = [LINKFUNC(updateVisualEffects), 0.25, []] call CBA_fnc_addPerFrameHandler;
};

// Owner-authoritative shield placement. The treatment callback may originate on another medic,
// but the patient's HMD slot and durable ocular state are mutated only where that patient is local.
[QGVAR(applyEyeShield), {
    params ["_patient","_shieldItem","_eyeIndex"];
    if (isNull _patient || {!local _patient} || {!alive _patient}) exitWith {};

    private _existingHmd = hmd _patient;
    if (_existingHmd != "" && {_existingHmd != _shieldItem}) then {
        _patient unlinkItem _existingHmd;
        _patient addItem _existingHmd;
    };
    if ((hmd _patient) != _shieldItem) then {_patient linkItem _shieldItem;};

    _patient setVariable [QGVAR(eyeShieldItem),_shieldItem,true];
    _patient setVariable [QGVAR(eyeShieldIndex),_eyeIndex,true];
    _patient setVariable [QGVAR(eyeShieldAppliedAt),CBA_missionTime,true];

    if (hasInterface && {_patient isEqualTo ACE_player}) then {
        private _displayId = [17103,17102] select _eyeIndex;
        [_displayId] call FUNC(showEyeShieldOverlay);
    };
}] call CBA_fnc_addEventHandler;

// One locality-safe ocular worker per machine. It picks up a casualty automatically after ownership migration.
if (isNil QGVAR(structuralPFH)) then {
    GVAR(structuralPFH) = [{
        {
            if (local _x && {alive _x} && {_x isKindOf "CAManBase"}) then {
                private _eyes = _x getVariable [QGVAR(eyeInjuries),[1,1]];
                private _needs = (_eyes isEqualType [] && {count _eyes == 2} && {({_x < 0.999} count _eyes) > 0})
                    || {(_x getVariable [QGVAR(eyeShieldItem),""]) != ""};
                if (_needs) then {[_x] call FUNC(structuralTick);};
            };
        } forEach allUnits;
    }, 1, []] call CBA_fnc_addPerFrameHandler;
};

["CBA_settingsInitialized", {
    if (!GVAR(enable)) exitWith {};

    // Dust/rotor-wash effects are local presentation events.
    if (hasInterface) then {
        [QACEGVAR(goggles,effect), LINKFUNC(handleDustInjury)] call CBA_fnc_addEventHandler;
    };

    // Explosion injury state must exist for every casualty, not only ACE_player.
    ["CAManBase", "explosion", LINKFUNC(handleExplosion)] call CBA_fnc_addClassEventHandler;
}] call CBA_fnc_addEventHandler;

[QACEGVAR(medical_treatment,fullHealLocalMod), LINKFUNC(fullHealLocal)] call CBA_fnc_addEventHandler;
[QACEGVAR(medical_gui,updateInjuryListPart), LINKFUNC(gui_updateInjuryListPart)] call CBA_fnc_addEventHandler;
