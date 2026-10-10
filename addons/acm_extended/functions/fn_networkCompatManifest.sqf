/* Wire schema 1. Component stamps are read from each loaded PBO's own CfgPatches class. */
private _components = [];
{
    private _cfg = configFile >> "CfgPatches" >> _x;
    _components pushBack [_x, isClass _cfg, getText (_cfg >> "acmeBuildBatch"),
        getNumber (_cfg >> "acmeNetworkProtocol"), getText (_cfg >> "acmeComponent")];
} forEach [
    "ACM_main", "ACM_core", "ACM_airway", "ACM_breathing", "ACM_circulation", "ACM_cbrn",
    "ACM_damage", "ACM_disability", "ACM_evacuation", "ACM_gui", "ACM_mission", "ACM_zeus",
    "ACM_Extended", "ACM_itemtext"
];
[1, missionNamespace getVariable ["ACME_infusion_version", "?"],
    missionNamespace getVariable ["ACME_buildBatch", "?"],
    missionNamespace getVariable ["ACME_networkProtocol", 1],
    if (isServer) then {"server"} else {if (hasInterface) then {"client"} else {"HC"}}, _components]
