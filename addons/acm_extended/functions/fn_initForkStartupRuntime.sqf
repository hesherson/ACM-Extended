ACME_infusion_version = getText (configFile >> "CfgPatches" >> "ACM_Extended" >> "version");
if (ACME_infusion_version == "") then { ACME_infusion_version = "1.3.0"; };
ACME_buildBatch = "DEV-130-PHYS1";
ACME_debugRevision = "PHYS1";
ACME_networkAuditRevision = "NA3-1.3.0-dev";
call ACME_fnc_chestSealNetInit;
[] call ACME_fnc_ventCustodyInit;
[{ call ACME_fnc_ownerInit; }, []] call CBA_fnc_execNextFrame;

// ACE prepares ace_dragging_fnc_dropObject_carry from its own source during startup, so attempting to own that
// function through CfgFunctions creates a load-order race. Preserve ACME's only required post-drop behavior on
// ACE's public stoppedCarry event instead. This runs after native carry cleanup and cannot become stale when ACE
// recompiles its function.
if (isNil "ACME_dropCarryLyingEH") then {
    ACME_dropCarryLyingEH = ["ace_dragging_stoppedCarry", {
        params ["_carrier", "_target", ["_loaded", false]];
        if (isNull _target || {_loaded} || {!(_target isKindOf "CAManBase")} || {!isNull objectParent _target}) exitWith {};

        private _unconscious = _target getVariable ["ACE_isUnconscious", false];
        private _lyingRaw = _target getVariable ["ACM_core_Lying_State", false];
        private _lying = if (_lyingRaw isEqualType true) then {_lyingRaw} else {_lyingRaw > 0};

        if (_unconscious && {!_lying}) then {
            _target setVariable ["ACM_core_Lying_State", true, true];
            _lying = true;
        };

        if (_unconscious || {_lying}) then {
            ["ace_common_switchMove", [_target, "ACM_LyingState"]] call CBA_fnc_globalEvent;
        };

        if (!_unconscious && {_lying}) then {
            ["ACM_core_getUpPrompt", [_target], _target] call CBA_fnc_targetEvent;
        };
    }] call CBA_fnc_addEventHandler;
};

// Cumulative clinical-expansion bootstrap. Kept on this executed startup path because
// ACM Extended's current config.cpp inlines its XEH declarations; the legacy standalone
// CfgEventHandlers.hpp is not the authoritative registration surface.
call compile preprocessFileLineNumbers "\acm_extended\functions\fn_expansionBootstrap.sqf";
