/* Batch 3 cumulative runtime registration. */
if (missionNamespace getVariable ["ACME_expansion_batch3_registered", false]) exitWith {};
missionNamespace setVariable ["ACME_expansion_batch3_registered", true];

[{
    // Invocation-scoped raw support rays only. Discovery and preoxygenation must stay adjacent;
    // do not insert geometry-changing gameplay work between these reads.
    private _acmeFlightSupportSamples = createHashMap;
    private _acmePerf = missionNamespace getVariable ["ACME_performance_enabled", false];
    private _acmePerfGeneration = if (_acmePerf) then {(missionNamespace getVariable ["ACME_performance_state", createHashMap]) get "generation"} else {-1};
    private _acmePerfStart = if (_acmePerf) then {diag_tickTime} else {0};
    call ACME_fnc_idlePhysDiscovery;
    if (_acmePerf) then {
        ["idlePhysDiscovery", (diag_tickTime - _acmePerfStart) * 1000, -1, _acmePerfGeneration] call ACME_fnc_performanceRecord;
        _acmePerfStart = diag_tickTime;
    };
    call ACME_fnc_preoxygenationTick;
    if (_acmePerf) then {["preoxygenationTick", (diag_tickTime - _acmePerfStart) * 1000, -1, _acmePerfGeneration] call ACME_fnc_performanceRecord;};
}, 1, []] call CBA_fnc_addPerFrameHandler;
[{ call ACME_fnc_shockPhenotypeTick; }, 0.5, []] call CBA_fnc_addPerFrameHandler;
[{
    private _acmePerf = missionNamespace getVariable ["ACME_performance_enabled", false];
    private _acmePerfGeneration = if (_acmePerf) then {(missionNamespace getVariable ["ACME_performance_state", createHashMap]) get "generation"} else {-1};
    private _acmePerfStart = if (_acmePerf) then {diag_tickTime} else {0};
    call ACME_fnc_coagulationTick;
    if (_acmePerf) then {["coagulationTick", (diag_tickTime - _acmePerfStart) * 1000, -1, _acmePerfGeneration] call ACME_fnc_performanceRecord;};
}, 0.20, []] call CBA_fnc_addPerFrameHandler;
[{ call ACME_fnc_aspirationTick; }, 0.5, []] call CBA_fnc_addPerFrameHandler;
[{ call ACME_fnc_megacodeAARTick; }, 1, []] call CBA_fnc_addPerFrameHandler;

["ACME_megacodeAARReset", {
    params ["_u"];
    if (!isNull _u && {local _u}) then {[_u] call ACME_fnc_megacodeAARReset;};
}] call CBA_fnc_addEventHandler;

// Instructor surfaces live on the existing Megacode laptop, so there is no second control panel to maintain.
if ((hasInterface || isServer) && {!isNil "ace_interact_menu_fnc_createAction"}) then {
    private _aar = [
        "ACME_MegacodeAAR",
        "Generate Objective AAR",
        "\a3\ui_f\data\IGUI\Cfg\Actions\heal_ca.paa",
        { [(_target getVariable ["ACME_megacodeDummy",objNull]),_player] call ACME_fnc_megacodeAARShow; },
        { _target getVariable ["ACME_isMegacodeLaptop",false] }
    ] call ace_interact_menu_fnc_createAction;
    ["Land_Laptop_03_olive_F",0,["ACE_MainActions"],_aar] call ace_interact_menu_fnc_addActionToClass;

    private _aarReset = [
        "ACME_MegacodeAARReset",
        "Reset AAR Timeline",
        "\a3\ui_f\data\IGUI\Cfg\Actions\heal_ca.paa",
        {
            private _d = _target getVariable ["ACME_megacodeDummy",objNull];
            if (!isNull _d) then {["ACME_megacodeAARReset",[_d],_d] call CBA_fnc_targetEvent;};
        },
        { _target getVariable ["ACME_isMegacodeLaptop",false] }
    ] call ace_interact_menu_fnc_createAction;
    ["Land_Laptop_03_olive_F",0,["ACE_MainActions"],_aarReset] call ace_interact_menu_fnc_addActionToClass;

    private _shockRoot = [
        "ACME_MegacodeShock",
        "Shock Phenotype",
        "\a3\ui_f\data\IGUI\Cfg\Actions\heal_ca.paa",
        {},
        { _target getVariable ["ACME_isMegacodeLaptop",false] }
    ] call ace_interact_menu_fnc_createAction;
    ["Land_Laptop_03_olive_F",0,["ACE_MainActions"],_shockRoot] call ace_interact_menu_fnc_addActionToClass;

    private _shockAuto = ["ACME_ShockAuto","Auto / Clear Forced Shock","",{
        private _d = _target getVariable ["ACME_megacodeDummy",objNull]; if (!isNull _d) then {[_d,"auto",0] call ACME_fnc_shockSetPhenotype;};
    },{true}] call ace_interact_menu_fnc_createAction;
    ["Land_Laptop_03_olive_F",0,["ACE_MainActions","ACME_MegacodeShock"],_shockAuto] call ace_interact_menu_fnc_addActionToClass;
    private _shockHem = ["ACME_ShockHem","Hemorrhagic Shock","",{
        private _d = _target getVariable ["ACME_megacodeDummy",objNull]; if (!isNull _d) then {[_d,"hemorrhagic",0.75] call ACME_fnc_shockSetPhenotype;};
    },{true}] call ace_interact_menu_fnc_createAction;
    ["Land_Laptop_03_olive_F",0,["ACE_MainActions","ACME_MegacodeShock"],_shockHem] call ace_interact_menu_fnc_addActionToClass;
    private _shockDis = ["ACME_ShockDis","Distributive Shock","",{
        private _d = _target getVariable ["ACME_megacodeDummy",objNull]; if (!isNull _d) then {[_d,"distributive",0.75] call ACME_fnc_shockSetPhenotype;};
    },{true}] call ace_interact_menu_fnc_createAction;
    ["Land_Laptop_03_olive_F",0,["ACE_MainActions","ACME_MegacodeShock"],_shockDis] call ace_interact_menu_fnc_addActionToClass;
    private _shockCard = ["ACME_ShockCard","Cardiogenic Shock","",{
        private _d = _target getVariable ["ACME_megacodeDummy",objNull]; if (!isNull _d) then {[_d,"cardiogenic",0.75] call ACME_fnc_shockSetPhenotype;};
    },{true}] call ace_interact_menu_fnc_createAction;
    ["Land_Laptop_03_olive_F",0,["ACE_MainActions","ACME_MegacodeShock"],_shockCard] call ace_interact_menu_fnc_addActionToClass;
    private _shockObs = ["ACME_ShockObs","Obstructive Shock","",{
        private _d = _target getVariable ["ACME_megacodeDummy",objNull]; if (!isNull _d) then {[_d,"obstructive",0.75] call ACME_fnc_shockSetPhenotype;};
    },{true}] call ace_interact_menu_fnc_createAction;
    ["Land_Laptop_03_olive_F",0,["ACE_MainActions","ACME_MegacodeShock"],_shockObs] call ace_interact_menu_fnc_addActionToClass;
    private _shockNeuro = ["ACME_ShockNeuro","Neurogenic Shock","",{
        private _d = _target getVariable ["ACME_megacodeDummy",objNull]; if (!isNull _d) then {[_d,"neurogenic",0.75] call ACME_fnc_shockSetPhenotype;};
    },{true}] call ace_interact_menu_fnc_createAction;
    ["Land_Laptop_03_olive_F",0,["ACE_MainActions","ACME_MegacodeShock"],_shockNeuro] call ace_interact_menu_fnc_addActionToClass;
};

diag_log "[ACME][Expansion] Batch 3 registered: cumulative physiology + aspiration + Megacode AAR";
