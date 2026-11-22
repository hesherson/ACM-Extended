#define ACME_TALON_GEOMETRY \
    model = "\acme_talon\talon_open.p3d"; \
    mapSize = 2.3; \
    acmeLitterOpen = "ACME_Talon_Open"; \
    acmeLitterOccupied = "ACME_Talon_Occupied"; \
    acmeLitterChestPoint = "strap_chest"; \
    acmeLitterChest[] = {0, 0.55}; \
    acmeLitterBedHeight = 0.148; \
    acmeLitterPose = "ACME_Litter_Side"; \
    acmeLitterBag[] = {0, -0.36, 0.14}; \
    acmeLitterHandles[] = {"handle_hl", "handle_hr", "handle_fl", "handle_fr"}; \
    acmeLitterExtraCrew = 1; \
    acmeLitterStow[] = {0.58, 1.99, 0.46}; \
    acmeDragLift = 0.65; \
    acmeDragStrap = 0; \
    acmeStrapFitSources[] = {}; \
    acmeStrapArcBare[] = {"\acme_talon\talon_strap_legs_bare.p3d", "\acme_talon\talon_strap_chest_bare.p3d"}; \
    acmeStrapArcHpmk[] = {"\acme_talon\talon_strap_legs_hpmk.p3d", "\acme_talon\talon_strap_chest_hpmk.p3d"}; \
    acmeStrapArcHpmkOpen[] = {"\acme_talon\talon_strap_legs_hpmk.p3d", "\A3\Weapons_F\empty.p3d"}; \
    acmeStrapArcSources[] = {"strap_legs_over", "strap_chest_over"}; \
    acmeHpmkStaged = "\acme_hpmk\hpmk_staged_talon.p3d"; \
    acmeHpmkUnder = "\acme_hpmk\hpmk_under_talon.p3d"; \
    acmeDragReach = 0.38

    class ACME_Talon_Open: ACME_SKED_Open {
        ACME_TALON_GEOMETRY;
        displayName = "Talon II (deployed)";
        ace_dragging_canDrag = 0;
        ace_dragging_carryPosition[] = {0, 1.4, 0.8};
        ace_dragging_carryDirection = 0;
        ace_cargo_size = 2;
        class AnimationSources {
            class fold {source = "user"; animPeriod = 12; initPhase = 0;};
            class handles {source = "user"; animPeriod = 4; initPhase = 0;};
            // a strap of the deck is taken up and closed over the casualty (fn_strapArcs.sqf)
            class strap_legs_over {source = "user"; animPeriod = 0.01; initPhase = 0;};
            class strap_chest_over {source = "user"; animPeriod = 0.01; initPhase = 0;};
        };
        class ACE_Actions: ACE_Actions {
            // (the Talon has no tow strap: the SKED's node at the strap's end is never there; "Drag" is at the head end)
            class acme_drag_strap: acme_drag_strap {condition = "false";};
            // The two ends of the litter have a point each, over their handles: what is done by the handles is
            // there ("move the options for grabbing handles to each end of the talon, and just keep the Load
            // Patient option and folding options in the middle", 2026-11-20).
            class acme_talon_head {
                displayName = "Head end";
                icon = "\acme_sked\data\ui\icon_sked_ca.paa";
                position = "[_target, 'head'] call acme_sked_fnc_menuPos";
                distance = 2.5;
                condition = "[_player, _target] call acme_sked_fnc_dragCan";
                statement = "";
                class acme_drag {
                    displayName = "Drag";
                    icon = "\acme_sked\data\ui\icon_sked_ca.paa";
                    condition = "[_player, _target] call acme_sked_fnc_dragCan";
                    statement = "[_player, _target] call acme_sked_fnc_dragStart";
                };
            };
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
        // both straps are closed over the casualty: the ones on the deck are not there
        class AnimationSources {
            // (the handles are pushed in when the litter lies in a helicopter: fn_srvVehicleLitter.sqf)
            class handles {source = "user"; animPeriod = 4; initPhase = 0;};
            class strap_legs_over {source = "user"; animPeriod = 0.01; initPhase = 1;};
            class strap_chest_over {source = "user"; animPeriod = 0.01; initPhase = 1;};
        };
        class ACE_Actions: ACE_Actions {
            // (the Talon has no tow strap: the SKED's node at the strap's end is never there; "Drag" is at the head end)
            class acme_drag_strap: acme_drag_strap {condition = "false";};
            // The two ends of the litter have a point each, over their handles: what is done by the handles is
            // there ("move the options for grabbing handles to each end of the talon, and just keep the Load
            // Patient option and folding options in the middle", 2026-11-20).
            class acme_talon_head {
                displayName = "Head end";
                icon = "\acme_sked\data\ui\icon_sked_ca.paa";
                position = "[_target, 'head'] call acme_sked_fnc_menuPos";
                distance = 2.5;
                // (in brackets as a whole: ACE adds "&& {canInteractWith}" behind it, and && is done before ||.
                // Without them "{...canTakeHandle} && {...}" stood alone: "Error &&: Type code, expected Bool")
                condition = "([_player, _target] call acme_sked_fnc_dragCan || {[_player, _target, 0] call acme_sked_fnc_canTakeHandle})";
                statement = "";
                class acme_sked_takeHandle {
                    displayName = "Take a handle";
                    icon = "\acme_sked\data\ui\icon_sked_ca.paa";
                    condition = "[_player, _target, 0] call acme_sked_fnc_canTakeHandle";
                    statement = "[_player, _target, 0] call acme_sked_fnc_takeHandle";
                };
                class acme_drag {
                    displayName = "Drag";
                    icon = "\acme_sked\data\ui\icon_sked_ca.paa";
                    condition = "[_player, _target] call acme_sked_fnc_dragCan";
                    statement = "[_player, _target] call acme_sked_fnc_dragStart";
                };
            };
            class acme_talon_foot {
                displayName = "Foot end";
                icon = "\acme_sked\data\ui\icon_sked_ca.paa";
                position = "[_target, 'foot'] call acme_sked_fnc_menuPos";
                distance = 2.5;
                condition = "[_player, _target, 1] call acme_sked_fnc_canTakeHandle";
                statement = "";
                class acme_sked_takeHandle {
                    displayName = "Take a handle";
                    icon = "\acme_sked\data\ui\icon_sked_ca.paa";
                    condition = "[_player, _target, 1] call acme_sked_fnc_canTakeHandle";
                    statement = "[_player, _target, 1] call acme_sked_fnc_takeHandle";
                };
            };
            class ACE_MainActions: ACE_MainActions {
                displayName = "Talon II";
                selection = "";
                // (the handles are taken at the ends)
                class acme_sked_takeHandle: acme_sked_takeHandle {condition = "false";};
            };
        };
    };
    // The litter in four parts, one for each segment: they show the fold and the unfold in place of the litter
    // (fn_talonTransition.sqf; why four: acme_talon, tools/build_talon_fold_parts.py).
    class ACME_Talon_FoldPart_1: ACME_DragCarrier {
        model = "\acme_talon\talon_fold_1.p3d";
        class AnimationSources {
            class fold {source = "user"; animPeriod = 12; initPhase = 0;};
            class handles {source = "user"; animPeriod = 4; initPhase = 0;};
        };
    };
    class ACME_Talon_FoldPart_2: ACME_Talon_FoldPart_1 {model = "\acme_talon\talon_fold_2.p3d";};
    class ACME_Talon_FoldPart_3: ACME_Talon_FoldPart_1 {model = "\acme_talon\talon_fold_3.p3d";};
    class ACME_Talon_FoldPart_4: ACME_Talon_FoldPart_1 {model = "\acme_talon\talon_fold_4.p3d";};
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
                class acme_drag {
                    displayName = "Drag behind you";
                    condition = "[_player, _target] call acme_sked_fnc_dragCan";
                    statement = "[_player, _target] call acme_sked_fnc_dragStart";
                };
                class acme_talon_unfold {
                    displayName = "Deploy Talon II";
                    condition = "[_player, _target] call acme_sked_fnc_canHandleEmpty";
                    statement = "[_player, 'deployTalon', _target] call acme_sked_fnc_request";
                };
            };
        };
    };
#undef ACME_TALON_GEOMETRY
