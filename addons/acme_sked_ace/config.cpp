#include "..\main\script_build.hpp"
// SKED litter for ACE 3: lay out, strap a casualty in, drag (ACE), carry as a team, load into vehicles.
// Needs ACE 3 (medical, dragging, interaction) and CBA. Skipped without them; the models in acme_sked still work.
// Adapted from the supplied SKED model package for the shared transport runtime.

class CfgPatches {
    class acme_sked_ace {
        ACME_BUILD_CONFIG("acme_sked_ace");
        name = "ACM Extended SKED: litter";
        author = "mavis";
        requiredVersion = 2.0;
        requiredAddons[] = {"acme_sked", "acme_talon", "cba_main", "ace_common", "ace_interact_menu", "ace_interaction", "ace_dragging", "ace_medical_treatment", "A3_Structures_F_Mil_Helipads"};
        skipWhenMissingDependencies = 1;
        units[] = {"ACME_Talon_Open", "ACME_Talon_Folded"};
        weapons[] = {};
    };
};

class CfgFunctions {
    class acme_sked {
        tag = "acme_sked";
        class sked {
            file = "\acme_sked_ace\functions";
            class align {};
            class auditTransport {};
            class bearerLimits {};
            class patientRoot {};
            class patientPose {};
            class placeLocal {};
            class gearDrop {};
            class gearHide {};
            class gearShow {};
            class carryBand {};
            class carryBandEnd {};
            class carryCan {};
            class carryNear {};
            class carryRearLocal {};
            class carryRearStop {};
            class carrySrvBegin {};
            class carrySrvEnd {};
            class dragAction {};
            class dragCan {};
            class dragDustLocal {};
            class dragSoundLocal {};
            class dragFree {};
            class dragGround {};
            class dragLie {};
            class dragLocal {};
            class dragOnto {};
            class dragPace {};
            class dragSrvBegin {};
            class dragSrvEnd {};
            class dragStart {};
            class dragStop {};
            class dragStrapAim {};
            class dragStrapClass {};
            class paceApply {};
            class orientLocal {};
            class placeAbort {};
            class strapBegin {};
            class strapAbort {};
            class preferredLitter {};
            class traceTransport {};
            class applyLocal {};
            class request {};
            class sendLocal {};
            class attachLocal {};
            class bearerLocal {};
            class bearerRelease {};
            class canHandleEmpty {};
            class canLayOutItem {};
            class canLift {};
            class canLoadVehicle {};
            class canStrapIn {};
            class canStrapNearest {};
            class canTakeHandle {};
            class canUnstrap {};
            class canUnstrapLitter {};
            class findCasualty {};
            class findLitter {};
            class hpmkSwap {};
            class layOut {};
            class layOutItem {};
            class letGo {};
            class lift {};
            class loadLocal {};
            class loadVehicle {};
            class loadVehicleActions {};
            class menuPos {};
            class pickUp {};
            class place {};
            class poseGuard {};
            class reattach {};
            class releaseLocal {};
            class rollUp {};
            class selPos {};
            class setDown {};
            class slungUpdate {};
            class slideCan {};
            class slideLocal {};
            class srvDragOff {};
            class srvDragOn {};
            class srvLetGo {};
            class srvLift {};
            class srvLoad {};
            class stageHpmk {};
            class srvRelease {};
            class srvRestore {};
            class srvSetDown {};
            class srvStow {};
            class srvTakeHandle {};
            class srvUnstrap {};
            class strapAnim {};
            class strapArcs {};
            class strapProgress {};
            class strapStage {};
            class strapFit {};
            class strapIn {};
            class strapNearest {};
            class strapActions {};
            class takeHandle {};
            class talonSteps {};
            class talonTransition {};
            class unstrap {};
            class unstrapLitter {};
            class vehicleLitter {};
            class vehicleLitterClear {};
            class vehicleLitterNear {};
            class vehicleLitterSpot {};
            class srvVehicleLitter {};
            class validCasualty {};
        };
    };
};

class CfgRemoteExec {
    class Functions {
        class acme_sked_fnc_request {allowedTargets = 2; jip = 0;};
        class acme_sked_fnc_applyLocal {allowedTargets = 0; jip = 0;};
    };
};

class Extended_PreInit_EventHandlers {
    class acme_sked_ace {
        init = "call compile preprocessFileLineNumbers '\acme_sked_ace\XEH_preInit.sqf'";
    };
};
class Extended_PostInit_EventHandlers {
    class acme_sked_ace {
        init = "call compile preprocessFileLineNumbers '\acme_sked_ace\XEH_postInit.sqf'";
    };
};

// Poses of a casualty on a litter (tools/build_litter_poses.py). The trunk and head are those of ACM_LyingState;
// only the limbs differ.
class CfgMovesBasic;
class CfgMovesMaleSdr: CfgMovesBasic {
    class States {
        class ainjppnemstpsnonwrfldnon;
        class ACME_Litter_Side: ainjppnemstpsnonwrfldnon {
            file = "\acme_sked_ace\anim\acme_litter_side.rtm";
            speed = -100;
            looped = 1;
            disableWeapons = 1;
            disableWeaponsLong = 1;
            showWeaponAim = 0;
            canPullTrigger = 0;
            duty = 0.2;
            limitGunMovement = 0;
            aiming = "aimingNo";
            aimingBody = "aimingUpNo";
            head = "headNo";
            ConnectTo[] = {};
            forceAim = 1;
            InterpolateTo[] = {};
        };
        // A casualty who is dragged by the collar (tools/build_drag_poses.py): the pose, held, and the same
        // with loose limbs, one second long, while he is moved.
        class ACME_Drag_Rest: ACME_Litter_Side {
            file = "\acme_sked_ace\anim\acme_drag_rest.rtm";
        };
        class ACME_Drag_Limp: ACME_Litter_Side {
            file = "\acme_sked_ace\anim\acme_drag_limp.rtm";
            speed = -1.05;
        };
    };
};

class CBA_Extended_EventHandlers;
class CfgVehicles {
    class ThingX;
    class NonStrategic;
    // What a dragged thing hangs on while it follows the rescuer (fn_dragLocal.sqf): static, invisible, nothing
    // to collide with. (Not a helipad class, though it borrows the invisible helipad's model: AI pilots land on
    // helipads.)
    class ACME_DragCarrier: NonStrategic {
        author = "mavis";
        scope = 1;
        scopeCurator = 0;
        displayName = "";
        model = "\A3\Structures_F\Mil\Helipads\HelipadEmpty_F.p3d";
        destrType = "DestructNo";
    };
    // ACE reads the drag, carry and cargo properties at init through CBA's extended event handlers.
    class ACME_SKED_Base: ThingX {
        author = "mavis";
        dlc = "ACM_Extended";
        class EventHandlers {
            class CBA_Extended_EventHandlers: CBA_Extended_EventHandlers {};
        };
    };
    class ACME_SKED_Pack: ACME_SKED_Base {
        class ACE_Actions {
            class ACE_MainActions {
                displayName = "Interactions";
                selection = "";
                distance = 2.5;
                condition = "true";
                class acme_sked_pickUp {
                    displayName = "Pick up SKED";
                    icon = "\acme_sked\data\ui\icon_sked_ca.paa";
                    condition = "[_player, _target] call acme_sked_fnc_canHandleEmpty";
                    statement = "[_player, _target] call acme_sked_fnc_pickUp";
                };
                class acme_sked_layOutPack {
                    displayName = "Lay out SKED";
                    icon = "\acme_sked\data\ui\icon_sked_ca.paa";
                    condition = "[_player, _target] call acme_sked_fnc_canHandleEmpty";
                    statement = "[_player, _target] call acme_sked_fnc_layOut";
                };
            };
        };
    };
    class ACME_SKED_Rolled: ACME_SKED_Pack {
        class ACE_Actions: ACE_Actions {
            class ACE_MainActions: ACE_MainActions {};
        };
    };
    class ACME_SKED_Open: ACME_SKED_Base {
        class ACE_Actions {
            // "Drag" is on the handle of the tow strap: a node of its own at the strap's end (memory point "tow"),
            // away from the litter's menu in its middle.
            class acme_drag_strap {
                displayName = "Drag";
                icon = "\acme_sked\data\ui\icon_sked_ca.paa";
                selection = "tow";
                distance = 2.5;
                condition = "[_player, _target] call acme_sked_fnc_dragCan";
                statement = "[_player, _target] call acme_sked_fnc_dragStart";
            };
            class ACE_MainActions {
                displayName = "SKED";
                selection = "center";
                // (over the litter, not on its deck among the casualty's own points: fn_menuPos.sqf)
                position = "[_target, 'mid'] call acme_sked_fnc_menuPos";
                distance = 3;
                condition = "true";
                class acme_sked_strapNearest {
                    displayName = "Load casualty";
                    icon = "\acme_sked\data\ui\icon_sked_ca.paa";
                    condition = "[_player, _target] call acme_sked_fnc_canStrapNearest";
                    statement = "";
                    insertChildren = "[_target, _player] call acme_sked_fnc_strapActions";
                };
                class acme_sked_rollUp {
                    displayName = "Roll up SKED";
                    icon = "\acme_sked\data\ui\icon_sked_ca.paa";
                    condition = "[_player, _target] call acme_sked_fnc_canHandleEmpty";
                    statement = "[_player, _target] call acme_sked_fnc_rollUp";
                };
                // An HPMK laid out ready on the empty litter: who is loaded onto it next is wrapped in it at once
                // (fn_stageHpmk.sqf). The Talon II has these two from here.
                class acme_sked_stageHpmk {
                    displayName = "Stage HPMK";
                    icon = "\acm_extended\ui\items\HPMK_ca.paa";
                    condition = "!(_target getVariable ['acme_sked_hpmkStaged', false]) && {'ACME_HPMK' in (items _player)} && {getText (configOf _target >> 'acmeHpmkStaged') != ''} && {[_player, _target] call acme_sked_fnc_canHandleEmpty}";
                    statement = "[_player, _target, 'start'] call acme_sked_fnc_stageHpmk";
                };
                class acme_sked_unstageHpmk {
                    displayName = "Take staged HPMK";
                    icon = "\acm_extended\ui\items\HPMK_ca.paa";
                    condition = "(_target getVariable ['acme_sked_hpmkStaged', false]) && {[_player, _target] call acme_sked_fnc_canHandleEmpty}";
                    statement = "[_player, _target, 'start'] call acme_sked_fnc_stageHpmk";
                };
            };
        };
    };
    class ACME_SKED_Wrapped: ACME_SKED_Base {
        class ACE_Actions {
            // "Drag" is on the handle of the tow strap: a node of its own at the strap's end (memory point "tow"),
            // away from the litter's menu in its middle.
            class acme_drag_strap {
                displayName = "Drag";
                icon = "\acme_sked\data\ui\icon_sked_ca.paa";
                selection = "tow";
                distance = 2.5;
                condition = "[_player, _target] call acme_sked_fnc_dragCan";
                statement = "[_player, _target] call acme_sked_fnc_dragStart";
            };
            class ACE_MainActions {
                displayName = "SKED";
                selection = "center";
                // (over the litter, not on its deck among the casualty's own points: fn_menuPos.sqf)
                position = "[_target, 'mid'] call acme_sked_fnc_menuPos";
                distance = 3;
                condition = "true";
                class acme_sked_takeHandle {
                    displayName = "Take a handle";
                    icon = "\acme_sked\data\ui\icon_sked_ca.paa";
                    condition = "[_player, _target] call acme_sked_fnc_canTakeHandle";
                    statement = "[_player, _target] call acme_sked_fnc_takeHandle";
                };
                class acme_sked_loadVehicle {
                    displayName = "Load into vehicle";
                    icon = "\acme_sked\data\ui\icon_sked_ca.paa";
                    condition = "[_player, _target] call acme_sked_fnc_canLoadVehicle";
                    statement = "";
                    insertChildren = "_this call acme_sked_fnc_loadVehicleActions";
                };
                class acme_sked_unloadVehicle {
                    displayName = "Unload litter";
                    icon = "\acme_sked\data\ui\icon_sked_ca.paa";
                    condition = "!isNull (_target getVariable ['acme_sked_inVehicle', objNull])";
                    statement = "[_player, _target, _target getVariable ['acme_sked_inVehicle', objNull], false] call acme_sked_fnc_vehicleLitter";
                };
                class acme_sked_unstrapObj {
                    displayName = "Unstrap casualty";
                    icon = "\acme_sked\data\ui\icon_sked_ca.paa";
                    condition = "[_player, _target] call acme_sked_fnc_canUnstrapLitter";
                    statement = "[_player, _target] call acme_sked_fnc_unstrapLitter";
                };
            };
        };
    };

    #include "Talon.hpp"

    // Self actions: lay out a SKED from the inventory; for a rescuer on a handle, lift, set down, let go.
    class Man;
    class CAManBase: Man {
        class ACE_Actions {
            class ACE_MainActions {
                class acme_drag {
                    displayName = "Drag behind you";
                    condition = "[_player, _target] call acme_sked_fnc_dragCan";
                    statement = "[_player, _target] call acme_sked_fnc_dragStart";
                };
                // on the rescuer who drags a litter by its head end: take its foot end (the litter itself is
                // claimed by him while he drags it, and ACE shows nobody else its menu)
                class acme_carry {
                    displayName = "Lift the foot end of the litter";
                    icon = "\acme_sked\data\ui\icon_sked_ca.paa";
                    condition = "[_player, _target getVariable ['acme_drag_target', objNull]] call acme_sked_fnc_carryCan";
                    statement = "[_player, 'carryRear', _target getVariable ['acme_drag_target', objNull]] call acme_sked_fnc_request";
                };
                class acme_sked_loadAtHips {
                    displayName = "Load into nearby SKED";
                    selection = "pelvis";
                    distance = 3.5;
                    icon = "\acme_sked\data\ui\icon_sked_ca.paa";
                    condition = "[_player, _target] call acme_sked_fnc_canStrapIn && {!isNull ([_target, true] call acme_sked_fnc_findLitter)}";
                    statement = "[_player, [_target, true] call acme_sked_fnc_findLitter, _target] call acme_sked_fnc_strapNearest";
                };
            };
        };
        class ACE_SelfActions {
            class acme_carry_take {
                displayName = "Lift the foot end of the litter";
                icon = "\acme_sked\data\ui\icon_sked_ca.paa";
                condition = "!isNull ([_player] call acme_sked_fnc_carryNear)";
                statement = "[_player, 'carryRear', [_player] call acme_sked_fnc_carryNear] call acme_sked_fnc_request";
            };
            class acme_carry_letGo {
                displayName = "Set the foot end down";
                icon = "\acme_sked\data\ui\icon_sked_ca.paa";
                condition = "!isNull (_player getVariable ['acme_carry_litter', objNull])";
                statement = "[_player, true] call acme_sked_fnc_carryRearStop";
            };
            class ACE_Equipment {
                class acme_sked_layOutItem {
                    displayName = "Lay out SKED";
                    icon = "\acme_sked\data\ui\icon_sked_ca.paa";
                    condition = "[_player] call acme_sked_fnc_canLayOutItem";
                    statement = "[_player] call acme_sked_fnc_layOutItem";
                };
            };
            class acme_drag_letGo {
                displayName = "Let go";
                condition = "!isNil {_player getVariable 'acme_drag_state'}";
                statement = "[_player, true] call acme_sked_fnc_dragStop";
                exceptions[] = {"isNotDragging", "isNotCarrying", "acme_sked_notBearing"};
            };
            class acme_sked_diagnostics {
                displayName = "Audit nearby medical transport";
                condition = "missionNamespace getVariable ['acme_sked_debug', false]";
                statement = "[_player] call acme_sked_fnc_auditTransport";
                exceptions[] = {"acme_sked_notBearing"};
            };
            class acme_sked_carry {
                displayName = "Litter team";
                icon = "\acme_sked\data\ui\icon_sked_ca.paa";
                condition = "!isNull (_player getVariable ['acme_sked_bearing', objNull])";
                statement = "";
                exceptions[] = {"acme_sked_notBearing"};
                class acme_sked_lift {
                    exceptions[] = {"acme_sked_notBearing"};
                    displayName = "Lift litter";
                    condition = "[_player] call acme_sked_fnc_canLift";
                    statement = "[_player] call acme_sked_fnc_lift";
                };
                class acme_sked_setDown {
                    exceptions[] = {"acme_sked_notBearing"};
                    displayName = "Set litter down";
                    condition = "(_player getVariable ['acme_sked_bearing', objNull]) getVariable ['acme_sked_lifted', false]";
                    statement = "[_player, _player getVariable ['acme_sked_bearing', objNull]] call acme_sked_fnc_setDown";
                };
                class acme_sked_letGo {
                    exceptions[] = {"acme_sked_notBearing"};
                    displayName = "Let go of handle";
                    condition = "true";
                    statement = "[_player] call acme_sked_fnc_letGo";
                };
            };
        };
    };
};

// ACE medical menu, Body: "Strap into nearby litter" (a laid out SKED within 3.5 m) and "Unstrap from litter".
class ace_medical_treatment_actions {
    class BasicBandage;
    class ACME_SKED_StrapIn: BasicBandage {
        displayName = "Load into nearby litter";
        displayNameProgress = "Packaging casualty in litter...";
        icon = "\acme_sked\data\ui\icon_sked_ca.paa";
        category = "advanced";
        items[] = {};
        consumeItem = 0;
        medicRequired = 0;
        allowSelfTreatment = 0;
        allowedSelections[] = {"Body"};
        treatmentLocations = 0;
        treatmentTime = 10;
        condition = "[_medic, _patient] call acme_sked_fnc_canStrapIn";
        // The casualty is laid on the litter while the timer runs; a broken off timer leaves them lying on it.
        callbackStart = "acme_sked_fnc_strapBegin";
        // the medic's animation lasts as long as the timer
        callbackProgress = "acme_sked_fnc_strapProgress";
        callbackFailure = "acme_sked_fnc_strapAbort";
        callbackSuccess = "acme_sked_fnc_strapIn";
        litter[] = {};
    };
    class ACME_SKED_Unstrap: ACME_SKED_StrapIn {
        displayName = "Unstrap from SKED";
        displayNameProgress = "Unstrapping...";
        treatmentTime = 8;
        condition = "[_medic, _patient] call acme_sked_fnc_canUnstrap";
        callbackStart = "";
        callbackProgress = "";
        callbackFailure = "";
        callbackSuccess = "acme_sked_fnc_unstrap";
    };
};
