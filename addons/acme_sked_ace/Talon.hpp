#define ACME_TALON_GEOMETRY \
    model = "\acme_talon\talon_open.p3d"; \
    mapSize = 2.3; \
    acmeLitterOpen = "ACME_Talon_Open"; \
    acmeLitterOccupied = "ACME_Talon_Occupied"; \
    acmeLitterChestPoint = "strap_chest"; \
    acmeLitterHandles[] = {"handle_hl", "handle_hr", "handle_fl", "handle_fr"}; \
    acmeLitterExtraCrew = 1

    class ACME_Talon_Open: ACME_SKED_Open {
        ACME_TALON_GEOMETRY;
        displayName = "Talon II (deployed)";
        ace_dragging_canDrag = 0;
        ace_dragging_carryPosition[] = {0, 1.4, 0.8};
        ace_dragging_carryDirection = 0;
        ace_cargo_size = 2;
        class ACE_Actions: ACE_Actions {
            class ACE_MainActions: ACE_MainActions {
                displayName = "Talon II";
                selection = "";
                class acme_sked_rollUp: acme_sked_rollUp {
                    displayName = "Fold Talon II";
                    statement = "[_player, 'foldTalon', _target] call acme_sked_fnc_request";
                };
            };
        };
    };
    class ACME_Talon_Occupied: ACME_SKED_Wrapped {
        ACME_TALON_GEOMETRY;
        scope = 1;
        displayName = "Talon II (occupied)";
        ace_dragging_canDrag = 0;
        class ACE_Actions: ACE_Actions {
            class ACE_MainActions: ACE_MainActions {
                displayName = "Talon II";
                selection = "";
            };
        };
    };
    class ACME_Talon_Folded: ACME_SKED_Base {
        scope = 2;
        scopeCurator = 2;
        displayName = "Talon II (folded)";
        model = "\acme_talon\talon_folded.p3d";
        mapSize = 0.6;
        ace_dragging_canCarry = 1;
        ace_dragging_carryPosition[] = {0, 0.7, 0.9};
        ace_cargo_size = 1;
        ace_cargo_canLoad = 1;
        class ACE_Actions {
            class ACE_MainActions {
                displayName = "Talon II";
                selection = "center";
                distance = 3;
                condition = "true";
                class acme_talon_unfold {
                    displayName = "Deploy Talon II";
                    condition = "[_player, _target] call acme_sked_fnc_canHandleEmpty";
                    statement = "[_player, 'deployTalon', _target] call acme_sked_fnc_request";
                };
            };
        };
    };
#undef ACME_TALON_GEOMETRY
