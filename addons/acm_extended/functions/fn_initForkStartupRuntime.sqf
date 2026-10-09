ACME_infusion_version = getText (configFile >> "CfgPatches" >> "ACM_Extended" >> "version");
if (ACME_infusion_version == "") then { ACME_infusion_version = "1.2.4.1"; };
ACME_buildBatch = "B264";
ACME_debugRevision = "";
ACME_networkAuditRevision = "NA8-B264-1.2.4.1-candidate";

/*
 * B199 physical-dressing invariant.
 * ACE 3.21.2 compiles ace_medical_treatment_fnc_handleBandageOpening as final, so a CfgFunctions
 * replacement is rejected before gameplay. Keep advanced bandages enabled for ACM's treated-wound
 * bookkeeping, but make ACE's final reopening roll impossible on every machine. Only ACME's explicit
 * unsecured-clot path may create a spontaneous reopen.
 */
call ACM_core_fnc_suppressPhysicalBandageReopening;
// Re-assert after CBA's server-setting synchronization as well; this keeps JIP clients on the same invariant.
["CBA_settingsInitialized", {
    call ACM_core_fnc_suppressPhysicalBandageReopening;
}] call CBA_fnc_addEventHandler;
call ACME_fnc_chestSealNetInit;
[] call ACME_fnc_ventCustodyInit;
[] call ACME_fnc_aiProtectionInit;
[{ call ACME_fnc_ownerInit; }, []] call CBA_fnc_execNextFrame;
call ACME_fnc_registerManualPlateCarrierRuntime;

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
            [_target, true, true] call ACM_core_fnc_setLyingState;
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

// Independently verify the server/client/HC build manifests after event handlers are installed.
[] call ACME_fnc_networkCompatInit;
