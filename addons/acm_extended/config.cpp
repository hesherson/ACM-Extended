// extended event handlers, matching the ACM and ACE convention. these are inlined from the former
// cfgeventhandlers.hpp, so the build has no #include to drop in.
// preinit registers the CBA settings. postinit starts the runtime of the addon.
class Extended_PreInit_EventHandlers {
    class ACM_Extended {
        init = "call compile preprocessFileLineNumbers '\acm_extended\XEH_preInit.sqf'";
    };
};

class Extended_PostInit_EventHandlers {
    class ACM_Extended {
        init = "call compile preprocessFileLineNumbers '\acm_extended\functions\fn_postInit.sqf'";
    };
};

// Pause-menu bridge for ACME's patient-focused diagnostic dump. CBA opens this empty display, the onLoad
// handler writes the snapshot, then closes immediately, mirroring ACE's own Debug To Clipboard option.
class RscDisplayEmpty;
class ACME_MainMenuHelperDumpDebug: RscDisplayEmpty {
    onLoad = "[] call ACME_fnc_debugDumpToClipboard; (_this select 0) closeDisplay 0;";
};

// the hang bag uses a dedicated copy of the crew-aid loop with forced freelook.
// ACE uses the same cfgmoves flags for its seated states. the body stays fixed and the head and camera stay
// free.
// Dedicated seizure gesture actions. These are separate aliases rather than global edits of BI's GestureSpasm
// states, so ACME gets the faster convulsion cadence without changing hit reactions or gestures used by other mods.
class CfgMovesBasic {
    class ManActions {
        ACME_SeizureSpasm3[] = {"ACME_SeizureSpasm3", "Gesture"};
        ACME_SeizureSpasm4[] = {"ACME_SeizureSpasm4", "Gesture"};
        ACME_SeizureSpasm5[] = {"ACME_SeizureSpasm5", "Gesture"};
        ACME_SeizureSpasm6[] = {"ACME_SeizureSpasm6", "Gesture"};
    };
};
class CfgMovesMaleSdr: CfgMovesBasic {
    class States {
        // B47 provider-treatment theatre. Each wrapper inherits the exact requested BI motion but disables
        // weapon use and adds short interpolation links to the normal empty-handed crouch. The runtime pose
        // controller owns timing, so ACM never needs to raise/holster a weapon to reach these states.
        class AinvPknlMstpSnonWnonDnon_medic4;
        class ACME_RollProviderWork: AinvPknlMstpSnonWnonDnon_medic4 {
            looped = 0;
            disableWeapons = 1;
            disableWeaponsLong = 1;
            disableWeaponsShort = 1;
            disableReload = 1;
            canPullTrigger = 0;
            enableOptics = 0;
            enableBinocular = 0;
            connectFrom[] = {"AmovPknlMstpSnonWnonDnon", 0.15};
            connectTo[] = {};
            interpolateFrom[] = {"AmovPknlMstpSnonWnonDnon", 0.15};
            interpolateTo[] = {"AmovPknlMstpSnonWnonDnon", 0.15, "Unconscious", 0.02};
        };
        class ACME_ChestInspectWork: AinvPknlMstpSnonWnonDnon_medic4 {
            looped = 0;
            disableWeapons = 1;
            disableWeaponsLong = 1;
            disableWeaponsShort = 1;
            disableReload = 1;
            canPullTrigger = 0;
            enableOptics = 0;
            enableBinocular = 0;
            connectFrom[] = {"AmovPknlMstpSnonWnonDnon", 0.15};
            connectTo[] = {};
            interpolateFrom[] = {"AmovPknlMstpSnonWnonDnon", 0.15};
            interpolateTo[] = {"AmovPknlMstpSnonWnonDnon", 0.15, "Unconscious", 0.02};
        };

        // Persistent hands-on-chest workspace pose. This deliberately does NOT inherit medic3:
        // medic3 is reserved exclusively for the moment a chest seal is actually applied. The CPR stop pose is
        // already a stable hands-planted-on-chest state, so the panel can remain open without replaying a treatment.
        class ACM_CPR_Stop;
        class ACME_ChestSealWorkspace: ACM_CPR_Stop {
            looped = 1;
            disableWeapons = 1;
            disableWeaponsLong = 1;
            disableWeaponsShort = 1;
            disableReload = 1;
            canPullTrigger = 0;
            enableOptics = 0;
            enableBinocular = 0;
            connectFrom[] = {
                "AmovPknlMstpSnonWnonDnon", 0.12,
                "AinvPknlMstpSnonWnonDnon_medic4", 0.08
            };
            connectTo[] = {
                "AmovPknlMstpSnonWnonDnon", 0.12,
                "AinvPknlMstpSnonWnonDnon_medic4", 0.08
            };
            interpolateFrom[] = {
                "AmovPknlMstpSnonWnonDnon", 0.12,
                "AinvPknlMstpSnonWnonDnon_medic4", 0.08
            };
            interpolateTo[] = {
                "AmovPknlMstpSnonWnonDnon", 0.12,
                "AinvPknlMstpSnonWnonDnon_medic4", 0.08,
                "Unconscious", 0.02
            };
        };

        // Semi-Fowler states.
        //
        // THE RULE THAT DRIVES ALL OF THIS, MEASURED IN GAME ON 2026-09-11.
        // A state that is not a loop and has an empty ConnectTo does not play. The engine takes the first
        // InterpolateTo edge on the same frame. DraggerBase is proof: it has an empty ConnectTo and it never runs.
        // So every state below that must play has a ConnectTo, and every state that must persist is a loop.
        //
        // PROVIDER. ACME_HeadElevProviderLift inherits the vanilla drag pickup, which has the DraggerBase RTM and a
        // move graph that works. Only the exit changes: the pickup runs its full length, then the graph goes to
        // AcinPknlMstpSnonWnonDnon_AmovPknlMstpSnonWnonDnon. The weapon stays in the hands.
        //
        // PATIENT. The grab plays the lift once, then the graph holds ACME_HeadElevPatientHold.
        // The hold is the first frame of the release RTM, which is the casualty held up. It is a loop with a speed
        // of zero, so the frame never advances and the state never ends. This is how ace_dragging_static holds a
        // pose. No script is needed to keep the casualty up, and nothing can transition out on its own.
        // The lay-flat motion is requested directly, which is the only way out.
        class AmovPercMstpSlowWrflDnon_AcinPknlMwlkSlowWrflDb_1;
        class ACME_HeadElevProviderLift: AmovPercMstpSlowWrflDnon_AcinPknlMwlkSlowWrflDb_1 {
            looped = 0;
            ConnectTo[] = {"AcinPknlMstpSnonWnonDnon_AmovPknlMstpSnonWnonDnon", 0.12};
            InterpolateTo[] = {"AcinPknlMstpSnonWnonDnon_AmovPknlMstpSnonWnonDnon", 0.12};
        };
        class AinjPpneMrunSnonWnonDb_grab;
        class ACME_HeadElevPatientGrab: AinjPpneMrunSnonWnonDb_grab {
            looped = 0;
            ConnectTo[] = {"ACME_HeadElevPatientHold", 0.05};
            InterpolateTo[] = {"ACME_HeadElevPatientHold", 0.05};
        };
        class AinjPpneMrunSnonWnonDb_release;
        class ACME_HeadElevPatientHold: AinjPpneMrunSnonWnonDb_release {
            looped = 1;
            speed = 0;
            ConnectTo[] = {};
            InterpolateTo[] = {};
        };
        class ACME_HeadElevPatientRelease: AinjPpneMrunSnonWnonDb_release {
            looped = 0;
            // Lay-flat and chest-access release must finish supine, never in BI's injured-prone idle.
            ConnectTo[] = {"ACM_LyingState", 0.1};
            InterpolateTo[] = {"Unconscious", 0.02};
        };

        class AinvPknlMstpSnonWrflDr_medic3_old;
        class ACME_ResponseCheckWork: AinvPknlMstpSnonWrflDr_medic3_old {
            looped = 0;
            disableWeapons = 1;
            disableWeaponsLong = 1;
            disableWeaponsShort = 1;
            disableReload = 1;
            canPullTrigger = 0;
            enableOptics = 0;
            enableBinocular = 0;
            connectFrom[] = {"AmovPknlMstpSnonWnonDnon", 0.15};
            connectTo[] = {};
            interpolateFrom[] = {"AmovPknlMstpSnonWnonDnon", 0.15};
            interpolateTo[] = {"AmovPknlMstpSnonWnonDnon", 0.15, "Unconscious", 0.02};
        };

        class AinvPknlMstpSnonWrflDr_medic4_old;
        class ACME_AirwayCheckWork: AinvPknlMstpSnonWrflDr_medic4_old {
            looped = 0;
            disableWeapons = 1;
            disableWeaponsLong = 1;
            disableWeaponsShort = 1;
            disableReload = 1;
            canPullTrigger = 0;
            enableOptics = 0;
            enableBinocular = 0;
            connectFrom[] = {"AmovPknlMstpSnonWnonDnon", 0.15};
            connectTo[] = {};
            interpolateFrom[] = {"AmovPknlMstpSnonWnonDnon", 0.15};
            interpolateTo[] = {"AmovPknlMstpSnonWnonDnon", 0.15, "Unconscious", 0.02};
        };

        class ACME_JunctionalWork: AinvPknlMstpSnonWnonDnon_medic4 {
            looped = 1;
            disableWeapons = 1;
            disableWeaponsLong = 1;
            canPullTrigger = 0;
            connectTo[] = {};
            interpolateFrom[] = {"AmovPknlMstpSnonWnonDnon", 0.2};
            interpolateTo[] = {"AmovPknlMstpSnonWnonDnon", 0.2, "Unconscious", 0.02};
        };
        // B40 animation audit: direct pressure gets its own held state instead of hard switchMove into
        // ACM_CPR_Stop. The RTM is inherited from ACM, but the graph is connected to the normal unarmed
        // crouch so playMoveNow can interpolate into and out of the hold. This keeps the same visual pose
        // without the one-frame snap that switchMove produces.
        class ACME_DirectPressureHold: ACM_CPR_Stop {
            looped = 1;
            disableWeapons = 1;
            disableWeaponsLong = 1;
            canPullTrigger = 0;
            connectFrom[] = {"AmovPknlMstpSnonWnonDnon", 0.15};
            // B128: chest-seal Flip can take ownership directly from the pressure hold instead of waiting for a
            // neutral crouch round-trip. This is the literal medic4 Flip/Inspect-Chest motion requested by ACME.
            connectTo[] = {"AmovPknlMstpSnonWnonDnon", 0.15, "AinvPknlMstpSnonWnonDnon_medic4", 0.08};
            interpolateFrom[] = {"AmovPknlMstpSnonWnonDnon", 0.15, "AinvPknlMstpSnonWnonDnon_AinvPknlMstpSnonWnonDnon_medic", 0.10};
            interpolateTo[] = {"AmovPknlMstpSnonWnonDnon", 0.15, "AinvPknlMstpSnonWnonDnon_medic4", 0.08, "Unconscious", 0.02};
        };
        class UnconsciousReviveMedic_B;
        class ACME_StethoscopeWork: UnconsciousReviveMedic_B {
            looped = 1;
            disableWeapons = 1;
            disableWeaponsLong = 1;
            disableWeaponsShort = 1;
            disableReload = 1;
            canPullTrigger = 0;
            enableOptics = 0;
            enableBinocular = 0;
            // The frozen frame is controlled by treatmentPoseStart, not by trapping the state in the move graph.
            // Give treatmentPoseStop an authored route back to the normal unarmed crouch.
            connectTo[] = {"AmovPknlMstpSnonWnonDnon", 0.2};
            interpolateFrom[] = {"AmovPknlMstpSnonWnonDnon", 0.2};
            interpolateTo[] = {"AmovPknlMstpSnonWnonDnon", 0.2, "Unconscious", 0.02};
        };
        // shared restriction set for all three hang-bag states.
        class Acts_JetsCrewaidFCrouchThumbup_in;
        class ACM_GenericContinuous;
        class ACME_Acts_JetsCrewaidFCrouchThumbup_in: Acts_JetsCrewaidFCrouchThumbup_in {
            // entry. this is the raise-the-bag motion, played once when a medic hangs a bag. it auto-advances into our
            // held loop, so the hand comes up and then holds. the watchdog of the hang-bag tick is token-based, on
            // "jetscrewaidfcrouchthumbup", which this state contains, so the watchdog does not interrupt it.
            head = "headNo";
            aiming = "aimingNo";
            aimingBody = "aimingNo";
            forceAim = 1;
            static = 1;
            turnSpeed = 0;
            enableDirectControl = 0;
            canBlendStep = 0;
            disableWeapons = 1;
            disableWeaponsLong = 1;
            disableWeaponsShort = 1;
            disableReload = 1;
            canPullTrigger = 0;
            enableOptics = 0;
            enableBinocular = 0;
            // The inherited Jets crew-aid state carries movement sound events. ACME uses this animation only as
            // silent medical theatre, so disable inherited animation sounds and prevent jump_sfx lookups.
            soundEnabled = 0;
            looped = 0;
            connectFrom[] = {"AmovPknlMstpSnonWnonDnon", 0.20, "ACM_GenericContinuous", 0.15};
            interpolateFrom[] = {"AmovPknlMstpSnonWnonDnon", 0.20, "ACM_GenericContinuous", 0.15};
            connectTo[] = {};
            interpolateTo[] = {"ACME_Acts_JetsCrewaidFCrouchThumbup_loop", 1};
        };
        // obtunded-on-back pose. it is the acts lying-wounded look with the full forced-freelook lock set that the
        // hang-bag states above and ACM's lying state both prove. the body cannot rotate or move, and the mouse drives
        // the head camera only. it holds as a self-contained loop with the exits cleared, so the pose enforcer never
        // has to re-fire during a normal hold.
        class Acts_LyingWounded_loop3;
        class ACME_ObtundedBack: Acts_LyingWounded_loop3 {
            head = "headNo";
            aiming = "aimingNo";
            aimingBody = "aimingNo";
            forceAim = 1;
            static = 1;
            turnSpeed = 0;
            enableDirectControl = 0;
            canBlendStep = 0;
            disableWeapons = 1;
            disableWeaponsLong = 1;
            disableWeaponsShort = 1;
            disableReload = 1;
            canPullTrigger = 0;
            enableOptics = 0;
            enableBinocular = 0;
            speed = -100;
            looped = 1;
            interpolateTo[] = {};
            connectTo[] = {};
        };
        class Acts_JetsCrewaidFCrouchThumbup_loop;
        class ACME_Acts_JetsCrewaidFCrouchThumbup_loop: Acts_JetsCrewaidFCrouchThumbup_loop {
            head = "headNo";
            aiming = "aimingNo";
            aimingBody = "aimingNo";
            forceAim = 1;
            static = 1;
            turnSpeed = 0;
            enableDirectControl = 0;
            canBlendStep = 0;
            disableWeapons = 1;
            disableWeaponsLong = 1;
            disableWeaponsShort = 1;
            disableReload = 1;
            canPullTrigger = 0;
            enableOptics = 0;
            enableBinocular = 0;
            // The parent cinematic loop also carries sound edges intended for deck crew movement. The frozen
            // medical hold must be silent or Arma can repeatedly request the inherited jump_sfx class.
            soundEnabled = 0;
            // The stock cinematic loop carries RTM movement. Running it at its authored speed is what makes a player
            // drift across the terrain while simply holding the bag. Keep the first raised-bag frame effectively
            // stationary on every client, while still leaving an explicit interrupt path into the authored lower-bag
            // animation. The Hang Bag input lock owns movement; this state must never move the provider itself.
            speed = -1000000;
            looped = 1;
            connectFrom[] = {"AmovPknlMstpSnonWnonDnon", 0.15, "ACM_GenericContinuous", 0.15, "ACME_Acts_JetsCrewaidFCrouchThumbup_in", 0.05};
            interpolateFrom[] = {"AmovPknlMstpSnonWnonDnon", 0.15, "ACM_GenericContinuous", 0.15, "ACME_Acts_JetsCrewaidFCrouchThumbup_in", 0.05};
            connectTo[] = {};
            interpolateTo[] = {"ACME_Acts_JetsCrewaidFCrouchThumbup_out", 0.05, "AmovPknlMstpSnonWnonDnon", 0.15, "Unconscious", 0.02};
        };
        // exit. this is the lower-the-bag motion, played once when the medic cancels with RMB or esc. it must not
        // freeze the player, because static and enableDirectControl=0 are what got the medic stuck. it plays briefly,
        // then the stop function resets to a normal movable idle. weapons stay disabled so the rifle does not flash
        // out mid-lower, and control stays enabled so there is no way to get stuck even if the reset is missed.
        class Acts_JetsCrewaidFCrouchThumbup_out;
        class ACME_Acts_JetsCrewaidFCrouchThumbup_out: Acts_JetsCrewaidFCrouchThumbup_out {
            head = "headNo";
            aiming = "aimingNo";
            aimingBody = "aimingNo";
            static = 0;
            enableDirectControl = 1;
            canBlendStep = 1;
            disableWeapons = 1;
            disableWeaponsLong = 1;
            disableReload = 1;
            canPullTrigger = 0;
            enableOptics = 0;
            enableBinocular = 0;
            // Do not inherit the Jets deck-crew foot/jump sound edge on the lower-bag animation.
            soundEnabled = 0;
            looped = 0;
            // A non-looping exit with no ConnectTo can be skipped by the move graph. Give the hold a real route into
            // this state and let this state finish naturally into the normal empty-handed crouch.
            connectFrom[] = {"ACME_Acts_JetsCrewaidFCrouchThumbup_loop", 0.05};
            interpolateFrom[] = {"ACME_Acts_JetsCrewaidFCrouchThumbup_loop", 0.05};
            connectTo[] = {"AmovPknlMstpSnonWnonDnon", 0.12};
            interpolateTo[] = {"AmovPknlMstpSnonWnonDnon", 0.12, "Unconscious", 0.02};
        };
    };
};

class CfgPatches {
    class ACM_Extended {
        name = "ACM Extended";
        units[] = {"ACME_ModuleMegacodeKelly", "ACME_ModuleBloodFridge", "ACME_BloodFridge_Closed", "ACME_BloodFridge_Open",
            // zeus enumerates units[]. a module that is not in this list does not exist as far as the curator is
            // concerned, however correctly it is built and whatever its scopecurator says. these five were fully
            // implemented and completely unreachable.
            "ACME_ModuleInflictBlastLung", "ACME_ModuleInflictJunctional", "ACME_ModuleInduceObtundation",
            "ACME_ModuleInflictTBI", "ACME_ModuleClearTBI", "ACME_ModuleInsertIV",
            "ACME_ModuleInflictEdema", "ACME_ModuleClearEdema",
            "ACME_BloodCoolerBox_CSWB1U", "ACME_BloodCoolerBox_CSWB2U", "ACME_BloodCoolerBox_CSWB4U"};
        weapons[] = {
            "ACME_HTSBag", "ACME_MagnesiumBag", "ACME_MannitolBag",
            "ACM_EsmololBag", "ACM_Vial_Norepinephrine", "ACM_Vial_Ceftriaxone", "ACM_Vial_Rocuronium", "ACM_Vial_Sugammadex",
            "ACM_IV_18g", "ACM_IV_20g", "ACM_SalineFlush_10", "ACME_Vial_EpinephrineCardiac",
            "ACM_Thermometer", "ACM_NRBMask", "ACM_HPMK", "ACM_EMMA", "ACM_CombatGauze", "ACME_NARSPEAR", "ACME_XStat", "ACME_Ventilator", "ACME_VentBattery", "ACME_Laryngoscope", "ACME_ETTube",
            "ACME_HTSBullet", "ACME_MannitolVial",
            "ACME_PlasmaLyteBag", "ACME_PlasmaLyteBag_500", "ACME_PlasmaLyteBag_250", "ACME_PlasmaLyteBag_100",
            "ACME_SalineBag_50", "ACME_SalineBag_100", "ACME_Spray_Esketamine",
            "ACM_Vial_Phentolamine", "ACM_Vial_Hyaluronidase", "ACM_Vial_CalciumGluconate", "ACM_Vial_Propofol", "ACM_Vial_Midazolam", "ACM_Vial_Fentanyl",
            "ACME_IVLine", "ACME_YTubing", "ACME_BloodWarmer", "ACME_PressureInfuser", "ACME_NARBOA", "ACME_AAJT_S", "ACME_SpoiledBlood",
            "ACME_BloodCooler_CSWB1U", "ACME_BloodCooler_CSWB2U", "ACME_BloodCooler_CSWB4U"
        };
        requiredVersion = 2.18;
        requiredAddons[] = {
            "A3_Data_F",
            "A3_Anims_F",
            "cba_main",
            "ace_main",
            "ace_fastroping",
            "ace_interact_menu",
            "ace_map",
            "ace_medical_status",
            "ace_medical_treatment",
            "ace_medical_gui",
            "ACM_gui",
            "ACM_core",
            "ACM_damage",
            "ACM_circulation",
            "ACM_breathing",
            "ACM_airway",
            "ACM_disability"
        };
        author = "mavis";
        // Public release identity is stored in CfgPatches.version because every debug-overlay page reads this
        // exact value. It lets testers prove which PBO Arma actually loaded instead of guessing from a workshop
        // timestamp or repository state.
        version = "1.2.2.1";
        // Only HEMTT dev/launch output enables experimental development actions.
        acme_developmentBuild = 0;
    };
};


// ACM Extended inventory / Arsenal branding. ACME-owned inventory classes below opt into this
// CfgMods identity through dlc = "ACM_Extended", so the inventory/arsenal mod badge uses the
// supplied ACME artwork instead of an empty or generic addon mark.
class CfgMods {
    class ACM_Extended {
        dir = "@ACM Extended";
        name = "ACM Extended";
        picture = "\acm_extended\ui\ACME_logo.paa";
        logo = "\acm_extended\ui\ACME_logo.paa";
        logoOver = "\acm_extended\ui\ACME_logo.paa";
        logoSmall = "\acm_extended\ui\ACME_logo_small.paa";
        hidePicture = 0;
        hideName = 0;
        tooltip = "ACM Extended";
        tooltipOwned = "ACM Extended";
        actionName = "";
        action = "";
        overview = "ACM Extended";
        author = "mavis";
    };
};

// premixed iv bags. these are carryable medical items modeled on ACM's own bag-item pattern, ACE_ItemCore
// plus CBA_MiscItem_ItemInfo, exactly like acm_fieldbloodtransfusionkit. they are the inventory items the add
// bag panel hangs. the matching iv fluid classes, with type and volume, are defined under
// ace_medical_treatment below, and fn_syncpremixedbags attaches the drug each one carries through
// ACME_infusion_premixedByType.
// the paracetamol magazines, the carried and usable items, are renamed to acetaminophen. this is display only.
// the medication classname and effect stay paracetamol, so all ACM logic is untouched.
// a partial override, such as class ACM_Paracetamol { displayname=..; }, keeps the class's own properties and
// drops the CA_Magazine-inherited defaults, namesound, displayNameShort and the rest. that surfaced as a
// cascade of "No entry .../ACM_Paracetamol.<prop>" popups. we re-derive from CA_Magazine instead and copy
// ACM's full property set plus the base defaults, so nothing inherited is ever missing. ACM's children,
// ammoniainhalant, inhaler_penthrox and syringe_10_epinephrine, inherit from this and pick up the same
// complete chain.
class CfgMagazines {
    class CA_Magazine;
    class ACM_Paracetamol: CA_Magazine {
        scope = 2;
        author = "Blue";
        picture = "\x\ACM\addons\circulation\ui\paracetamol_ca.paa";
        displayName = "Acetaminophen";
        displayNameShort = "APAP";
        descriptionShort = "$STR_ACM_Circulation_Paracetamol_Desc";
        nameSound = "";
        ACE_isMedicalItem = 1;
        ACE_asItem = 1;
        count = 10;
        mass = 0.3;
    };
    class ACM_Paracetamol_DoublePack: ACM_Paracetamol {
        scope = 1;
        picture = "\x\ACM\addons\circulation\ui\paracetamol_doublepack_ca.paa";
        displayName = "Acetaminophen (Double Pack)";
        displayNameShort = "APAP";
        count = 2;
        mass = 0.06;
    };

    // filled-syringe magazines for the drugs we added. this fixes the "Bad vehicle type" error.
    // ACM auto-generates the filled-syringe magazine for each drug it knows, through its prepare_syringe macro.
    // that covers epinephrine, morphine, ketamine, amiodarone, lidocaine, TXA, fentanyl, ondansetron,
    // CalciumChloride, esmolol, ertapenem, atropine, adenosine and dimercaprol. it does not generate them for the
    // four drugs we added: norepinephrine, midazolam, CalciumGluconate and ceftriaxone. when ACM's draw and inject
    // path builds the class string ACM_Syringe_<size>_<drug>, in fnc_syringe_preparefinish line 37 and
    // fnc_syringe_inject, the magazine does not exist. ace_common_fnc_addToInventory then falls back to spawning a
    // GroundWeaponHolder for the missing class and the engine throws "Bad vehicle type".
    // these definitions mirror ACM's own macro. they inherit ACM_Syringe_10_Epinephrine, which carries scope=1,
    // ACE_isMedicalItem, ACE_asItem and acm_issyringe=1, and override the picture, displayname, count and mass
    // only. the count is the drug volume times 100, so 10 ml is 1000 and 1 ml is 100, the same as ACM.
    // acm_issyringe=1 is inherited, so ACM's xeh_postinit syringe scan, acm_syringes_*, picks these up
    // automatically and the drugs become fully drawable and pushable with no further wiring.
    class ACM_Syringe_10_Epinephrine;  // ACM base, forward-declared so the inherits below resolve to the real class.

    class ACM_Syringe_10_EpinephrineCardiac: ACM_Syringe_10_Epinephrine {
        author = "mavis";
        dlc = "ACM_Extended";
        picture = "\x\ACM\addons\circulation\ui\syringe_10_ca.paa";
        displayName = "Syringe (10 mL) [Epinephrine 1:10,000]";
        descriptionShort = "Cardiac epinephrine 0.1 mg/mL. Actual dose equals filled volume times concentration. IV/IO only.";
        count = 1000;
        mass = 0.9;
    };
    class ACM_Syringe_5_EpinephrineCardiac: ACM_Syringe_10_Epinephrine {
        author = "mavis";
        dlc = "ACM_Extended";
        picture = "\x\ACM\addons\circulation\ui\syringe_5_ca.paa";
        displayName = "Syringe (5 mL) [Epinephrine 1:10,000]";
        descriptionShort = "Cardiac epinephrine 0.1 mg/mL. Actual dose equals filled volume times concentration. IV/IO only.";
        count = 500;
        mass = 0.7;
    };
    class ACM_Syringe_3_EpinephrineCardiac: ACM_Syringe_10_Epinephrine {
        author = "mavis";
        dlc = "ACM_Extended";
        picture = "\x\ACM\addons\circulation\ui\syringe_3_ca.paa";
        displayName = "Syringe (3 mL) [Epinephrine 1:10,000]";
        descriptionShort = "Cardiac epinephrine 0.1 mg/mL. Actual dose equals filled volume times concentration. IV/IO only.";
        count = 300;
        mass = 0.6;
    };
    class ACM_Syringe_1_EpinephrineCardiac: ACM_Syringe_10_Epinephrine {
        author = "mavis";
        dlc = "ACM_Extended";
        picture = "\x\ACM\addons\circulation\ui\syringe_1_ca.paa";
        displayName = "Syringe (1 mL) [Epinephrine 1:10,000]";
        descriptionShort = "Cardiac epinephrine 0.1 mg/mL. Actual dose equals filled volume times concentration. IV/IO only.";
        count = 100;
        mass = 0.5;
    };

    class ACM_Syringe_10_Norepinephrine: ACM_Syringe_10_Epinephrine {
        author = "mavis";
        dlc = "ACM_Extended";
        picture = "\x\ACM\addons\circulation\ui\syringe_10_ca.paa";
        displayName = "Syringe (10ml) [Norepinephrine]";
        descriptionShort = "Prepared syringe of Norepinephrine.";
        count = 1000;
        mass = 0.9;
    };
    class ACM_Syringe_5_Norepinephrine: ACM_Syringe_10_Epinephrine {
        author = "mavis";
        dlc = "ACM_Extended";
        picture = "\x\ACM\addons\circulation\ui\syringe_5_ca.paa";
        displayName = "Syringe (5ml) [Norepinephrine]";
        descriptionShort = "Prepared syringe of Norepinephrine.";
        count = 500;
        mass = 0.7;
    };
    class ACM_Syringe_3_Norepinephrine: ACM_Syringe_10_Epinephrine {
        author = "mavis";
        dlc = "ACM_Extended";
        picture = "\x\ACM\addons\circulation\ui\syringe_3_ca.paa";
        displayName = "Syringe (3ml) [Norepinephrine]";
        descriptionShort = "Prepared syringe of Norepinephrine.";
        count = 300;
        mass = 0.6;
    };
    class ACM_Syringe_1_Norepinephrine: ACM_Syringe_10_Epinephrine {
        author = "mavis";
        dlc = "ACM_Extended";
        picture = "\x\ACM\addons\circulation\ui\syringe_1_ca.paa";
        displayName = "Syringe (1ml) [Norepinephrine]";
        descriptionShort = "Prepared syringe of Norepinephrine.";
        count = 100;
        mass = 0.5;
    };

    // phentolamine, an alpha-blocker. it is the reversal agent for catecholamine vasopressor extravasation, from
    // norepinephrine and epinephrine. injected locally at the extravasation site it reverses the ischemic
    // vasoconstriction. it draws and injects like any vial, and the vesicant eh handles the extravasation reversal
    // when the classname "Phentolamine" is delivered peripherally.
    class ACM_Syringe_10_Phentolamine: ACM_Syringe_10_Epinephrine {
        author = "mavis";
        dlc = "ACM_Extended";
        picture = "\x\ACM\addons\circulation\ui\syringe_10_ca.paa";
        displayName = "Syringe (10ml) [Phentolamine]";
        descriptionShort = "Prepared syringe of Phentolamine. Reverses vasopressor extravasation.";
        count = 1000;
        mass = 0.9;
    };
    class ACM_Syringe_5_Phentolamine: ACM_Syringe_10_Epinephrine {
        author = "mavis";
        dlc = "ACM_Extended";
        picture = "\x\ACM\addons\circulation\ui\syringe_5_ca.paa";
        displayName = "Syringe (5ml) [Phentolamine]";
        descriptionShort = "Prepared syringe of Phentolamine. Reverses vasopressor extravasation.";
        count = 500;
        mass = 0.7;
    };
    class ACM_Syringe_3_Phentolamine: ACM_Syringe_10_Epinephrine {
        author = "mavis";
        dlc = "ACM_Extended";
        picture = "\x\ACM\addons\circulation\ui\syringe_3_ca.paa";
        displayName = "Syringe (3ml) [Phentolamine]";
        descriptionShort = "Prepared syringe of Phentolamine. Reverses vasopressor extravasation.";
        count = 300;
        mass = 0.6;
    };
    class ACM_Syringe_1_Phentolamine: ACM_Syringe_10_Epinephrine {
        author = "mavis";
        dlc = "ACM_Extended";
        picture = "\x\ACM\addons\circulation\ui\syringe_1_ca.paa";
        displayName = "Syringe (1ml) [Phentolamine]";
        descriptionShort = "Prepared syringe of Phentolamine. Reverses vasopressor extravasation.";
        count = 100;
        mass = 0.5;
    };

    // hyaluronidase, an enzyme that breaks down hyaluronic acid in connective tissue and lets an extravasated drug
    // disperse and absorb. it is the reversal agent for hyperosmolar and non-catecholamine extravasation, from
    // calcium, hypertonic saline, mannitol, amiodarone, magnesium and esmolol. the vesicant eh handles the
    // reversal when the classname "Hyaluronidase" is delivered peripherally.
    class ACM_Syringe_10_Hyaluronidase: ACM_Syringe_10_Epinephrine {
        author = "mavis";
        dlc = "ACM_Extended";
        picture = "\x\ACM\addons\circulation\ui\syringe_10_ca.paa";
        displayName = "Syringe (10ml) [Hyaluronidase]";
        descriptionShort = "Prepared syringe of Hyaluronidase. Disperses extravasated hyperosmolar/irritant drugs.";
        count = 1000;
        mass = 0.9;
    };
    class ACM_Syringe_5_Hyaluronidase: ACM_Syringe_10_Epinephrine {
        author = "mavis";
        dlc = "ACM_Extended";
        picture = "\x\ACM\addons\circulation\ui\syringe_5_ca.paa";
        displayName = "Syringe (5ml) [Hyaluronidase]";
        descriptionShort = "Prepared syringe of Hyaluronidase. Disperses extravasated hyperosmolar/irritant drugs.";
        count = 500;
        mass = 0.7;
    };
    class ACM_Syringe_3_Hyaluronidase: ACM_Syringe_10_Epinephrine {
        author = "mavis";
        dlc = "ACM_Extended";
        picture = "\x\ACM\addons\circulation\ui\syringe_3_ca.paa";
        displayName = "Syringe (3ml) [Hyaluronidase]";
        descriptionShort = "Prepared syringe of Hyaluronidase. Disperses extravasated hyperosmolar/irritant drugs.";
        count = 300;
        mass = 0.6;
    };
    class ACM_Syringe_1_Hyaluronidase: ACM_Syringe_10_Epinephrine {
        author = "mavis";
        dlc = "ACM_Extended";
        picture = "\x\ACM\addons\circulation\ui\syringe_1_ca.paa";
        displayName = "Syringe (1ml) [Hyaluronidase]";
        descriptionShort = "Prepared syringe of Hyaluronidase. Disperses extravasated hyperosmolar/irritant drugs.";
        count = 100;
        mass = 0.5;
    };

    class ACM_Syringe_10_Midazolam: ACM_Syringe_10_Epinephrine {
        author = "mavis";
        dlc = "ACM_Extended";
        picture = "\x\ACM\addons\circulation\ui\syringe_10_ca.paa";
        displayName = "Syringe (10ml) [Midazolam]";
        descriptionShort = "Prepared syringe of Midazolam.";
        count = 1000;
        mass = 0.9;
    };
    class ACM_Syringe_5_Midazolam: ACM_Syringe_10_Epinephrine {
        author = "mavis";
        dlc = "ACM_Extended";
        picture = "\x\ACM\addons\circulation\ui\syringe_5_ca.paa";
        displayName = "Syringe (5ml) [Midazolam]";
        descriptionShort = "Prepared syringe of Midazolam.";
        count = 500;
        mass = 0.7;
    };
    class ACM_Syringe_3_Midazolam: ACM_Syringe_10_Epinephrine {
        author = "mavis";
        dlc = "ACM_Extended";
        picture = "\x\ACM\addons\circulation\ui\syringe_3_ca.paa";
        displayName = "Syringe (3ml) [Midazolam]";
        descriptionShort = "Prepared syringe of Midazolam.";
        count = 300;
        mass = 0.6;
    };
    class ACM_Syringe_1_Midazolam: ACM_Syringe_10_Epinephrine {
        author = "mavis";
        dlc = "ACM_Extended";
        picture = "\x\ACM\addons\circulation\ui\syringe_1_ca.paa";
        displayName = "Syringe (1ml) [Midazolam]";
        descriptionShort = "Prepared syringe of Midazolam.";
        count = 100;
        mass = 0.5;
    };

    class ACM_Syringe_10_Rocuronium: ACM_Syringe_10_Epinephrine {
        author = "mavis";
        dlc = "ACM_Extended";
        picture = "\x\ACM\addons\circulation\ui\syringe_10_ca.paa";
        displayName = "Syringe (10ml) [Rocuronium]";
        descriptionShort = "Prepared syringe of Rocuronium (paralytic).";
        count = 1000;
        mass = 0.9;
    };
    class ACM_Syringe_5_Rocuronium: ACM_Syringe_10_Epinephrine {
        author = "mavis";
        dlc = "ACM_Extended";
        picture = "\x\ACM\addons\circulation\ui\syringe_5_ca.paa";
        displayName = "Syringe (5ml) [Rocuronium]";
        descriptionShort = "Prepared syringe of Rocuronium (paralytic).";
        count = 500;
        mass = 0.7;
    };
    class ACM_Syringe_3_Rocuronium: ACM_Syringe_10_Epinephrine {
        author = "mavis";
        dlc = "ACM_Extended";
        picture = "\x\ACM\addons\circulation\ui\syringe_3_ca.paa";
        displayName = "Syringe (3ml) [Rocuronium]";
        descriptionShort = "Prepared syringe of Rocuronium (paralytic).";
        count = 300;
        mass = 0.6;
    };
    class ACM_Syringe_1_Rocuronium: ACM_Syringe_10_Epinephrine {
        author = "mavis";
        dlc = "ACM_Extended";
        picture = "\x\ACM\addons\circulation\ui\syringe_1_ca.paa";
        displayName = "Syringe (1ml) [Rocuronium]";
        descriptionShort = "Prepared syringe of Rocuronium (paralytic).";
        count = 100;
        mass = 0.5;
    };

    // sugammadex syringes. the narc box and draw system instantiate ACM_Syringe_<size>_<drug> directly, so every
    // size the draw list offers must exist as a real class or the game throws "Bad vehicle type". the vial is 500
    // mg in 5 ml, so 5 ml is the full-vial draw. all four sizes are provided because the medic can draw a partial
    // volume, and with sugammadex the volume drawn is the dose. 16 mg/kg needs multiple full vials.
    class ACM_Syringe_10_Sugammadex: ACM_Syringe_10_Epinephrine {
        author = "mavis";
        dlc = "ACM_Extended";
        picture = "\x\ACM\addons\circulation\ui\syringe_10_ca.paa";
        displayName = "Syringe (10ml) [Sugammadex]";
        descriptionShort = "Prepared syringe of Sugammadex (rocuronium reversal).";
        count = 1000;
        mass = 0.9;
    };
    class ACM_Syringe_5_Sugammadex: ACM_Syringe_10_Epinephrine {
        author = "mavis";
        dlc = "ACM_Extended";
        picture = "\x\ACM\addons\circulation\ui\syringe_5_ca.paa";
        displayName = "Syringe (5ml) [Sugammadex]";
        descriptionShort = "Prepared syringe of Sugammadex (rocuronium reversal).";
        count = 500;
        mass = 0.7;
    };
    class ACM_Syringe_3_Sugammadex: ACM_Syringe_10_Epinephrine {
        author = "mavis";
        dlc = "ACM_Extended";
        picture = "\x\ACM\addons\circulation\ui\syringe_3_ca.paa";
        displayName = "Syringe (3ml) [Sugammadex]";
        descriptionShort = "Prepared syringe of Sugammadex (rocuronium reversal).";
        count = 300;
        mass = 0.6;
    };
    class ACM_Syringe_1_Sugammadex: ACM_Syringe_10_Epinephrine {
        author = "mavis";
        dlc = "ACM_Extended";
        picture = "\x\ACM\addons\circulation\ui\syringe_1_ca.paa";
        displayName = "Syringe (1ml) [Sugammadex]";
        descriptionShort = "Prepared syringe of Sugammadex (rocuronium reversal).";
        count = 100;
        mass = 0.5;
    };

    class ACM_Syringe_10_CalciumGluconate: ACM_Syringe_10_Epinephrine {
        author = "mavis";
        dlc = "ACM_Extended";
        picture = "\x\ACM\addons\circulation\ui\syringe_10_ca.paa";
        displayName = "Syringe (10ml) [CalciumGluconate]";
        descriptionShort = "Prepared syringe of CalciumGluconate.";
        count = 1000;
        mass = 0.9;
    };
    class ACM_Syringe_5_CalciumGluconate: ACM_Syringe_10_Epinephrine {
        author = "mavis";
        dlc = "ACM_Extended";
        picture = "\x\ACM\addons\circulation\ui\syringe_5_ca.paa";
        displayName = "Syringe (5ml) [CalciumGluconate]";
        descriptionShort = "Prepared syringe of CalciumGluconate.";
        count = 500;
        mass = 0.7;
    };
    class ACM_Syringe_3_CalciumGluconate: ACM_Syringe_10_Epinephrine {
        author = "mavis";
        dlc = "ACM_Extended";
        picture = "\x\ACM\addons\circulation\ui\syringe_3_ca.paa";
        displayName = "Syringe (3ml) [CalciumGluconate]";
        descriptionShort = "Prepared syringe of CalciumGluconate.";
        count = 300;
        mass = 0.6;
    };
    class ACM_Syringe_1_CalciumGluconate: ACM_Syringe_10_Epinephrine {
        author = "mavis";
        dlc = "ACM_Extended";
        picture = "\x\ACM\addons\circulation\ui\syringe_1_ca.paa";
        displayName = "Syringe (1ml) [CalciumGluconate]";
        descriptionShort = "Prepared syringe of CalciumGluconate.";
        count = 100;
        mass = 0.5;
    };

    // propofol syringes. it is a sedative-hypnotic at 500 mg in 50 ml, or 10 mg/ml. it draws and pushes, and the
    // infusion route waits on the syringe pump. it is half of ketofol, with ketamine.
    class ACM_Syringe_10_Propofol: ACM_Syringe_10_Epinephrine {
        author = "mavis";
        dlc = "ACM_Extended";
        picture = "\x\ACM\addons\circulation\ui\syringe_10_ca.paa";
        displayName = "Syringe (10ml) [Propofol]";
        descriptionShort = "Prepared syringe of Propofol.";
        count = 1000;
        mass = 0.9;
    };
    class ACM_Syringe_5_Propofol: ACM_Syringe_10_Epinephrine {
        author = "mavis";
        dlc = "ACM_Extended";
        picture = "\x\ACM\addons\circulation\ui\syringe_5_ca.paa";
        displayName = "Syringe (5ml) [Propofol]";
        descriptionShort = "Prepared syringe of Propofol.";
        count = 500;
        mass = 0.7;
    };
    class ACM_Syringe_3_Propofol: ACM_Syringe_10_Epinephrine {
        author = "mavis";
        dlc = "ACM_Extended";
        picture = "\x\ACM\addons\circulation\ui\syringe_3_ca.paa";
        displayName = "Syringe (3ml) [Propofol]";
        descriptionShort = "Prepared syringe of Propofol.";
        count = 300;
        mass = 0.6;
    };
    class ACM_Syringe_1_Propofol: ACM_Syringe_10_Epinephrine {
        author = "mavis";
        dlc = "ACM_Extended";
        picture = "\x\ACM\addons\circulation\ui\syringe_1_ca.paa";
        displayName = "Syringe (1ml) [Propofol]";
        descriptionShort = "Prepared syringe of Propofol.";
        count = 100;
        mass = 0.5;
    };

    class ACM_Syringe_10_Ceftriaxone: ACM_Syringe_10_Epinephrine {
        author = "mavis";
        dlc = "ACM_Extended";
        picture = "\x\ACM\addons\circulation\ui\syringe_10_ca.paa";
        displayName = "Syringe (10ml) [Ceftriaxone]";
        descriptionShort = "Prepared syringe of Ceftriaxone.";
        count = 1000;
        mass = 0.9;
    };
    class ACM_Syringe_5_Ceftriaxone: ACM_Syringe_10_Epinephrine {
        author = "mavis";
        dlc = "ACM_Extended";
        picture = "\x\ACM\addons\circulation\ui\syringe_5_ca.paa";
        displayName = "Syringe (5ml) [Ceftriaxone]";
        descriptionShort = "Prepared syringe of Ceftriaxone.";
        count = 500;
        mass = 0.7;
    };
    class ACM_Syringe_3_Ceftriaxone: ACM_Syringe_10_Epinephrine {
        author = "mavis";
        dlc = "ACM_Extended";
        picture = "\x\ACM\addons\circulation\ui\syringe_3_ca.paa";
        displayName = "Syringe (3ml) [Ceftriaxone]";
        descriptionShort = "Prepared syringe of Ceftriaxone.";
        count = 300;
        mass = 0.6;
    };
    class ACM_Syringe_1_Ceftriaxone: ACM_Syringe_10_Epinephrine {
        author = "mavis";
        dlc = "ACM_Extended";
        picture = "\x\ACM\addons\circulation\ui\syringe_1_ca.paa";
        displayName = "Syringe (1ml) [Ceftriaxone]";
        descriptionShort = "Prepared syringe of Ceftriaxone.";
        count = 100;
        mass = 0.5;
    };

};

class CfgWeapons {
    class ACE_ItemCore;
    class CBA_MiscItem_ItemInfo;
    class ACM_NCDKit;
    // rename paracetamol to acetaminophen, the same drug under its us name. we override the display name only.
    // the medication classname and effect stay "Paracetamol", so all ACM logic is untouched.
    class ACM_Paracetamol_SinglePack { displayName = "Acetaminophen (Single Pack)"; };
    class ACME_HTSBag: ACE_ItemCore {
        author = "mavis";
        dlc = "ACM_Extended";
        scope = 2;
        displayName = "Hypertonic Saline 3% (250mL)";
        picture = "\acm_extended\ui\items\htsiv_ca.paa";
        descriptionShort = "Premixed 3% hypertonic saline. Osmotherapy for raised ICP.";
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo { mass = 3; };
    };
    // the herniation rescue. 23.4 percent hypertonic saline in a 30 ml bullet, which is the concentrated push that
    // buys minutes of ICP reduction when a pupil has blown, as opposed to the 3 percent bag above which is a drip.
    // it is a central-line drug in life, because 23.4 percent scleroses a peripheral vein, and that is not modeled
    // here beyond the description saying so.
    class ACME_HTSBullet: ACE_ItemCore {
        author = "mavis";
        dlc = "ACM_Extended";
        scope = 2;
        displayName = "Hypertonic Saline 23.4% (30mL)";
        picture = "\acm_extended\ui\items\htsiv_ca.paa";
        descriptionShort = "Concentrated osmotherapy bolus for herniation. Central access preferred. Buys minutes, does not fix the lesion.";
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo { mass = 1; };
    };
    // mannitol as a push rather than a bag. it draws water out of the brain and it also makes the casualty pass it,
    // so it drops the circulating volume, which is why it is the wrong choice in someone who is already dry.
    class ACME_MannitolVial: ACE_ItemCore {
        author = "mavis";
        dlc = "ACM_Extended";
        scope = 2;
        displayName = "Mannitol 20% (50g Push)";
        picture = "\acm_extended\ui\items\mannitolbag_iv_ca.paa";
        descriptionShort = "Osmotic diuretic push for raised ICP. Lowers circulating volume as it works.";
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo { mass = 2; };
    };
    class ACME_Ventilator: ACE_ItemCore {
        author = "mavis";
        dlc = "ACM_Extended";
        scope = 2;
        displayName = "Ventway Sparrow Robust";
        picture = "\acm_extended\ui\vent\ventway_sparrow_robust_ca.paa";
        descriptionShort = "Portable transport ventilator. Carry it and use the self-interaction to open the control panel.";
        ACE_isMedicalItem = 1;
        // 2.86 lb, or 1.3 kg. arma mass is pounds times 10, the same scale the rest of the kit in this config uses.
        class ItemInfo: CBA_MiscItem_ItemInfo { mass = 29; };
    };
    // spare battery. it is heavy on purpose. a spare is a real logistics decision and not something you top off
    // with, and between the vent and one spare you have spent a meaningful part of an aid bag on the airway of one
    // casualty.
    class ACME_VentBattery: ACE_ItemCore {
        author = "mavis";
        dlc = "ACM_Extended";
        scope = 2;
        displayName = "Ventway Sparrow Battery";
        descriptionShort = "Spare lithium battery pack for the Ventway Sparrow. Replaces a depleted battery in the field.";
        picture = "\acm_extended\ui\vent\ventway_sparrow_robust_battery_ca.paa";
        // 0.52 lb, or 235 g. it was 28, which made a spare cell heavier than the machine it goes in.
        class ItemInfo: CBA_MiscItem_ItemInfo { mass = 5; };
    };
    class ACME_Laryngoscope: ACE_ItemCore {
        author = "mavis";
        dlc = "ACM_Extended";
        scope = 2;
        displayName = "Laryngoscope";
        picture = "\acm_extended\ui\vent\laryngoscope_ca.paa";
        descriptionShort = "Rigid laryngoscope for direct-vision orotracheal intubation. Needed with an ET tube to intubate.";
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo { mass = 4; };
    };
    class ACME_ETTube: ACE_ItemCore {
        author = "mavis";
        dlc = "ACM_Extended";
        scope = 2;
        displayName = "Endotracheal Tube";
        picture = "\acm_extended\ui\vent\et_tube_ca.paa";
        descriptionShort = "Cuffed endotracheal tube. Passed under direct laryngoscopy to secure a definitive airway.";
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo { mass = 1; };
    };
    class ACME_MagnesiumBag: ACE_ItemCore {
        author = "mavis";
        dlc = "ACM_Extended";
        scope = 2;
        displayName = "Magnesium Sulfate (2g / 50mL)";
        picture = "\acm_extended\ui\items\mgbag_50ml_iv_ca.paa";
        descriptionShort = "Premixed magnesium sulfate, 2 g in 50 mL. First-line for torsades / polymorphic VT.";
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo { mass = 2; };
    };
    // mannitol 20 percent, premixed in 500 ml. it is osmotherapy for raised ICP and replaces the old push vial.
    // it uses the same osmotherapy bag pattern as HTS. it hangs as a fluids bag, and the ICP drop is ml-driven
    // through the "Mannitol" osmotic agent, in premixedbytype and osmoticagents in fn_postInit.
    class ACME_MannitolBag: ACE_ItemCore {
        author = "mavis";
        dlc = "ACM_Extended";
        scope = 2;
        displayName = "Mannitol 20% (500mL)";
        picture = "\acm_extended\ui\items\mannitolbag_iv_ca.paa";
        descriptionShort = "Premixed 20% mannitol in 500 mL. Osmotic diuretic for raised ICP.";
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo { mass = 5; };
    };
    // plasma-lyte a, 1000 ml. it is a balanced, buffered crystalloid. it gives resuscitation volume like saline,
    // and its acetate and gluconate buffer helps reverse metabolic acidosis as it runs. it is shelf-stable,
    // because it is not a blood product, so the cold chain ignores it, and it carries no cells, protein or
    // clotting factors. it is not plasma. it rides ACM's fluid system as its own "PlasmaLyte" type. see
    // PlasmaLyteIV_1000 and the getBloodVolumeChange override.
    class ACME_PlasmaLyteBag: ACE_ItemCore {
        author = "mavis";
        dlc = "ACM_Extended";
        scope = 2;
        displayName = "Plasma-Lyte A (1000mL)";
        picture = "\acm_extended\ui\items\plasmalyte-a_ca.paa";
        descriptionShort = "Balanced crystalloid, 1000 mL. Volume resuscitation + buffers metabolic acidosis. Shelf-stable; no cells/protein/clotting factors (not plasma).";
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo { mass = 10; };
    };
    // smaller plasma-lyte a volumes, at 100, 250 and 500 ml. it is the same balanced crystalloid, and the mass
    // scales at about 1 per 100 ml.
    class ACME_PlasmaLyteBag_500: ACME_PlasmaLyteBag {
        author = "mavis";
        dlc = "ACM_Extended";
        displayName = "Plasma-Lyte A (500mL)";
        descriptionShort = "Balanced crystalloid, 500 mL. Volume resuscitation + buffers metabolic acidosis. Shelf-stable.";
        class ItemInfo: CBA_MiscItem_ItemInfo { mass = 5; };
    };
    class ACME_PlasmaLyteBag_250: ACME_PlasmaLyteBag {
        author = "mavis";
        dlc = "ACM_Extended";
        displayName = "Plasma-Lyte A (250mL)";
        descriptionShort = "Balanced crystalloid, 250 mL. Volume resuscitation + buffers metabolic acidosis. Shelf-stable.";
        class ItemInfo: CBA_MiscItem_ItemInfo { mass = 3; };
    };
    class ACME_PlasmaLyteBag_100: ACME_PlasmaLyteBag {
        author = "mavis";
        dlc = "ACM_Extended";
        displayName = "Plasma-Lyte A (100mL)";
        descriptionShort = "Balanced crystalloid, 100 mL. Small volume / carrier. Shelf-stable.";
        class ItemInfo: CBA_MiscItem_ItemInfo { mass = 2; };
    };
    // small-volume saline bags, at 50 and 100 ml. these are flush and keep-open reserves. they are ideal as the
    // y-line saline reserve, because each flush line bleeds 50 ml, so a 50 ml bag is one flush and a 100 ml bag is
    // two. they also suit small standalone drips.
    class ACME_SalineBag_50: ACE_ItemCore {
        author = "mavis";
        dlc = "ACM_Extended";
        scope = 2;
        displayName = "Saline IV (50mL)";
        picture = "\acm_extended\ui\items\salineiv_50ml_ca.paa";
        descriptionShort = "0.9% sodium chloride, 50 mL. Small flush / keep-vein-open volume. As a Y-line reserve this is one line flush.";
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo { mass = 1; };
    };
    class ACME_SalineBag_100: ACE_ItemCore {
        author = "mavis";
        dlc = "ACM_Extended";
        scope = 2;
        displayName = "Saline IV (100mL)";
        picture = "\acm_extended\ui\items\salineiv_100ml_ca.paa";
        descriptionShort = "0.9% sodium chloride, 100 mL. Small flush / keep-vein-open volume. As a Y-line reserve this is two line flushes.";
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo { mass = 2; };
    };

    // intranasal esketamine atomizer. it gives battlefield analgesia with no iv access, and a medic administers it
    // like the ACM naloxone spray, targeted at the head. at a sub-dissociative dose it gives strong analgesia and
    // stays hemodynamically stable, because it is mildly sympathomimetic rather than carrying the bradycardia and
    // hypotension of an opioid. respiratory depression is minimal and the gag reflex is preserved. the effect
    // config lives in ACM_Medication >> medications >> esketamine below.
    class ACME_Spray_Esketamine: ACE_ItemCore {
        author = "mavis";
        dlc = "ACM_Extended";
        scope = 2;
        displayName = "Esketamine Atomizer (IN, 50mg)";
        picture = "\acm_extended\ui\items\esketamine_in_ca.paa";
        descriptionShort = "Intranasal esketamine for moderate-to-severe pain when IV access isn't available. Well tolerated in shock / hemodynamic instability; far less respiratory depression than opioids; preserves airway reflexes.";
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo { mass = 1; };
    };

    // former CfgWeapons.hpp items, merged into this single CfgWeapons block.
    class ACE_bloodIV;  // ACE base for iv fluid bags, medical-tagged.
    class ACE_salineIV_250;  // ACE 250 ml saline bag. it is the carrier base for our premixed drips.
    class ACE_salineIV_500;  // ACE 500 ml saline bag. it is the carrier base for the mannitol drip.

    // norepinephrine, levophed, vial. it belongs to the vial family.
    // Dedicated cardiac-strength source. Existing Epinephrine remains 1 mg/mL (1:1,000).
    class ACM_Vial_Epinephrine;
    class ACME_Vial_EpinephrineCardiac: ACM_Vial_Epinephrine {
        dlc = "ACM_Extended";
        scope = 2;
        scopeArsenal = 2;
        author = "mavis";
        displayName = "Epinephrine 1:10,000 (1 mg / 10 mL)";
        picture = "\acm_extended\ui\items\vial_epinephrine_1_10000_ca.paa";
        descriptionShort = "0.1 mg/mL cardiac epinephrine. IV/IO source. For a 10 mcg/mL mixture: 1 mL of this source plus 9 mL saline. The full mixture contains 100 mcg, not 10 mcg.";
        ACE_isMedicalItem = 1;
        ACM_isVial = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo { mass = 1; };
    };
    // Hidden compatibility alias for old missions/loadouts. New arsenals and the Narc Box use ACME_.
    class ACM_Vial_EpinephrineCardiac: ACME_Vial_EpinephrineCardiac {
        author = "mavis";
        dlc = "ACM_Extended";
        scope = 1;
        scopeArsenal = 0;
    };

    class ACM_Vial_Norepinephrine: ACE_ItemCore {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        displayName = "Norepinephrine (4mg/4ml)";
        descriptionShort = "Vasopressor. CPP support AFTER volume resuscitation.";
        picture = "\acm_extended\ui\items\vial_norepinephrine_ca.paa";
        ACE_isMedicalItem = 1;
        ACM_isVial = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 1;
        };
    };

    // phentolamine vial. it is an alpha-adrenergic blocker and the antidote for vasopressor extravasation, from
    // norepinephrine and epinephrine. injected at the affected peripheral site it reverses the ischemic
    // vasoconstriction and the tissue recovers. it draws and pushes like any vial.
    class ACM_Vial_Phentolamine: ACE_ItemCore {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        displayName = "Phentolamine (5mg/1ml)";
        descriptionShort = "Alpha-blocker. Antidote for vasopressor (norepi/epi) extravasation.";
        picture = "\acm_extended\ui\items\vial_norepinephrine_ca.paa";
        ACE_isMedicalItem = 1;
        ACM_isVial = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 1;
        };
    };

    // hyaluronidase vial. it is an enzyme, a spreading factor, and the antidote for hyperosmolar and irritant
    // extravasation, from calcium, hypertonic saline, mannitol, amiodarone, magnesium and esmolol. injected around
    // the site it lets the trapped drug disperse and absorb, so the tissue recovers. it draws and pushes like any
    // vial.
    class ACM_Vial_Hyaluronidase: ACE_ItemCore {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        displayName = "Hyaluronidase (150U/1ml)";
        descriptionShort = "Spreading-factor enzyme. Antidote for hyperosmolar/irritant extravasation.";
        picture = "\acm_extended\ui\items\vial_norepinephrine_ca.paa";
        ACE_isMedicalItem = 1;
        ACM_isVial = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 1;
        };
    };

    // rocuronium bromide vial. it is a non-depolarizing neuromuscular blocker, a paralytic. it provides no
    // sedation, no analgesia and no amnesia. it draws and pushes like any vial. at an intubating dose it paralyzes
    // skeletal muscle, the respiratory muscles included, so the patient goes apneic and must be ventilated. the
    // onset is about 45 to 60 s and the duration about 30 to 45 min. paralysis without adequate sedation on board
    // is the cardinal RSI error, an awake paralysis. ACME_fnc_rocuroniumTick drives the effect, not ACM's pain and
    // vitals model.
    class ACM_Vial_Rocuronium: ACE_ItemCore {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        displayName = "Rocuronium Bromide (100mg/10ml)";
        descriptionShort = "Non-depolarizing paralytic for RSI. NO sedation: paralyzes and stops breathing. Sedate first.";
        picture = "\acm_extended\ui\items\vial_rocuronium_ca.paa";
        ACE_isMedicalItem = 1;
        ACM_isVial = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 1;
        };
    };

    // sugammadex vial. it is the rocuronium reversal agent and the only way out of a failed RSI. it encapsulates
    // rocuronium and drags it out of circulation, which restores the patient's own respiratory drive in about 2 to
    // 3 min. it reverses the paralysis only. it is not a sedative and it does not undo awareness. a patient
    // paralyzed while awake was awake for it, see ACME_roc_awarenessEvent, and a reversal afterwards does not
    // change that. the effect is dose-dependent. see ACME_fnc_sugammadexTick.
    class ACM_Vial_Sugammadex: ACE_ItemCore {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        displayName = "Sugammadex (500mg/5ml)";
        descriptionShort = "Reverses rocuronium. Restores spontaneous breathing in ~2-3 min. Rescues a failed RSI. Dose by WEIGHT: 16 mg/kg to reverse a fresh intubating dose. Under-dose and the block RETURNS. NOT a sedative: does not undo awareness.";
        picture = "\acm_extended\ui\items\vial_sugammadex_ca.paa";
        ACE_isMedicalItem = 1;
        ACM_isVial = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 1;
        };
    };

    // ceftriaxone vial, a broad-spectrum antibiotic. it is functionally identical to ACM's ertapenem. when infused
    // it is delivered as Ertapenem_IV, see ACME_infusion_deliveryClassOverride, so it satisfies ACM's evac
    // antibiotic gate, because getMedicationCount counts the recorded classname, and it carries the same effect.
    // the vial relabels it as ceftriaxone in the inventory and the draw list.
    class ACM_Vial_Ceftriaxone: ACE_ItemCore {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        displayName = "Ceftriaxone (1g/10ml)";
        descriptionShort = "Broad-spectrum antibiotic. Satisfies the evacuation antibiotic requirement (same as ertapenem).";
        picture = "\acm_extended\ui\items\vial_ceftriaxone_ca.paa";
        ACE_isMedicalItem = 1;
        ACM_isVial = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 1;
        };
    };

    // calcium gluconate vial, the gentle calcium salt. it delivers the same calcium count as calcium chloride when
    // infused, because it routes to CalciumChloride_IV, and it is never vesicant. the harsh peripheral-push
    // penalty lives on calcium chloride only. it is about 1 g in 10 ml, a 10 percent solution.
    class ACM_Vial_CalciumGluconate: ACE_ItemCore {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        displayName = "Calcium Gluconate (5g/50ml)";
        descriptionShort = "Calcium salt for hypocalcemia / hyperkalemia / post-transfusion. Far gentler on peripheral veins than calcium chloride.";
        picture = "\acm_extended\ui\items\vial_calcium_gluconate_ca.paa";
        ACE_isMedicalItem = 1;
        ACM_isVial = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 1;
        };
    };

    // propofol vial, a sedative-hypnotic known as milk of amnesia. it is 500 mg in 50 ml, or 10 mg/ml. it pushes
    // and draws, and the infusion, or maintenance, route waits on the syringe pump. it pairs with ketamine to make
    // ketofol.
    class ACM_Vial_Propofol: ACE_ItemCore {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        displayName = "Propofol (500mg/50ml)";
        descriptionShort = "Sedative-hypnotic for induction and procedural sedation. Causes dose-dependent hypotension and apnea; half of Ketofol.";
        picture = "\acm_extended\ui\items\vial_propofol_ca.paa";
        ACE_isMedicalItem = 1;
        ACM_isVial = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 1;
        };
    };

    // midazolam vial, a benzodiazepine sedative. ACM ships an im midazolam only, so we add an iv variant,
    // Midazolam_IV below, that can be pushed and infused iv. it is 5 mg in 5 ml.
    class ACM_Vial_Midazolam: ACE_ItemCore {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        displayName = "Midazolam (5mg/5ml)";
        descriptionShort = "Benzodiazepine for sedation / seizure control. IV variant for push or infusion.";
        picture = "\acm_extended\ui\items\vial_midazolam_ca.paa";
        ACE_isMedicalItem = 1;
        ACM_isVial = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 1;
        };
    };
class ACM_Vial_Fentanyl: ACE_ItemCore {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        displayName = "Fentanyl (500mcg/10ml)";
        descriptionShort = "Synthetic opioid. Analgesia at 25-50mcg. At 2-3mcg/kg given three minutes before laryngoscopy it blunts the sympathetic response and the ICP surge that comes with it.";
        picture = "\acm_extended\ui\items\vial_midazolam_ca.paa";
        ACE_isMedicalItem = 1;
        ACM_isVial = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 1;
        };
    };

    // iv line, the administration set. this is the tubing you spike a bag with, and it is required to push any
    // fluid. each bag must be spiked, which consumes one of these, before a medic can hang it. it weighs
    // essentially nothing.
    class ACME_IVLine: ACE_ItemCore {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        displayName = "IV Line (Administration Set) (QTTS)";
        descriptionShort = "Spike set / tubing. Required to spike a fluid bag before it can be hung. One per bag.";
        picture = "\acm_extended\ui\items\iv_line_qtts_ca.paa";
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 0.1;  // essentially weightless.
        };
    };

    // Standard blood administration set with blood and saline spikes sharing one patient line.
    // Any supported saline bag can be paired; the line consumes only the configured flush volume.
    class ACME_YTubing: ACE_ItemCore {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        displayName = "Y-Type Blood Tubing Set (QTTS)";
        descriptionShort = "Blood administration set (dual-spike, in-line filter). Pair blood with a compatible saline bag. Flush the line when prompted; no 250mL bag minimum.";
        picture = "\acm_extended\ui\items\y_tubing_qtts_ca.paa";
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 0.2;
        };
    };

    // LifeWarmer quantum, an inline blood and fluid warmer.
    // this is a portable inline warmer placed on the administration set. when a medic hangs a blood bag while
    // carrying one, that patient's blood line is flagged as warmed. transfused blood then adds heat toward 37 c,
    // see ACME_warmer_tempPerLiter, warmed rows color orange, and the log and aar text get a [warmed] tag.
    class ACME_BloodWarmer: ACE_ItemCore {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        displayName = "LifeWarmer Quantum";
        descriptionShort = "Inline blood/fluid warmer. Non-cold blood runs at 200 mL/min; cold-stored blood uses the cold-flow ladder. Warms transfused blood and counters hypothermia.";
        picture = "\acm_extended\ui\items\quantum_bloodwarmer_ca.paa";
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 0.3;
        };
    };

    // pressure infuser bag.
    // this is a pressure cuff that wraps the fluid or blood bag and is pumped up to force the unit in fast, a rapid
    // transfuser. it is a reusable device and is not consumed. a medic applies it through "Apply Pressure
    // Infuser", and while it is on, ACME_pressureInfuser_boost multiplies the flow ceiling of the line.
    class ACME_PressureInfuser: ACE_ItemCore {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        displayName = "Pressure Infuser Bag";
        descriptionShort = "Pressure cuff for a blood/fluid bag. Apply it to a hung line and pump it up to force the unit in fast (rapid transfuser). Reusable.";
        picture = "\acm_extended\ui\items\pressure_infuser_ca.paa";
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 0.4;
        };
    };

    // NAR BOA constricting band.
    // the north american rescue BOA is a wide elastic constricting band. a medic applies it proximal to the chosen
    // iv site to engorge the veins and make the target easier to cannulate. it is consumed as part of starting an
    // iv.
    class ACME_NARBOA: ACE_ItemCore {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        displayName = "NAR BOA Constricting Band";
        descriptionShort = "Wide elastic constricting band. Applied proximal to the IV site to engorge the veins for an easier stick.";
        picture = "\acm_extended\ui\nar_boa_ca.paa";
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 0.2;
        };
    };

    // hypertonic saline 3 percent.
    // the HTS bag is ACME_HTSBag above, registered into ACM_circulation_Fluids_Array in fn_postInit, so it lists in
    // add bag and available fluids exactly like the esmolol and magnesium bags. the old duplicate ACM_Vial_HTS3,
    // an ACE_salineIV_250 that was never added to fluids_array, is removed. it only ever showed as a redundant
    // inventory item that a medic could not administer. HTS osmotherapy still flows through type "HTS", into
    // ACME_infusion_premixedByType["hts"], into HTS3 in fn_syncpremixedbags.

    // premixed esmolol drip bag, 2500 mg in 250 ml, or 10 mg/ml.
    // it is a real fluid bag in the same family as saline, plasma and blood. it is not flagged ACM_isVial, so it
    // leaves the infusion draw list and cannot be mixed into another bag, because it is already premixed.
    // ACME_premixedBag marks it for the auto-attach loop, fn_syncpremixedbags, which layers esmolol rate control
    // on the active bag. the premixed content is declared in ACME_infusion_PremixedBags and premixedbytype, in
    // fn_postInit.
    class ACM_EsmololBag: ACE_salineIV_250 {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        displayName = "Esmolol 2500mg/250ml (10mg/ml)";
        descriptionShort = "Premixed esmolol drip. Rate control for AFib-RVR / atrial tach (titrate to mcg/kg/min). Transfusable bag.";
        picture = "\acm_extended\ui\items\esmololbagiv_ca.paa";
        ACE_isMedicalItem = 1;
        ACME_premixedBag = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 8;
        };
    };

    // display-only proxy classes for the active premixed bags.
    // ACM resolves the shown name of an active bag from the CfgWeapons class whose name is
    // formatfluidbagname(type,volume), which is ace_<lowertype>iv_<vol>. with distinct fluid types, esmolol and
    // hts at 250 ml, the active bags resolve to these, which gives the correct name and icon instead of a generic
    // saline label. scope is 1, so they are never offered from inventory.
    class ACE_esmololIV_250: ACE_salineIV_250 {
        scope = 1;
        author = "mavis";
        displayName = "Esmolol 2500mg/250ml (10mg/ml)";
        picture = "\acm_extended\ui\items\esmololbagiv_ca.paa";
    };
    class ACE_htsIV_250: ACE_salineIV_250 {
        scope = 1;
        author = "mavis";
        displayName = "Hypertonic Saline 3% (250ml)";
        picture = "\acm_extended\ui\items\htsiv_ca.paa";
    };
    class ACE_mannitolIV_500: ACE_salineIV_500 {
        scope = 1;
        author = "mavis";
        displayName = "Mannitol 20% (500ml)";
        picture = "\acm_extended\ui\items\mannitolbag_iv_ca.paa";
    };
    class ACE_magnesiumIV_50: ACE_salineIV_250 {
        scope = 1;
        author = "mavis";
        displayName = "Magnesium Sulfate (2g / 50ml)";
        picture = "\acm_extended\ui\items\mgbag_50ml_iv_ca.paa";
    };

    // calcium chloride 10 percent, 1 g in 10 ml. it covers citrate and hypocalcemia.

    // 18g iv catheter. it is a smaller-bore peripheral line with a slower flow.
    class ACM_IV_18g: ACE_ItemCore {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        displayName = "18g IV";
        descriptionShort = "Smaller-bore peripheral IV. Slower flow than 16G. Distal limb sites risk a hypertensive surge with drips/pressors.";
        picture = "\acm_extended\ui\items\iv_18g_ca.paa";
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 0.1;  // a light needle, in line with the other iv catheters. it was 1, which read as far heavier.
        };
    };

    // ACM'S TWO CATHETER ITEMS, REPOINTED AT THE MATCHING ICON SET.
    // ACM ships iv_16g_ca.paa and iv_14g_ca.paa in circulation/ui and uses each file TWICE: as the inventory
    // picture on the item, in circulation/CfgWeapons.hpp:26 and :38, and as the medical-menu row icon through
    // the ACM_MEDICALMENU_ACTION_BUTTON macro in gui/ActionButtons.hpp:36 and :37. so both surfaces have to be
    // repointed, and the button half is done further down beside the other button classes.
    // the parent is RESTATED on each reopen. that merges with ACM's class and keeps its displayName,
    // descriptionShort, ACE_isMedicalItem and ItemInfo mass. a bare reopen with no parent can replace the class
    // with a stub instead, which is how RemoveTourniquet was broken for two builds.
    // ACM_IV_14g inherits ACM_IV_16g and sets its own picture, so repointing 16g alone would not reach it.
    class ACM_IV_16g: ACE_ItemCore {
        picture = "\acm_extended\ui\items\iv_16g_ca.paa";
    };
    class ACM_IV_14g: ACM_IV_16g {
        descriptionShort = "Large-bore peripheral IV. Wrist placement requires an extremely accurate central stick or the vein blows.";
        picture = "\acm_extended\ui\items\iv_14g_ca.paa";
    };

    // All carried gauges can be attempted at the wrist. A 14g requires a precise central stick.
    // the path is a SINGLE backslash, like every other texture path in this file. a python heredoc writes a
    // doubled backslash and ArmA then reports Picture not found even though the PAA is packed correctly.
    class ACM_IV_20g: ACE_ItemCore {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        displayName = "20g IV";
        descriptionShort = "Smallest-bore peripheral IV. Slowest flow. Most forgiving placement margin at the wrist.";
        picture = "\acm_extended\ui\items\iv_20g_ca.paa";
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 0.1;
        };
    };

    // prefilled 10 ml saline flush. it is the push-dose epi base.
    class ACM_SalineFlush_10: ACE_ItemCore {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        displayName = "Saline Flush (10ml)";
        descriptionShort = "Prefilled 10 mL flush. Base for improvised push-dose epi (1:100,000).";
        picture = "\acm_extended\ui\items\salineFlush_ca.paa";
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 1;
        };
    };

    // core thermometer, a reusable tool. it is the only way to read the core temperature. it is reusable, so it
    // must be in the inventory and is never consumed. a condition gates it and items[] is empty.
    class ACM_Thermometer: ACE_ItemCore {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        displayName = "SureTemp Plus 690";
        descriptionShort = "Welch Allyn SureTemp Plus 690 electronic thermometer. Measures patient core temperature for hypothermia assessment. Reusable. 215 mm x 81 mm x 62 mm, 12.6 oz (~357 g).";
        picture = "\acm_extended\ui\items\suretemp690_thermometer_ca.paa";
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 1;
        };
    };

    // non-rebreather mask, a reusable o2 tool. it gives high-flow oxygen with a continuous flow sfx.
    class ACM_NRBMask: ACE_ItemCore {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        displayName = "Non-Rebreather Mask";
        descriptionShort = "High-flow oxygen mask (15 L/min, FiO2 ~0.9). Reusable. Apply on the patient's head.";
        picture = "\acm_extended\ui\items\nrbmask_ca.paa";
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 2;
        };
    };
    class ACM_HPMK: ACE_ItemCore {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        displayName = "NAR HPMK";
        descriptionShort = "Hypothermia Prevention & Management Kit. Reusable warming blanket.";
        picture = "\acm_extended\ui\items\HPMK_ca.paa";
        nameSound = "";
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 8;
        };
    };
    // EMMA mainstream capnograph. it attaches inline on a BVM, and the HUD reads out while a medic ventilates.
    class ACM_EMMA: ACE_ItemCore {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        displayName = "EMMA Capnograph";
        descriptionShort = "Mainstream end-tidal CO2 monitor. Attach it to your own BVM; it stays in inventory and follows your BVM between patients.";
        picture = "\acm_extended\ui\emma\emma_etco2_ca.paa";
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 2;
        };
    };
    // combat gauze, hemostatic packing for junctional hemorrhage.
    // it is stage 1 of the two-stage junctional treatment: pack the wound across 15 s, then secure it with a
    // pressure bandage across another 15 s. it is a proper ACE medical item, so it sits in the medical
    // inventory.
    class ACM_CombatGauze: ACE_ItemCore {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        model = "\z\ace\addons\medical_treatment\data\bandage.p3d";
        displayName = "Combat Gauze";
        descriptionShort = "Hemostatic gauze for packing junctional hemorrhage. Pack the wound, then secure with a pressure bandage.";
        picture = "\acm_extended\ui\items\combat_gauze_ca.paa";
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 1;
        };
    };

    // NAR SPEAR decompression needle. it has the same inventory characteristics as ACM's NCD kit.
    class ACME_NARSPEAR: ACM_NCDKit {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        displayName = "NAR SPEAR";
        descriptionShort = "Needle decompression device for pneumothorax and tension pneumothorax.";
        picture = "\acm_extended\ui\items\nar_spear_ca.paa";
    };

    // NAR AAJT-s, the stabilized abdominal aortic and junctional tourniquet.
    // this is a junctional hemorrhage control device with two placements through the medical menu.
    // inguinal, on the body selection: it clamps the aorta, so it controls both leg junctional wounds and
    // tourniquets the legs that have an inguinal wound. it blocks a manual tourniquet on those legs.
    // axilla, on LeftArm or RightArm: it controls the junctional wound of that one arm. there is no tourniquet
    // effect, and a manual tourniquet on that arm is still allowed.
    // on mass: arma inventory has a single mass stat. it is both the weight and the bulk, and there is no separate
    // volume. the real device is about 7.5 by 6.5 by 2 in and about 17 oz, so it is bulky and light.
    // the value is biased to the bulk, because the bulk is what limits how many a medic carries.
    // the scale comes from ACE: ACE_bloodIV is mass 10 for a 1000 mL bag, so one mass unit is about 100 g or
    // about 100 mL. the device is about 1.6 L, which gives 16. true to weight alone would give 5.
    class ACME_AAJT_S: ACE_ItemCore {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        model = "\z\ace\addons\medical_treatment\data\bandage.p3d";
        displayName = "NAR AAJT-S";
        descriptionShort = "Abdominal Aortic & Junctional Tourniquet (Stabilized). Inguinal placement occludes one selected leg; axillary placement occludes one selected arm; Zone 3 REBOA placement occludes both lower extremities. Bulky (~7.5 x 6.5 x 2 in, ~17 oz).";
        picture = "\acm_extended\ui\items\aajt-s_ca.paa";
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 16;  // the volume of the device on the ACE scale. see the note above.
        };
    };

    // XStat 30, an injectable hemostatic sponge bolus for extreme-case junctional control.
    // it is inguinal only. it is much faster than gauze, at a 3 s insert with full control in about 15 s total,
    // and the wound never resolves on its own. the bolus holds it permanently until surgery or a full heal.
    // applying it marks the casualty for surgical removal, permanently impairs the leg so they cannot sprint, and
    // starts a 2-hour dwell timer, after which it rebleeds. it cannot be removed, replaced, reapplied or stacked.
    // it is tiny and light, about 71 g, so it barely takes room. it uses the dedicated xstat_ca.paa treatment and
    // menu icon.
    class ACME_XStat: ACE_ItemCore {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        model = "\z\ace\addons\medical_treatment\data\bandage.p3d";
        displayName = "XStat 30";
        descriptionShort = "Injectable hemostatic sponge bolus for inguinal junctional hemorrhage. Extreme-case: very fast, controls bleeding completely, but permanently impairs the leg and requires surgical removal.";
        picture = "\acm_extended\ui\items\xstat_ca.paa";
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 1;  // about 71 g. it has barely any footprint.
        };
    };

    // spoiled blood.
    // this is what a blood bag becomes when its cold chain lapses. it is a plain inert item and not an
    // ACE_bloodIV, so ACM's transfusion menu cannot list or hang it. a medic cannot give it. discard it.
    class ACME_SpoiledBlood: ACE_ItemCore {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        displayName = "Blood Bag (SPOILED)";
        descriptionShort = "This blood lost its cold chain and is no longer safe to transfuse. Discard it.";
        picture = "\acm_extended\ui\items\spoiled_bloodiv_ca.paa";
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 4;
        };
    };

    // blood coolers, for cold-chain storage.
    // these carry blood cold so it does not spoil. the cold-chain mechanic, fn_bloodcoldchaintick, reads the two
    // custom numbers below. ACME_coolerCapacityMl is how much blood, by volume, the unit keeps cold, and
    // ACME_coolerColdChainTime is how long the coolant lasts, in seconds from mission start. blood beyond the
    // capacity, and any blood once the coolant lapses, is left out in the warm and spoils. see postinit for the
    // loose-blood timer. the real cold-chain figures of 48, 24 and 72 h are compressed hard for operations of
    // about 4 h. tune them in postinit or here.
    // mass is bulk, because arma has a single stat. the 4u is huge on purpose, so it only fits vehicle cargo or a
    // very large pack. it cannot go in a uniform, a vest or a normal ruck.

    // pelican golden hour one-v. it holds 1 unit, a single 500 ml bag, weighs about 2 lb and is the smallest. it
    // has the longest validated cold chain.
    class ACME_BloodCooler_CSWB1U: ACE_ItemCore {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        displayName = "Golden Hour CSWB-1U";
        descriptionShort = "Single-unit blood cold-chain carrier (1x 500 ml). Keeps one unit of blood cold and transfusable; longest coolant life of the three.";
        picture = "\acm_extended\ui\items\goldenhour_cswb1u_ca.paa";
        ACE_isMedicalItem = 1;
        ACME_coolerCapacityMl = 500;
        ACME_coolerColdChainTime = 7200;  // 2 h.
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 50;
        };
    };

    // golden minute CSWB-2u. it holds 2 units, either one 1000 ml bag or two 500 ml bags, weighs about 4.2 lb and
    // is mid size. it has the shortest coolant life.
    class ACME_BloodCooler_CSWB2U: ACE_ItemCore {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        displayName = "Golden Minute CSWB-2U";
        descriptionShort = "Two-unit blood cold-chain carrier. 2000 mL total capacity.";
        picture = "\acm_extended\ui\items\goldenminute_cswb2u_ca.paa";
        ACE_isMedicalItem = 1;
        ACME_coolerCapacityMl = 1000;
        ACME_coolerColdChainTime = 5400;  // 1.5 h.
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 100;
        };
    };

    // golden hour CSWB-4u soft container. it holds 4 units, 2000 ml in any bag combination, and weighs about 7.5
    // lb. it is dimensionally massive, so it fits vehicle cargo and very large packs only. it has the longest
    // coolant life.
    class ACME_BloodCooler_CSWB4U: ACE_ItemCore {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        displayName = "Golden Hour CSWB-4U";
        descriptionShort = "Four-unit blood cold-chain container. 2000 mL total capacity.";
        picture = "\acm_extended\ui\items\goldenhour_cswb4u_ca.paa";
        ACE_isMedicalItem = 1;
        ACME_coolerCapacityMl = 2000;
        ACME_coolerColdChainTime = 10800;  // 3 h.
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 330;  // huge on purpose, so it fits vehicle cargo or a very large pack only.
        };
    };
};

// iv fluid classes for the premixed bags. ACM resolves the type and volume of a bag from ace_medical_treatment
// >> iv >> <datastring>. see acm_circulation_fnc_getfluidbagstring and ivbaglocal. ACM has none of these,
// because esmolol, HTS and calcium are vials and syringe pushes there rather than hung bags, so the old
// EsmololIV_250 and HTSIV_250 data strings of this extension resolved to nothing. these definitions are what
// makes the premixed bags work. they inherit SalineIV, a non-blood crystalloid carrier, and override the type
// and volume. ACM transfuses the volume and the type string drives the drug auto-attach.
class ace_medical_treatment {
    class IV {
        class SalineIV;
        class EsmololIV_250: SalineIV { type = "Esmolol";   volume = 250; };
        class HTSIV_250:     SalineIV { type = "HTS";       volume = 250; };
        class MagnesiumIV_50: SalineIV { type = "Magnesium"; volume = 50; };
        class MannitolIV_500: SalineIV { type = "Mannitol";  volume = 500; };
        class PlasmaLyteIV_1000: SalineIV { type = "PlasmaLyte"; volume = 1000; };
        class PlasmaLyteIV_500:  SalineIV { type = "PlasmaLyte"; volume = 500; };
        class PlasmaLyteIV_250:  SalineIV { type = "PlasmaLyte"; volume = 250; };
        class PlasmaLyteIV_100:  SalineIV { type = "PlasmaLyte"; volume = 100; };
        // small-volume saline bags. these are flush and keep-vein-open reserves for y lines, and for standalone small
        // drips.
        class SalineIV_50:  SalineIV { type = "Saline"; volume = 50; };
        class SalineIV_100: SalineIV { type = "Saline"; volume = 100; };
    };

};

// hang bag: the in-hand iv bag model and the physical iv rope.
// the thin pale-blue line is a custom rope class in ACE's fuelhose pattern. it is a ropesegment whose model is
// ACE's hose.p3d shrunk to about 5 mm diameter with 0.15 m segments, tinted pale blue on the "rope" hidden
// selection.
// BUILD WITH BINARIZE TURNED OFF. this is the verified working setting, not a workaround.
// nothing in this addon needs binarizing. every texture is already DXT5 .paa, there are no .rvmat, and
// models/iv_line_segment.p3d is already ODOL, at version 75. binarize therefore has exactly one file it can act
// on and that file is already in its output format.
// with binarize on, binarize.exe dies with an access violation, exit code -1073741819, after about 14 seconds,
// having printed nothing at all. addon builder reports only that code, so the log says nothing useful.
// note that putting *.p3d in the copy-directly list does NOT stop this. that list only controls which files
// addon builder copies straight through. binarize is invoked separately on the whole source folder and walks
// everything it recognizes regardless. the -exclude argument is what actually gates it, and addon builder points
// that at <source>\acm_extended\exclude.lst, which does not exist unless you create it.
// if a future edit replaces this model with a raw mlod .p3d, that one does have to be binarized, because an
// unbinarized mlod throws "Cannot open object" at runtime. read the first four bytes to tell them apart: ODOL is
// binarized and MLOD is not.
// there is a fallback either way. set ACME_hang_ropeClass to "" for the engine rope, which needs no model at all,
// or to "ACME_IVLine_BlueHose", which reuses ACE's own hose.
// ""                     engine default rope. thin, model-free, and needs no model at all.
// "ACME_IVLine_Rope"     thin pale-blue custom line. the default, and it needs the segment .p3d in the pbo.
// "ACME_IVLine_BlueHose" pale-blue, reusing ACE's binarized hose. it always loads and is hose-thick.
// "ace_refuel_fuelHose"  ACE's stock black hose.
class CfgNonAIVehicles {
    class ACME_IVLine_Segment {
        scope = 2;
        displayName = "IV Line Segment";
        simulation = "ropesegment";
        autocenter = 0;
        animated = 0;
        model = "\acm_extended\models\iv_line_segment.p3d";
    };
};
// the iv line, bag and anchor CfgVehicles classes are merged into the single CfgVehicles block below, so
// mikero rapify does not see two top-level CfgVehicles definitions.

// walk-and-carry pose. a full-body move-state would lock the whole skeleton and stop the medic walking, so a
// gesture overlays the upper body on top of whatever locomotion plays. the legs keep walking or running while
// the left arm raises to hold the bag up. we reuse the bundled standing iv rtm, and the bone mask of the
// gesture drops its lower body so the walk shows through. it loops so the arm stays up, and the hang-bag tick
// re-asserts it so it survives an action interruption.
// two levers for in-game tuning. the inherited base, GestureFreezeStand, is a vanilla upper-body arm gesture
// that sets the bone mask and whether movement is allowed. if it blocks walking, swap to a patrol hand-signal
// gesture base. the other lever is looped and speed, plus the rtm itself if the arm pose needs re-authoring
// for upper-body-only masking.
class CfgGesturesMale {
    class Default;
    class States {
        class GestureFreezeStand;  // vanilla upper-body arm gesture base. it inherits the movement-friendly mask.
        class GestureSpasm3;
        class GestureSpasm4;
        class GestureSpasm5;
        class GestureSpasm6;

        class ACME_IV_Gesture: GestureFreezeStand {
            file = "\acm_extended\animations\acm_iv_stand_lh.rtm";
            looped = 1;
            speed = 0.5;
            disableWeapons = 1;
            canPullTrigger = 0;
            enableOptics = 0;
        };

        // BI's four best whole-body-looking spasm gestures, isolated under ACME action names and played at 1.05x.
        // They retain the original RTMs, masks and interpolation data. Only playback speed changes.
        // Positive speed is clip cycles/second, not a playback multiplier.
        // BI Spasm3-6: 0.238, 0.2325, 0.2069, 0.1287, each multiplied by 1.05.
        class ACME_SeizureSpasm3: GestureSpasm3 { speed = 0.2499; };
        class ACME_SeizureSpasm4: GestureSpasm4 { speed = 0.244125; };
        class ACME_SeizureSpasm5: GestureSpasm5 { speed = 0.217245; };
        class ACME_SeizureSpasm6: GestureSpasm6 { speed = 0.135135; };
    };
};

class CfgFunctions {
    // compile-time override of ACM's ACE medical-menu action renderer. a runtime reassignment did not reliably
    // replace the compiled updateactions function of ACM and ACE, so the left-align setting installs at
    // CfgFunctions.

    // NA3 HR/resistance composition is installed through configuration and exact upstream merges below.
    // Native drug effects and Extended source contributions compose once; no late clinical reassignment.

    // Modified ACM/ACE functions are registered by their owning ACM addons.
    class ACME {
        tag = "ACME";
        class infusion {
            file = "\acm_extended\functions";
            class postInit {};
            class initMedicationRegistry {};
            class initTrainingCasualty {};
            class initInfusionConfig {};
            class initThoracostomyConfig {};
            class initCirculationConfig {};
            class initConsciousnessConfig {};
            class initIVProcedureConfig {};
            class initPatientPositioningConfig {};
            class initMegacodeConfig {};
            class initDrugPhysiologyConfig {};
            class initResuscitationConfig {};
            class initTbiProgressionConfig {};
            class initProcedurePainConfig {};
            class initBlastLungConfig {};
            class initFlightMotionConfig {};
            class initVentilatorClinicalConfig {};
            class initMedicalMenuConfig {};
            class initVentilatorUiPowerConfig {};
            class initPerfusionConfig {};
            class initVentilatorRuntimeConfig {};
            class initFlightPhysiologyConfig {};
            class initAirwayProcedureConfig {};
            class initNarcBoxConfig {};
            class registerTbiRuntime {};
            class registerBlastLungRuntime {};
            class registerCirculationRuntime {};
            class registerVentilatorAudioRuntime {};
            class initNrbRuntime {};
            class initHangBagRuntime {};
            class initHpmkCoreRuntime {};
            class initProcedureEnvironmentConfig {};
            class registerHpmkVisualRuntime {};
            class registerChestSealPresenceRuntime {};
            class registerHpmkTransportCleanupRuntime {};
            class initHypothermiaRuntime {};
            class registerMedicalBodyBaseRuntime {};
            class initBloodStorageRuntime {};
            class registerClinicalLifecycleRuntime {};
            class initHeadAirwayRuntime {};
            class initBlastOverpressureRuntime {};
            class initJunctionalConfig {};
            class initChestSealProcedureRuntime {};
            class registerInjuryPresentationRuntime {};
            class initRhythmTriggerConfig {};
            class initPressureAndAuscultationConfig {};
            class initRhythmHemodynamicsConfig {};
            class initMinigameVentDefaults {};
            class initCardioversionSafetyConfig {};
            class registerCompatibilityCheck {};
            class initMonitorSyncConfig {};
            class registerConsciousnessRuntime {};
            class registerProviderStanceReleaseRuntime {};
            class registerHeadElevationTransportRuntime {};
            class registerRhythmLifecycleRuntime {};
            class registerInfusionProcessingRuntime {};
            class initEmmaRuntime {};
            class registerBvmVentRuntime {};
            class initAedMonitorRuntime {};
            class initRhythmThresholdRuntime {};
            class registerTransfusionUiRuntime {};
            class initHardcoreRuntime {};
            class registerTreatmentRollRuntime {};
            class registerHeadElevationTreatmentRuntime {};
            class registerChestAccessVestRuntime {};
            class chestAccessVestEvent {};
            class chestAccessVestAcquire {};
            class chestAccessVestPark {};
            class chestAccessVestRestore {};
            class chestAccessVestProvider {};
            class chestSealProviderHoldStart {};
            class registerMegacodeInteractionRuntime {};
            class registerVentilatorKeybindRuntime {};
            class initMinigameInteractionRuntime {};
            class registerMedicationDeliveryRuntime {};
            class registerEcgJostleRuntime {};
            class registerSyringeLifecycleRuntime {};
            class initForkStartupRuntime {};

            // Cumulative physiology / Megacode systems introduced after Batch 1.
            class preoxygenationTick {};
            class shockPhenotypeTick {};
            class shockSetPhenotype {};
            class coagulationTick {};
            class aspirationTick {};
            class pulsePerfusionProfile {};
            class expansionBootstrap {};
            class expansionRegisterRuntime {};
            class megacodeAARRecord {};
            class megacodeAARReset {};
            class megacodeAARShow {};
            class megacodeAARTick {};
            class registerDebugWatchdogRuntime {};
            class registerDebugPageKeybindRuntime {};
            class registerThoracicMenuPresentationRuntime {};
            class registerMedicalMenuOpenRuntime {};
            class registerClinicalMenuPresentationRuntime {};
            class initVesicantRuntime {};
            class registerRoscBreathingRuntime {};
            class registerClampDragRuntime {};
            class initTbiCoreState {};
            class initTbiCoreConfig {};
            class registerProcedureIntegrationRuntime {};
            // NA2: explicit networking and collaborative-treatment contracts.
            class ivBagsCommit {};
            class tbiStateCommit {};
            class circStateCommit {};
            class infusionMedicationStateCommit {};
            class yLinesCommit {};
            class detachedBagsCommit {};
            class initNetworkSyncConfig {};
            class medicationRouteAllowed {};
            class medicationTakeSources {};
            class medicationAvailability {};
            class medicationCountRaw {};
            class medicationToxicityTick {};
            class medicationCBRNTick {};
            class medicationRecordIDs {};
            class medicationLineLocal {};
            class medicationRequest {};
            class medicationEscrowCommit {};
            class medicationLineIdentity {};
            class medicationLineFraction {};
            class medicationLeak {};
            class medicationRefund {};
            class medicationAck {};
            class medicationRetry {};
            class medicationExposure {};
            class medicationToxicityFiredCommit {};
            class medicationInteractions {};
            class medicationDriveAdd {};
            class medicationDriveTick {};
            class hardcoreMedicationRateEffect {};
            class ecgJostleLocal {};
            class ecgJostleRequest {};
            class ecgArtifactStrength {};
            class ecgArtifactApply {};
            class sedationThreshold {};
            class sedationPhysiology {};
            class adenosineTick {};
            class suctionStateLocal {};
            class suctionPhysiologyTick {};
            class suctionPublish {};
            class suctionObservers {};
            class ownerDispatch {};
            class patientInteractionDistance {};
            class headElevEffective {};
            class canCheckPatientDogtags {};
            class headElevHoldStart {};
            class headElevHoldRelease {};
            class headElevHoldClear {};
            class headElevHoldStop {};
            class headElevTreatmentEvent {};
            class clinicalInit {};
            class clinicalFields {};
            class clinicalCodec {};
            class clinicalEncodedValid {};
            class clinicalValidate {};
            class clinicalBagRecover {};
            class preparedAttachRequest {};
            class preparedAttachLocal {};
            class preparedAttachAck {};
            class preparedHangCommit {};
            class preparedHangResult {};
            class bagIdentity {};
            class infusionRegisterLocal {};
            class infusionRegisterCore {};
            class infusionAck {};
            class infusionRetire {};
            class infusionRemoveLocal {};
            class yFlushStart {};
            class yFlushTick {};
            class clinicalBagMove {};
            class infusionFlow {};

            class clinicalEpoch {};
            class clinicalNotice {};
            class arrestLocal {};
            class rhythmRelease {};
            class rhythmNative {};
            class shockRequest {};
            class shockLocal {};
            class shockROSC {};
            class clinicalTickDelta {};
            class bpCompute {};
            class clinicalBindings {};
            class clinicalInspect {};
            class clinicalSnapshot {};
            class clinicalRestore {};
            class clinicalReset {};
            class deathFreeze {};
            class deadPhysiologyFreeze {};
            class fluidCommit {};
            class infusionDeliver {};
            class injuryEvent {};
            class aajtOccludes {};
            class junctionalResume {};

            class netNotice {};
            class ownerRegister {};
            class ownerInit {};
            class transientStateReconcile {};
            class providerStateReconcile {};
            class nrbStateLocal {};
            class nrbStateCommit {};
            class nrbSoundServer {};
            class nrbOxygenDraw {};
            class nrbOxygenAck {};
            class chestSealKey {};
            class chestSealActualSide {};
            class chestSealCanPhysicalRoll {};
            class chestSealReset {};
            class chestSealSession {};
            class chestSealRequest {};
            class chestSealEdit {};
            class chestSealAck {};
            class chestSealSyncUI {};
            class chestSealEffectLocal {};
            class chestSealLogOnce {};
            class chestSealNetInit {};

            class a11yColor {};
            class menuLeftAlignTick {};
            class bpNative {};
            class checkTemperature {};
            class tempInjuryEntry {};
            class acmSpawnerArmor {};
            class openFromTransfusionMenu {};
            class openPrepFromInventoryMenu {};
            class givePreparedBag {};
            class openDrawMenu {};
            class patchDrawDialog {};
            class injectIntoBag {};
            class infusionDone {};
            class infusionRefreshTally {};
            class transfusionSpikeOrAdd {};
            class bloodThermalStateCommit {};
            class transfusionYTubing {};
            class transfusionFlushLine {};
            class transfusionPullBag {};
            class transfusionPullCommit {};
            class transfusionPullResult {};
            class rehangUsedBagCommit {};
            class rehangUsedBagResult {};
            class yRefillCommit {};
            class yRefillResult {};
            class discardYTubingCommit {};
            class discardYTubingResult {};
            class discardYTubing {};
            class resumeSiteFlow {};
            class togglePreparedSets {};
            class hangPreparedSet {};
            class yLineAttach {};
            class ySalineSetup {};
            class ySalinePin {};
            class bloodFridgeModuleInit {};
            class bloodFridgeSetup {};
            class bloodFridgeTakeMenu {};
            class bloodFridgeTake {};
            class bloodFridgeTick {};
            class bloodFridgeMenuPoll {};
            class coolerInvHook {};
            class coolerOpenDialog {};
            class coolerOpenCarried {};
            class coolerAutoStore {};
            class coolerRefresh {};
            class coolerClearSlots {};
            class cheyneStokesTick {};
            class debugCheyneStokes {};
            class installRmbCancelGuard {};
            class airwayMedicPose {};
            class airwayInjuryRelabel {};
            class animQueue {};
            class headElevMedicSeq {};
            class ptxTensionTick {};
            class ptxEnsure {};
            class ptxPublish {};
            class ptxInjury {};
            class ptxStep {};
            class ptxTreat {};
            class ptxAmbientChange {};
            class ptxContext {};

            class ivCathSetFrame {};
            class ivMinigamePullTick {};
            class ivMinigamePullStop {};
            class ivNeedleTip {};
            class thoraOutput {};
            class thoraOutputStateCommit {};
            class thoraOutputEntry {};
            class ivSiteIndex {};
            class laryngoTubeEject {};
            class ivCathTex {};
            class ivCathGeometry {};
            class ivLimbBounds {};
            class ivCathPose {};
            class ivMinigameHookCtrl {};
            class ivInfiltrated {};
            class ivMinigameGrabLine {};
            class ivMinigameBandFlag {};
            class ivMinigameSyncBand {};
            class ivMinigameSaveState {};
            class ivMinigameRestoreState {};
            class ivMinigameResetView {};
            class ivMinigamePrepView {};
            class ivMinigameViewValid {};
            class ivMinigameInsertStart {};
            class ivMinigameInsertAdvance {};
            class ivMinigameScroll {};
            class ivMinigameRetract {};
            class ivMinigameLineConnect {};
            class ivSiteRelabel {};
            class ivGaugeRelabel {};
            class ivLogRelabel {};
            class bodyPartName {};
            class medLog {};
            class clinTerm {};
            class inspectForFracture {};
            class woundNameRelabel {};
            class bleedStatusRelabel {};
            class descriptorSelfTest {};
            class ioPainResponse {};
            class ivSiteData {};
            class ivHeldRaise {};
            class ivSeedHub {};
            class doAnim {};
            class medicAnimationPrep {};
            class rollProviderStart {};
            class obtundedMasterChanged {};
            class obtundedWeaponIntent {};
            class ivSiteAtPoint {};
            class ivEnforceSite {};
            class ivPlacementLocal {};
            class ivUiValid {};
            class ivStateLocal {};
            class ivPrepPaint {};
            class ivVenousPhenotype {};
            class ivVeinSet {};
            class ivVeinNearest {};
            class ivPalpModel {};
            class netReport {};
            class ivSiteDifficulty {};
            class ivStickBlows {};
            class ivVeinDist {};
            class ivVeinCatalog {};
            class ivLogSite {};
            class ivMinigameCursor {};
            class ivMinigameGrabBand {};
            class ivMinigameGrabNeedle {};
            class ivMinigameGrabPad {};
            class ivMinigameCleanDone {};
            class ivMinigameRelease {};
            class ivMinigameRenderMarks {};
            class ivExtravasationState {};
            class visualBruiseState {};
            class ivMinigameAddMark {};
            class ivMarkCommit {};
            class ivMinigameClick {};
            class ivMinigameRefreshBandSlot {};
            class ivTrayHover {};
            class ivMinigameRemoveBand {};
            class ivMinigameStickSuccess {};
            class ivMinigameFlip {};
            class ivMinigameRegister {};
            class ivMinigameOpen {};
            class ivMinigamePrepare {};
            class ivMinigameInit {};
            class ivMinigamePan {};
            class ivMinigameTick {};
            class ivMinigameClose {};
            class ivMinigameDone {};
            class coolerLoad {};
            class coolerStateCommit {};
            class coolerUnload {};
            class coolerContentsTick {};
            class take4U {};
            class coolerBoxDeploy {};
            class coolerBoxApplyScale {};
            class coolerBoxPackUp {};
            class coolerBoxColdChainTick {};
            class popClots {};
            class clotPopTick {};
            class cancelInfusionDraw {};
            class restoreMedicationList {};
            class findBestSyringe {};
            class registerBagMedication {};
            class registerPreparedBag {};
            class findPreparedBagIndex {};
            class findTrackedBag {};
            class bagInfusionEntry {};
            class findRunningDirtyEpi {};
            class isYLineAccess {};
            class isYLineBagContext {};
            class canMedicateBagContext {};
            class findNewestBagContext {};
            class getSelectedActiveBagContext {};
            class getSelectedInventoryBagContext {};
            class getSelectedInfusionEntryIndexes {};
            class isSalineItem {};
            class getSalineVolumeFromItem {};
            class handleInfusions {};
            class updateTransfusionControls {};
            class updateTransfusionAccessHotspots {};
            class selectTransfusionAccess {};
            class transfusionAccessValid {};
            class transfusionRemoveBagCommit {};
            class transfusionRemoveBagResult {};
            class transfusionFlowToggleCommit {};
            class updateEJTransfusionMenu {};
            class selectEJTransfusionSite {};
            class adjustDripRate {};
            class cycleDropSet {};
            class formatDose {};
            class formatRate {};
            class formatPreparedLabel {};
            class formatInfusionLabel {};
            class getSelectedPreparedInfusion {};
            class restorePausedFlow {};
            class clampPositionToDrops {};
            class dropsToClampPosition {};
            class openRollerClamp {};
            class onClampLoad {};
            class updateClampDialog {};
            class setClampPosition {};
            class scrollClamp {};
            class placeClampWheel {};
            class playClampSfx {};
            class syringeKitOpen {};
            class syringeKitOnLoad {};
            class syringeKitRender {};
            class syringeKitTick {};
            class syringeKitGrab {};
            class syringeKitInfo {};
            class syringeKitSize {};
            class syringeKitSource {};
            class syringeKitWaste {};
            class syringeKitDraw {};
            class skOpenDraw {};
            class uiCanvas {};
            class skInject {};
            class givePremixedSet {};
            class pressureInfuserCan {};
            class reopenTransfusion {};
            class skClickSound {};
            class skUpdateBody {};
            class menuActionInfo {};
            class menuDropdownState {};
            class menuExamineGroups {};
            class procedureAllowed {};
            class procedureActionAllowed {};
            class thoraKitItem {};
            class thoraCanOpen {};
            class thoraAftercare {};
            class skClose {};
            class skIMGeometry {};
            class skListRefresh {};
            class skListSelect {};
            class skSiteClick {};
            class skSiteGeometry {};
            class skUiTick {};

            class skPickSize {};
            class skApplySize {};
            class skPageNavigate {};
            class skPickFlush {};
            class skWasteBegin {};
            class skWasteToggleMove {};
            class skWasteCommit {};
            class skWasteDraw {};
            class skFlushSave {};
            class epinephrineTakeSource {};
            class epinephrineRecipe {};
            class epinephrinePrepare {};
            class skEpinephrineStock {};
            class epinephrineDrawCardiac {};
            class skEpinephrineDose {};
            class epinephrinePushStored {};
            class epinephrineBolusLocal {};

            class skWasteEnd {};
            class skCompoundLabel {};
            class skCompoundBegin {};
            class skCompoundDraw {};
            class skCompoundSave {};
            class skCompoundCommit {};
            class skRefreshDrawn {};
            class skFinalName {};
            class skCarouselToggle {};
            class skCarouselMove {};
            class skCarouselRender {};
            class skStoreEnsureIds {};
            class narcStoreCommit {};
            class skSelectStored {};
            class skSelectedIndex {};
            class skAfterStoredRemoval {};
            class skBodySyringeRender {};
            class skBodySyringeMove {};
            class skTagCommit {};
            class skTagColor {};
            class skTagEditOpen {};
            class skTagEditDone {};
            class skSyringeSummary {};
            class skSyringeRemembered {};
            class skDefaultTagColor {};
            class skApplyPendingTag {};
            class skPendingTagReset {};
            class skPendingTagCommit {};
            class skPendingTagColor {};
            class skPendingTagRender {};
            class skPendingTagEnsure {};
            class skAfterSaveOpenBody {};
            class skDynamicLayout {};
            class skCarouselHover {};
            class skCarouselPick {};
            class skSyringeSelfMenu {};
            class skOpenStoredSyringe {};
            class skPickDrawn {};
            class skToggleView {};
            class skSiteName {};
            class medDescriptor {};
            class laryngoIcpSurge {};
            class fentanylOnBoard {};
            class skSetView {};
            class skBuildHotspots {};
            class skInjectSite {};
            class skBeginInjection {};
            class skConfirmInjection {};
            class medicationSuggestedPushSec {};
            class hardcorePushStart {};
            class hardcorePushTick {};
            class hardcorePushSendBatch {};
            class hardcorePushStop {};
            class hardcorePushFinalize {};
            class hardcorePushAck {};
            class hardcorePushRestoreDelta {};
            class hardcorePushOverlay {};
            class hardcorePushReopen {};
            class hardcorePushRestoreUi {};
            class skBodyActionRender {};
            class skBodyActionClick {};
            class skDiscardSelected {};
            class skFlushSite {};
            class skToggleRoute {};
            class directPressureStart {};
            class directPressureHasFracture {};
            class directPressureFracturePain {};
            class directPressureSelf {};
            class directPressureTorso {};
            class directPressureLimb {};
            class directPressureTick {};
            class directPressureStop {};
            class directPressureAssess {};
            class directPressureDraw3D {};
            class measureBPWrap {};
            class updateJunctionalImage {};
            class updateEJImage {};
            class updateETTubeImage {};
            class removeEJ {};
            class junctionalInflict {};
            class junctionalPackDone {};
            class junctionalPackSfxStart {};
            class junctionalPackSfxStop {};
            class aajtDownedTick {};
            class aajtDownedStop {};
            class aajtForceProne {};
            class aajtPainTick {};
            class junctionalWrapDone {};
            class junctionalRollSpawn {};
            class junctionalStartBleed {};
            class junctionalWrapSfxStart {};
            class junctionalWrapSfxStop {};
            class wrapSfxInit {};
            class wrapSfxStart {};
            class wrapSfxStop {};
            class wrapSfxServer {};
            class markImportantSfx {};
            class directPressurePose {};
            class patientAnimRequest {};
            class patientAnimRelease {};
            class treatmentPatientSettle {};
            class junctionalInjuryEntry {};
            class junctionalGuiSyncTick {};
            class aajtInjuryEntry {};
            class seizureInjuryEntry {};
            class seizureCollapse {};
            class benzoOnBoard {};
            class seizureControl {};
            class forceRagdoll {};
            class aajtApply {};
            class aajtRemove {};
            class aajtStateCommit {};
            class aajtSetLegTQ {};
            class aajtTqHideImage {};
            class aajtTqHideInjury {};
            class cyanosisHideInjury {};
            class xstatApply {};
            class junctionalFullHeal {};
            class bloodColdChainTick {};
            class bloodColdChainNudge {};
            class ccApply {};
            class assessBleeding {};
            class chestSealOpen {};
            class chestSealPatientBegin {};
            class chestSealPatientEnd {};
            class chestSealParkCarrier {};
            class chestSealInit {};
            class chestSealGenHoles {};
            class chestSealBumpVer {};
            class chestSealPeel {};
            class chestSealBurp {};
            class chestSealBurpReady {};
            class chestSealOcclusionTick {};
            class hcCircTick {};
            class hcVentTick {};
            class chestSealPresenceSend {};
            class chestSealPresenceRender {};
            class chestSealTrackWound {};
            class chestSealRender {};
            class chestSealTick {};
            class chestSealMouseCoords {};
            class chestSealMouseDown {};
            class chestSealMouseUp {};
            class chestSealScroll {};
            class chestSealSealAt {};
            class chestSealSnd {};
            class chestSealFlip {};
            class chestSealFlipTick {};
            class thoraOpen {};
            class thoraInit {};
            class thoraClose {};
            class thoraRender {};
            class thoraRenderBruises {};
            class thoraFlip {};
            class thoraTick {};
            class thoraBumpVer {};
            class thoraMouseDown {};
            class thoraAftercareLocal {};
            class thoraCanSweep {};
            class thoraSealAt {};
            class thoraSealScroll {};
            class thoraSideStateCommit {};
            class thoraMouseUp {};
            class thoraSelectTool {};
            class thoraClosureMode {};
            class thoraClosureArt {};
            class thoraSlotHover {};
            class thoraCursorUV {};
            class thoraDrawIncision {};
            class thoraRenderPrep {};
            class thoraRenderOpen {};
            class thoraRenderTube {};
            class thoraUpdateTrayIcons {};
            class thoraPassiveDrain {};
            class thoraSutureTube {};
            class surgicalCasualtyCommit {};
            class thoraBloodStain {};
            class breathSoundsStart {};
            class chestSealRoll {};
            class chestSealRefreshSlot {};
            class chestSealToggleHeld {};
            class chestSealApply {};
            class chestSealPrompt {};
            class chestSealCanApply {};
            class chestSealCanNAR {};
            class chestSealRefreshSpearSlot {};
            class chestSealToggleSpear {};
            class chestSealApplyNCD {};
            class chestSealClose {};
            class moveInfusionBag {};
            class removeInfusionBag {};
            class relinkInfusionBag {};
            class tbiInit {};
            class tbiGetMAP {};
            class tbiIsVolumeAdequate {};
            class tbiHandle {};
            class evacuationRequirementCommit {};
            class tbiApplyOsmotherapy {};
            class tbiApplyPressorMAP {};
            class tbiApplyVitals {};
            class tbiAssessPupils {};
            class tbiOsmoBolus {};
            class headElevateCanStart {};
            class headElevateStart {};
            class headElevateStop {};
            class headElevYieldForRoll {};
            class releasePatient {};
            class patientHeldByOther {};
            class headElevAnimGuard {};
            class doAnimHeld {};
            class setVarNet {};
            class setVarNetApprox {};
            class headElevDeathRelease {};
            class headElevVestRestore {};
            class headElevWatch {};
            class headElevMedicStart {};
            class headElevateCancelSeq {};
            class headElevApplyTilt {};
            class headElevSuspend {};
            class headElevRestAnim {};
            class headElevPinPose {};
            class headElevCollision {};
            class headElevResume {};
            class headElevTryResume {};
            class headElevTuneOpen {};
            class headElevPropApply {};
            class propEaseTo {};
            class headElevTuneLoad {};
            class headElevTuneUpdate {};
            class headElevTuneReport {};
            class circHandle {};
            class salineAcidosisTrack {};
            class administerPushDoseEpi {};
            class administerCalcium {};
            class applyCalciumCredit {};
            class calciumCreditCommit {};
            class toggleShock {};
            class toggleOverResus {};
            class setObtunded {};
            class obtundedTick {};
            class obtundedInputLock {};
            class obtundedVoice {};
            class obtundedApply {};
            class obtundedTransition {};
            class obtundedSet {};
            class obtundedStateCommit {};
            class debugObtundedBack {};
            class obtundedAuto {};
            class consciousnessBudget {};
            class toggleHypothermia {};
            class readCoreTemp {};
            class nrbAirwayCompatible {};
            class nrbApply {};
            class nrbRemove {};
            class hpmkWrap {};
            class hpmkRemove {};
            class hpmkPrep {};
            class hpmkPickUp {};
            class remoteSay3D {};
            class remoteDeleteVehicle {};
            class forceWalkLocal {};
            class updateHpmkImage {};
            class hpmkUnwrap {};
            class hpmkExposeChest {};
            class hpmkCoverChest {};
            class updateHpmkUnwrapped {};
            class emmaAttach {};
            class emmaAttachIGel {};
            class emmaIGelStateCommit {};
            class emmaCanAttachIGel {};
            class emmaAirwayKind {};
            class emmaCanRemoveIGel {};
            class emmaClearIGelForMedic {};
            class emmaMarkContact {};
            class emmaRemove {};
            class emmaRemoveIGel {};
            class emmaTick {};
            class emmaBuildDisplay {};
            class bvmVentTick {};
            class vesicantRouteAllows {};
            class vesicantInjure {};
            class vesicantRegistryCommit {};
            class vesicantTick {};
            class vesicantReverse {};
            class ivExtravasationCheck {};
            class hpmkTick {};
            class hpmkStateCommit {};
            class hpmkBlanketTick {};
            class hpmkSpawnBlanket {};
            class nrbTick {};
            class suctionSfxStart {};
            class suctionSfxStop {};
            class headInjuryTBI {};
            class genRhythmEKG {};
            class rhythmTick {};
            class rhythmToggle {};
            class minigameOpen {};
            class minigameClose {};
            class minigameReopen {};
            class aceCursorRestore {};
            class rhythmGet {};
            class peaIsWide {};
            class rhythmSet {};
            class rhythmActiveCommit {};
            class rhythmNativeHoldCommit {};
            class rhythmNativeHighHRFloorCommit {};
            class rhythmNativeShockGraceCommit {};
            class rhythmAFibRVR {};
            class rhythmAFib {};
            class rhythmAtrialTach {};
            class rhythmTorsades {};
            class rhythmSVT {};
            class rhythmDiag {};
            class salineFlush {};
            class place18g {};
            class remove18g {};
            class syncPremixedBags {};
            class debugMenu {};
            class debugMenuClinical {};
            class debugMenuNetwork {};
            class ejTexturePath {};
            class debugDumpToClipboard {};
            class debugEnabled {};
            class autoBPCondition {};
            class toggleAutoBP {};
            class autoBPTick {};
            class toggleClamp {};
            class closeClamp {};
            class aedSyncSetup {};
            class aedBeatClockTick {};
            class rhythmThresholdTick {};
            class lidoEffectiveness {};
            class lidoToxTick {};
            class debugInduceSeizure {};
            class seizureMotion {};
            class seizureGestureAdvance {};
            class seizureGestureSync {};
            class clearAllAilments {};
            class syncToggle {};
            class syncCardiovert {};
            class syncFlagsTick {};
            // ambient temp and the hypothermia auto-drivers.
            class ambientTemp {};
            class hypothermiaTick {};
            class hypothermiaTemperatureCommit {};
            // skin pallor and the "Feel Skin" action.
            class skinSigns {};
            class feelSkin {};
            class skinInjuryEntry {};
            // TBI blast, or overpressure, trigger.
            class tbiBlast {};
            // magnesium, for torsades.
            class administerMagnesium {};
            // hang bag, for gravity-assisted high flow and the iv line.
            class hangBagCanStart {};
            class hangBagFromMenu {};
            class pressureInfuserAttach {};
            class pressureInfuserCommit {};
            class pressureInfuserStateCommit {};
            class pressureInfuserAck {};
            class pressureInfuserTick {};
            class hangBagPrep {};
            class hangBagPrepStop {};
            class hangBagFluidType {};
            class hangBagStart {};
            class hangBagActivate {};
            class hangBagClaimLocal {};
            class hangBagClaimAck {};
            class hangBagVisualSync {};
            class hangBagTick {};
            class hangBagStop {};
            class hangBagRestoreWeapons {};
            class hangBagInputLock {};
            class hangBagHint {};
            class hangBagTuneOpen {};
            class hangBagTuneLoad {};
            class hangBagTuneUpdate {};
            class hangBagTuneReport {};
            class inspectChestPoseStart {};
            class inspectChestPoseStop {};
            class treatmentPoseStart {};
            class treatmentGesture {};
            class treatmentPoseStop {};
            class treatmentPoseSync {};
            class providerStanceOwned {};  // Batch 07
            class beginStethoscopeAction {};
            class stethoscopeInit {};
            class stethoscopeSetView {};
            class stethoscopeEntryFlip {};
            class stethoscopeEntryFlipTick {};
            class stethoscopeFlip {};
            class stethoscopeFlipTick {};
            class stethoscopeTick {};
            class stethoscopeWeights {};
            class stethoscopeClose {};
            class rollProviderCancel {};
            class patientRollCancel {};
            class ivLineCreate {};
            class ivLineDestroy {};
            // megacode kelly, the zeus training manikin and its control panel.
            class megacodeSpawn {};
            class megacodeModuleInit {};
            class zeusInflictJunctional {};
            class zeusInflictJunctionalLocal {};
            class zeusInduceObtundation {};
            class zeusInflictBlastLung {};
            class zeusInflictEdema {};
            class zeusClearEdema {};
            class edemaSet {};
            class zeusInflictTBI {};
            class zeusInsertIV {};
            class zeusIVDialogConfirm {};
            class zeusIVDialogSite {};
            class zeusTBIDialogConfirm {};
            class zeusTBIApplyLocal {};
            class zeusClearTBI {};
            class zeusClearTBILocal {};
            class bloodFridgeSpawn {};
            class bloodFridgeDialogConfirm {};
            class bloodFridgeContents {};
            class bloodFridgeContentsFill {};
            class ventPanelOpen {};
            class ventLevelWindow {};
            class ventVeilRaise {};
            class ventFlip {};
            class ventBootStart {};
            class laryngoFlash {};
            class airwayGrade {};
            class airwayHasFacialBurn {};
            class laryngoFail {};
            class laryngoAbort {};
            class laryngoCanAttempt {};
            class laryngoDrag {};
            class laryngoTeeth {};
            class laryngoTeethArt {};
            class laryngoBleed {};
            class ventFaceGate {};
            class ventPanelShowDyn {};
            class ventPanelHideScreen {};
            class ventConnectPatient {};
            class ventDisconnectPatient {};
            class ventDeviceFields {};
            class ventRecoveryNear {};
            class ventPatientClear {};
            class ventInventoryLocal {};
            class ventCustodyInit {};
            class ventCustodyRequest {};
            class ventCustodyAck {};
            class ventCustodyTick {};
            class ventItemGate {};
            class ventMinuteVolume {};
            class ventMVLimits {};
            class ventTechPrompt {};
            class ventModeTitle {};
            class permHypoBleedMult {};
            class oxygenDelivery {};
            class cbColor {};
            class ventColor {};
            class ventBatteryTick {};
            class swapVentBattery {};
            class canSwapVentBattery {};
            class ventPanelInit {};
            class ventPanelTick {};
            class ventPanelRefresh {};
            class ventPanelFieldClick {};
            class ventPanelKnob {};
            class ventPanelStripClick {};
            class ventPanelClose {};
            class ventPanelShowScreen {};
            class ventPanelListRefresh {};
            class ventPanelValueFields {};
            class ventCustomLayout {};
            class ventAlarmLetter {};
            class ventLogbookAdd {};
            class ventLeashTick {};
            class ventPanelSetValue {};
            class ventNavStrip {};
            class ventPanelListClick {};
            class ventPanelActivateSel {};
            class ventPanelLiveEdit {};
            class applyHardcore {};
            class ventPanelLiveRefresh {};
            class ventDriveTick {};
            class ventEffectiveSettings {};
            class ventSimpleManualBreath {};
            class ventManualBreath {};
            class ventManualBreathCommit {};
            class ventAlarmTick {};
            class ventHoldClear {};
            class ventMmbUp {};
            class ventHoldTick {};
            class ventPowerOff {};
            class ventPowerDown {};
            class ventStopHard {};
            class ventHardStopCommit {};
            class ventAlarmSilence {};
            class ventAlarmWindow {};
            class ventAlarmSeverity {};
            class ventStatusTick {};
            class ventFormatIE {};
            class motionShake {};
            class motionSmooth {};
            class animBlocked {};
            class uiShakeApply {};
            class lightSelect {};
            class lightExtras {};
            class installLightKey {};
            class flashlightDiag {};
            class debugForceShake {};
            class initVisualEffectsConfig {};
            class visualFxTick {};
            class visualFxDebugCycle {};
            class visualFxDebugClear {};
            class compatCheck {};
            class altitudeTick {};
            class altitudeDatum {};
            class altitudeTrue {};
            class vomitDislodgeOPA {};
            class flightChill {};
            class vehicleOpenness {};
            class ventOxygenation {};
            class darknessShade {};
            class minigameVisionClear {};
            class minigameVisionProfile {};
            class minigameVisionNative {};
            class minigameVisionTick {};
            class minigameInputBindings {};
            class minigameInputMatch {};
            class minigameInputMouse {};
            class minigameInput {};
            class minigameInputInstall {};
            class ventFlipKeyHint {};
            class capnoMorph {};
            class ettAirwayStateCommit {};
            class ettMigrationStateCommit {};
            class ettMainstemTick {};
            class laryngoFrames {};
            class laryngoCreak {};
            class laryngoScroll {};
            class laryngoRegrip {};
            class laryngoCuff {};
            class laryngoCuffDone {};
            class laryngoTubePose {};
            class laryngoCollarSet {};
            class laryngoTubeAnchor {};
            class laryngoCollarRemove {};
            class laryngoCuffDeflate {};
            class laryngoFluid {};
            class laryngoGag {};
            class laryngoSuction {};
            class laryngoExtubate {};
            class laryngoSuctionPin {};
            class laryngoSuctionDrain {};
            class laryngoFluidSync {};
            class laryngoFluidState {};
            class laryngoFluidDrain {};
            class laryngoFluidDrainLocal {};
            class suctionDevice {};
            class suctionSelectDevice {};
            class suctionBulb {};
            class zeroPad {};
            class suctionOpen {};
            class ettMigrate {};
            class ettObstructTick {};
            class ettWakeGuard {};
            class airwayVomitOPA {};
            class laryngoPersistBleed {};
            class laryngoTubeFrames {};
            class sedationOnBoard {};
            class sedationActive {};
            class preparedComponents {};
            class vialHolder {};
            class vialClass {};
            class vialMedication {};
            class vialItemCount {};
            class itemCount {};
            class itemTake {};
            class itemList {};
            class vialCapacity {};
            class vialPreview {};
            class medicationSourceRows {};
            class patientUpright {};  // B56
            class poseUprightState {};  // B56
            class menuPoseStart {};  // B56
            class menuPoseStop {};  // B56
            class skMedicationSync {};
            class skMedicationStockRefresh {};
            class skMedicationSelect {};
            class vialSession {};
            class vialTake {};
            class openVialStoreCommit {};
            class vialRefund {};
            class vialLeaseCommit {};
            class vialLeaseEnsure {};
            class vialLeaseRelease {};
            class vialLeaseResult {};
            class infusionVialVolume {};
            class infusionTakeSupplies {};
            class infusionRefundSupplies {};
            class queueInfusionClamp {};
            class infusionDrawStock {};
            class syringeDrawSetAmount {};
            class sedationComponents {};
            class proceduralAnalgesiaOnBoard {};
            class proceduralAnesthetized {};
            class laryngoStimulusLocal {};
            class laryngoStimulusEffect {};
            class laryngoView {};
            class laryngoConsequence {};
            class laryngoConsequenceLocal {};
            class laryngoReflexChance {};
            class laryngoIrritationTick {};
            class infusionClampLocal {};

            class propofolOnBoard {};
            class midazolamTick {};
            class sugammadexTick {};
            class sugammadexOnBoard {};
            class ettAirwayProtect {};
            class blastLungInflict {};
            class blastLungStateCommit {};
            class blastLungArdsCommit {};
            class blastLungEpisodeCommit {};
            class blastSolve {};
            class ncdAirLeakTick {};
            class blastApply {};
            class blastDetonated {};
            class blastLungTick {};
            class ventShuntCommit {};
            class ventPanelNavClick {};
            class laryngoOpen {};
            class laryngoInit {};
            class laryngoTick {};
            class laryngoGrab {};
            class laryngoClick {};
            class laryngoRefreshSlots {};
            class traySlotState {};
            class laryngoPassTube {};
            class laryngoClose {};
            class reopenMedicalMenu {};
            class ketamineOnBoard {};
            class ketamineSedationTick {};
            class rocuroniumOnBoard {};
            class rocuroniumTick {};
            class rocParalysisCommit {};
            class rocStressStateCommit {};
            class rocAwarenessStateCommit {};
            class rocAwakeParalysisCommit {};
            class rocApneaCommit {};
            class megacodeStanceLock {};
            class megacodeOpenPanel {};
            class megacodeClosePanel {};
            class megacodePanelLoad {};
            class megacodeCableTunerOpen {};
            class megacodeCableTunerLoad {};
            class megacodeCableApply {};
            class megacodeLaptopOrient {};
            class megacodeLaptopMove {};
            class megacodePanelTick {};
            class megacodeMenu {};
            class megacodeLog {};
            class megacodeResetUnit {};
            class megacodeRespawn {};
            class megacodePanelRetarget {};
            class megacodeWatch {};
            class megacodeDie {};
            class megacodeScenario {};
            class megacodeScenarioTick {};
            class megacodeSetVital {};
            class megacodeSetRhythm {};
            class megacodeAddWound {};
            class megacodeSpawnJunctional {};
            class megacodeClearWounds {};
            class megacodeSetAirway {};
            class megacodeSetFeature {};
            class megacodeReset {};
            class megacodeArrest {};
            class megacodeChestInjury {};
        };
    };
};

// B72: QEDaveMergens replaces the previous syringe-tag handwriting family. Arma requires generated .fxy/.paa
// font assets at the configured base path; runtime tag controls fall back to Caveat only when those assets are absent.
class CfgFontFamilies {
    class ACME_QEDaveMergens {
        fonts[] = {"\acm_extended\ui\fonts\QEDaveMergens\QEDaveMergens96"};
        spaceWidth = 0.42;
        spacing = 0.02;
    };
};

class RscText;
class RscButton;
class RscPicture;
class RscPictureKeepAspect;
class RscListBox;
class RscXSliderH;
class RscEdit;

// add chest-tube markers to ACE's medical-menu body image. they inherit the torso chest-seal position, use our
// textures and airway blue, and are hidden by default. the ace_medical_gui_updateBodyImage event toggles them
// per side. see postinit.
class RscControlsGroupNoScrollbars;
class RscControlsGroupNoHScrollbars;
class ace_medical_gui_BodyImage: RscControlsGroupNoScrollbars {
    class Controls {
        class Torso_ChestSeal;
        class ACME_Torso_ChestTube_Right: Torso_ChestSeal {
            idc = 70190;
            text = "\acm_extended\ui\chest_tube_body_right_ca.paa";
            colorText[] = {0.19, 0.91, 0.93, 1};
            show = 0;
        };
        class ACME_Torso_ChestTube_Left: Torso_ChestSeal {
            idc = 70191;
            text = "\acm_extended\ui\chest_tube_body_left_ca.paa";
            colorText[] = {0.19, 0.91, 0.93, 1};
            show = 0;
        };
        // chest bruising overlay. it shows for blast lung and for genuine extensive chest bruising, from a hemothorax
        // or internal bleeding, and it uses the same artwork on purpose. on inspection they look alike and the
        // provider has to tell them apart. the tell is the injury list rather than the picture, because extensive
        // bruising prints its text entry and blast lung prints nothing. see the updateinjurylistpart handler in
        // postinit.
        // the color is bruise-purple rather than the airway blue used for devices.
        class ACME_Torso_BlastLung_Right: Torso_ChestSeal {
            idc = 70192;
            text = "\acm_extended\ui\blast_lung_right_ca.paa";
            colorText[] = {0.62, 0.28, 0.72, 1};
            show = 0;
        };
        class ACME_Torso_BlastLung_Left: Torso_ChestSeal {
            idc = 70193;
            text = "\acm_extended\ui\blast_lung_left_ca.paa";
            colorText[] = {0.62, 0.28, 0.72, 1};
            show = 0;
        };
    };
};

// Category label is shared by self/other patients and grouped/flat menu modes.
class ACE_Medical_Menu {
    class Controls {
        class Triage;
        class Medication: Triage {
            tooltip = "IV / Medication";
        };
    };
};

// ACM explicitly mutes Button_Draw. Restore the normal Arma button sound arrays.
// Button_Inject and Button_Push retain their original inheritance and action handlers.
class ACM_circulation_SyringeDraw_Dialog {
    class Controls {
        class Button_Draw: RscButton {
            soundClick[] = {"\a3\ui_f\data\sound\rscbutton\soundClick", 0.09, 1};
            soundEnter[] = {"\a3\ui_f\data\sound\rscbutton\soundEnter", 0.09, 1};
            soundPush[] = {"\a3\ui_f\data\sound\rscbutton\soundPush", 0.09, 1};
            soundEscape[] = {"\a3\ui_f\data\sound\rscbutton\soundEscape", 0.09, 1};
        };
        class Button_Inject: Button_Draw {
            soundClick[] = {"\a3\ui_f\data\sound\rscbutton\soundClick", 0.09, 1};
            soundEnter[] = {"\a3\ui_f\data\sound\rscbutton\soundEnter", 0.09, 1};
            soundPush[] = {"\a3\ui_f\data\sound\rscbutton\soundPush", 0.09, 1};
            soundEscape[] = {"\a3\ui_f\data\sound\rscbutton\soundEscape", 0.09, 1};
        };
        class Button_Push: Button_Inject {
            soundClick[] = {"\a3\ui_f\data\sound\rscbutton\soundClick", 0.09, 1};
            soundEnter[] = {"\a3\ui_f\data\sound\rscbutton\soundEnter", 0.09, 1};
            soundPush[] = {"\a3\ui_f\data\sound\rscbutton\soundPush", 0.09, 1};
            soundEscape[] = {"\a3\ui_f\data\sound\rscbutton\soundEscape", 0.09, 1};
        };
    };
};

// static overlay label, used by the optional left-aligned medical menu runtime path. the click target stays the
// real ACM and ACE button underneath, and this control draws the text only.
class ACME_MedicalMenu_LeftText: RscText {
    idc = -1;
    style = 0;
    text = "";
    font = "RobotoCondensed";
    sizeEx = "(((((safezoneW / safezoneH) min 1.2) / 1.2) / 25) * 0.72)";
    colorText[] = {0.898, 0.898, 0.898, 1};
    colorBackground[] = {0, 0, 0, 0};
    shadow = 0;
};

// fully transparent button base for the runtime SYNC hotspot. it mirrors ACM's button_power, so the key has no
// visible fill, hover, border or sound. it is an invisible click target over the texture.
class ACME_AEDSyncButton: RscButton {
    style = 0;
    text = "";
    colorText[] = {1,1,1,0};
    colorDisabled[] = {1,1,1,0};
    colorBackground[] = {1,1,1,0};
    colorBackgroundDisabled[] = {1,1,1,0};
    colorBackgroundActive[] = {1,1,1,0};
    colorFocused[] = {1,1,1,0};
    colorBorder[] = {0,0,0,0};
    soundEnter[] = {};
    soundPush[] = {};
    soundClick[] = {};
    soundEscape[] = {};
    shadow = 0;
};

// invisible ej click target for ACM's transfusion body diagram. it keeps the hover and click behavior on the
// icon itself and does not draw a black button panel.
class ACME_EJTransfusionHotspot: RscButton {
    style = 0;
    text = "";
    colorText[] = {1,1,1,0};
    colorDisabled[] = {1,1,1,0};
    colorBackground[] = {0,0,0,0};
    colorBackgroundDisabled[] = {0,0,0,0};
    colorBackgroundActive[] = {0,0,0,0};
    colorFocused[] = {0,0,0,0};
    colorBorder[] = {0,0,0,0};
    soundEnter[] = {};
    soundPush[] = {};
    soundClick[] = {"\a3\ui_f\data\sound\rscbutton\soundClick", 0.09, 1};
    soundEscape[] = {};
    shadow = 0;
    sizeEx = 0;
};

// cooler bay click target. the focused and active background of the base RscButton is dark, which blacks out
// the whole bay when a player clicks a unit. here those states are a faint translucent gold instead, so a click
// reads as a soft highlight rather than a black panel.
class ACME_CoolerHotspot: RscButton {
    style = 0;
    text = "";
    colorText[] = {1,1,1,0};
    colorDisabled[] = {1,1,1,0};
    colorBackground[] = {0,0,0,0};
    colorBackgroundDisabled[] = {0,0,0,0};
    colorBackgroundActive[] = {1,0.85,0.30,0.22};
    colorFocused[] = {1,0.85,0.30,0.14};
    colorBorder[] = {0,0,0,0};
    soundEnter[] = {};
    soundPush[] = {};
    soundClick[] = {};
    soundEscape[] = {};
    shadow = 0;
};
// re-opening of the controls of the dialog. see the body-image lesson. this addon loads after ACM, so this
// onload wins. everything else on the dialog is inherited from ACM untouched.
class ACM_circulation_Lifepak_Monitor_Dialog {
    onLoad = "_this call ACME_fnc_aedSyncSetup";
    // Local operator/SYNC intent belongs to this display only. Clear it on close so an out-of-dialog
    // AdministerShock call cannot reuse a stale local SYNC choice from an older patient/session.
    onUnload = "uiNamespace setVariable ['ACM_circulation_AEDMonitor_DLG', nil]; uiNamespace setVariable ['ACME_sync_localArmed', nil]; missionNamespace setVariable ['ACM_circulation_AED_Monitor_Medic', objNull]";
};

class ACME_RollerClamp_Dialog {
    idd = 86200;
    movingEnable = 0;
    enableSimulation = 1;
    onLoad = "[_this select 0] call ACME_fnc_minigameInputInstall; call ACME_fnc_onClampLoad";
    onMouseZChanged = "_this call ACME_fnc_scrollClamp";
    onUnload = "[uiNamespace getVariable ['ACME_RollerClamp_Position',1], true, false] call ACME_fnc_setClampPosition; uiNamespace setVariable ['ACME_RollerClamp_DLG', displayNull]; uiNamespace setVariable ['ACME_RollerClamp_InitDisplay', displayNull]; uiNamespace setVariable ['ACME_RollerClamp_Dragging', false]; uiNamespace setVariable ['ACME_RollerClamp_ReleaseOnUp', false]; uiNamespace setVariable ['ACME_RollerClamp_Track', []];";

    class ControlsBackground {
        class ACME_Backdrop: RscText {
            idc = 86210;
            text = "";
            x = "safeZoneX + (safeZoneW / 2) - (safeZoneW / 4.65)";
            y = "safeZoneY + (safeZoneH / 2) - (safeZoneH / 2.55)";
            w = "safeZoneW / 2.33";
            h = "safeZoneH / 1.28";
            colorBackground[] = {0,0,0,0.78};
            colorText[] = {1,1,1,1};
        };
        class ACME_ClampBG: RscPicture {
            idc = 86201;
            text = "\acm_extended\ui\roller_clamp_bg.paa";
            x = "safeZoneX + (safeZoneW / 2) - (safeZoneW / 18)";
            y = "safeZoneY + (safeZoneH / 2) - (safeZoneH / 2.95)";
            w = "safeZoneW / 9";
            h = "safeZoneH / 1.55";
            colorText[] = {1,1,1,1};
        };
    };

    class Controls {
        class ACME_Wheel: RscPicture {
            idc = 86202;
            text = "\acm_extended\ui\roller_clamp_whl.paa";
            x = "safeZoneX + (safeZoneW / 2) - (safeZoneW / 45)";
            y = "safeZoneY + (safeZoneH / 2)";
            w = "safeZoneW / 18";
            h = "safeZoneH / 7";
            colorText[] = {1,1,1,1};
        };
        class ACME_DragOverlay: RscButton {
            idc = 86203;
            text = "";
            colorText[] = {1,1,1,0};
            colorDisabled[] = {1,1,1,0};
            colorBackground[] = {1,1,1,0.01};
            colorBackgroundDisabled[] = {1,1,1,0};
            colorBackgroundActive[] = {1,1,1,0.01};
            colorFocused[] = {1,1,1,0.01};
            colorBorder[] = {0,0,0,0};
            x = "safeZoneX + (safeZoneW / 2) - (safeZoneW / 18)";
            y = "safeZoneY + (safeZoneH / 2) - (safeZoneH / 2.95)";
            w = "safeZoneW / 9";
            h = "safeZoneH / 1.55";
            shadow = 0;
            font = "RobotoCondensed";
            sizeEx = "0";
            action = "";
            tooltip = "Click the wheel to grab it (click again to release), or press and hold to drag. Scroll for fine adjustment.";
        };
        class ACME_Title: RscText {
            idc = 86205;
            text = "Roller Clamp";
            x = "safeZoneX + (safeZoneW / 2) - (safeZoneW / 6.6)";
            y = "safeZoneY + (safeZoneH / 2) - (safeZoneH / 2.75)";
            w = "safeZoneW / 3.3";
            h = "safeZoneH / 24";
            colorText[] = {1,1,1,1};
            colorBackground[] = {0,0,0,0};
            font = "RobotoCondensed";
            sizeEx = "safeZoneH / 34";
            style = 2;
            shadow = 0;
        };
        class ACME_RateText: ACME_Title {
            idc = 86206;
            text = "20 gtt/mL | 60 gtt/min | 3 mL/min";
            x = "safeZoneX + (safeZoneW / 2) - (safeZoneW / 4.65)";
            y = "safeZoneY + (safeZoneH / 2) + (safeZoneH / 3.38)";
            w = "safeZoneW / 2.33";
            h = "safeZoneH / 19";
            sizeEx = "safeZoneH / 76";
            colorBackground[] = {0,0,0,0.65};
            style = 2;
        };
        class ACME_DropSet: RscButton {
            idc = 86207;
            text = "Drop Set: 20";
            x = "safeZoneX + (safeZoneW / 2) - (safeZoneW / 6.3)";
            y = "safeZoneY + (safeZoneH / 2) + (safeZoneH / 2.85)";
            w = "safeZoneW / 10.5";
            h = "safeZoneH / 26";
            colorText[] = {1,1,1,1};
            colorDisabled[] = {1,1,1,0.25};
            colorBackground[] = {0,0,0,1};
            colorBackgroundDisabled[] = {0,0,0,0.35};
            colorBackgroundActive[] = {0.12,0.12,0.12,1};
            colorFocused[] = {0,0,0,1};
            colorBorder[] = {0,0,0,0};
            style = 2;
            shadow = 0;
            font = "RobotoCondensed";
            sizeEx = "safeZoneH / 50";
            action = "call ACME_fnc_cycleDropSet";
            tooltip = "Cycle drop set: 10, 15, 20, or 60 gtt/mL";
        };
        class ACME_ToggleClamp: ACME_DropSet {
            idc = 86208;
            text = "Clamp Closed";
            x = "safeZoneX + (safeZoneW / 2) - (safeZoneW / 21)";
            action = "call ACME_fnc_toggleClamp";
            tooltip = "Fully close or reopen the roller clamp";
        };
        class ACME_Close: ACME_DropSet {
            idc = 86209;
            text = "Done";
            x = "safeZoneX + (safeZoneW / 2) + (safeZoneW / 15.3)";
            action = "call ACME_fnc_closeClamp";
            tooltip = "Close roller clamp controls";
        };
    };
};

// left-side list styling for the syringe-draw injection. it matches ACM's medication list on the right.
class ACME_SK_RowGroup: RscControlsGroupNoHScrollbars {};
// Separate vial-count field: right-aligned text inside a padded row rectangle.
class ACME_SK_RightText: RscText {
    style = 1;
};

class ACME_SK_StyledList: RscListBox {
    rowHeight = "safeZoneH / 20";
    colorText[] = {1,1,1,1};
    colorSelect[] = {0,0,0,1};
    colorSelect2[] = {0,0,0,1};
    colorBackground[] = {0,0,0,0.1};
    colorSelectBackground[] = {0.7,0.7,0.7,1};
    colorSelectBackground2[] = {0.7,0.7,0.7,1};
    sizeEx = "(safeZoneH / 20) * 0.5";
};
// B71 dedicated syringe-tag menu: dark medication-list-style panel with tighter rows so every
// full clinical-purpose label fits in one long dropdown without clipping.
class ACME_SK_TagList: ACME_SK_StyledList {
    rowHeight = "safeZoneH / 27";
    colorBackground[] = {0.04,0.04,0.04,0.96};
    colorSelectBackground[] = {0.38,0.38,0.38,1};
    colorSelectBackground2[] = {0.38,0.38,0.38,1};
    sizeEx = "(safeZoneH / 27) * 0.58";
};
class ACME_SK_NameEdit: RscEdit {
    style = 0;
    maxChars = 25;
    colorText[] = {1,1,1,1};
    colorSelection[] = {0.7,0.7,0.7,1};
    colorBackground[] = {0.02,0.02,0.02,0.85};
    font = "RobotoCondensed";
    sizeEx = "safeZoneH / 44";
    autocomplete = "";
};
// Explicit native edit semantics for the medication push duration.
class ACME_SK_PushDurationEdit: ACME_SK_NameEdit {
    type = 2;
    style = 0;
    canModify = 1;
    maxChars = 3;
    text = "";
};
class ACME_SK_TagEdit: RscEdit {
    // B64: ST_NO_RECT preserves a clickable caret/text surface but suppresses the default black RscEdit frame.
    style = 0x200;
    colorBackground[] = {0,0,0,0};
    colorText[] = {0.08,0.08,0.08,1};
    colorSelection[] = {0.3,0.5,0.8,0.10};
    colorDisabled[] = {0.08,0.08,0.08,0.6};
    colorBorder[] = {0,0,0,0};
    borderSize = 0;
    font = "ACME_QEDaveMergens";
    sizeEx = "safeZoneH / 58";
    shadow = 0;
    forceDrawCaret = 0;
    maxChars = 25;
};
class ACME_SK_TagText: RscText {
    colorBackground[] = {0,0,0,0};
    colorText[] = {0.08,0.08,0.08,1};
    font = "ACME_QEDaveMergens";
    shadow = 0;
    style = 0;
};

class ACME_SK_StyledLabel: RscText {
    colorText[] = {1,1,1,1};
    colorBackground[] = {0,0,0,0.35};
    style = 2;
    font = "RobotoCondensed";
    sizeEx = "safeZoneH / 40";
};
// narc box body-picker buttons, the view toggle and the route toggle. they are plain dark styled buttons.
// RscButton is already forward-declared earlier with the other base controls, so there is no re-declaration
// here.
class ACME_SK_StyledButton: RscButton {
    colorBackground[] = {0.05,0.05,0.05,0.65};
    colorBackgroundActive[] = {0.28,0.28,0.28,0.90};
    colorBackgroundDisabled[] = {0,0,0,0.30};
    colorFocused[] = {0.05,0.05,0.05,0.65};
    colorText[] = {1,1,1,1};
    colorDisabled[] = {1,1,1,0.30};
    font = "RobotoCondensed";
    sizeEx = "safeZoneH / 44";
    borderSize = 0;
};
// transparent button used for the view toggle. every background state is clear, so only the label renders. it
// sits over a separate pulsing RscText backing, because the pulse cannot live on the button itself. the
// focused and active colors of a button are static config that the runtime ctrlSetBackgroundColor cannot
// reach, so the pulse froze the instant a player clicked or hovered the button.
class ACME_SK_PulseButton: ACME_SK_StyledButton {
    colorBackground[] = {0,0,0,0};
    colorBackgroundActive[] = {0,0,0,0};
    colorBackgroundDisabled[] = {0,0,0,0};
    colorFocused[] = {0,0,0,0};
};
// Transfusion page navigation uses the exact same transparent button-over-pulsing-backing construction as
// Narc Box / Body Map. Runtime owns the blue pulse, so hover/focus/press can never replace it with a darker
// RscButton state.
class ACME_TX_PageButton: ACME_SK_PulseButton {
    colorText[] = {0.94,0.91,0.82,1};
    colorDisabled[] = {0.94,0.91,0.82,0.45};
    font = "RobotoCondensed";
    sizeEx = "safeZoneH / 46";
    shadow = 0;
};
// injection hotspots over the body image. each is a faint blue clickable zone that brightens on hover.
// they are invisible by default. this used to paint a solid 50 percent blue rectangle over every site, which
// is the giant blue box: a hit-test region drawn as though it were the artwork. the site itself is shown by
// its overlay texture, which is real anatomy, and the button only has to catch the click.
// The input stays transparent. fn_skBuildHotspots changes the artwork opacity on hover.
class ACME_SK_RowButton: ACME_SK_PulseButton {
    style = 0;
    sizeEx = "safeZoneH / 44";
    colorShadow[] = {0,0,0,0};
    offsetX = 0;
    offsetY = 0;
    offsetPressedX = 0;
    offsetPressedY = 0;
};
class ACME_SK_HotspotButton: ACME_SK_StyledButton {
    colorBackground[] = {0,0,0,0};
    colorBackgroundActive[] = {0,0,0,0};
    colorBackgroundDisabled[] = {0,0,0,0};
    colorFocused[] = {0,0,0,0};
    colorText[] = {0,0,0,0};
    sizeEx = "safeZoneH / 52";
};

// custom syringe kit bench, idd 86300, inlined from the former ui/items/syringekit_dialog.hpp. the build has no
// #include to drop. the controls are given placeholder geometry here and fully positioned in
// ACME_fnc_syringeKitOnLoad, through safezone math, which mirrors the roller-clamp dialog.
// chest-seal mini-game, idd 86400. hold lmb to rake four visible fingertip indicators over the chest, and
// their color shifts as they approach an occult hole. click the cric-style tray icon to pick up or return a
// chest seal. while held, the seal follows the cursor and a body click places it. the NAR SPEAR tray beneath
// it uses the same pickup and return behavior, and guides the needle to the patient-side fifth intercostal
// space. a flip checks the opposite side without a close of the procedure. the logic is in acme_fnc_chestseal*.
class RscStructuredText;
class ACME_ChestSeal_Dialog {
    idd = 86400;
    movingEnable = 0;
    onLoad = "[_this select 0] call ACME_fnc_minigameInputInstall; _this call ACME_fnc_chestSealInit";
    onUnload = "_this call ACME_fnc_chestSealClose";
    class ControlsBackground {
        class CS_Dim: RscText {
            idc = -1;
            x = "safezoneX"; y = "safezoneY"; w = "safezoneW"; h = "safezoneH";
            text = ""; colorBackground[] = {0, 0, 0, 0.55};
        };
        class CS_Body: RscPicture {
            idc = 86401;
            x = "safezoneX + safezoneW * 0.36";
            y = "safezoneY + safezoneH * 0.10";
            w = "safezoneW * 0.28";
            h = "safezoneH * 0.80";
            text = "\x\acm\addons\gui\ui\body_background.paa";
        };
    };
    class Controls {
        class CS_Title: RscText {
            idc = -1;
            style = 2;
            x = "safezoneX"; y = "safezoneY + safezoneH * 0.035"; w = "safezoneW"; h = "safezoneH * 0.05";
            text = "";
            colorText[] = {0.93, 0.89, 0.80, 1};
            colorBackground[] = {0, 0, 0, 0};
            sizeEx = "0.042 * safezoneH";
        };
        class CS_Instruction: CS_Title {
            idc = 86403;
            y = "safezoneY + safezoneH * 0.09"; h = "safezoneH * 0.04";
            text = "";
            sizeEx = "0.026 * safezoneH";
            colorText[] = {0.82, 0.82, 0.82, 1};
        };
        // valid placement area, below the neckline and inside the pectoral box. it shows faintly as a guide and the
        // script gates it against acme_cs_chestzone, a screen-fraction rect. it is repositioned at init.
        class CS_Zone: RscPicture {
            idc = 86404;
            x = 0; y = 0; w = 0; h = 0;
            // shaped translucent guide overlay, traced to the body for the front torso and the back thorax. it is
            // positioned to the full body rect at init, and fn_chestsealrender swaps the texture per side.
            text = "\acm_extended\ui\cs_zone_front_ca.paa";
            colorText[] = {1, 1, 1, 1};
        };
        // transparent interaction surface over the body. it is a controls-group rather than a static, so it receives
        // mouse events. its MouseMoving and MouseHolding handlers report the cursor in dialog ui coordinates exactly
        // as the engine computes them for hit-testing. that is the one source that is correct under ultrawide
        // non-stretch, where no fixed safezone formula can map getMousePosition to control space. it is positioned to
        // the full body rect at init, and defined after CS_Zone so it sits above the guide overlay and still catches
        // moves over the blue area.
        class CS_Surface: RscControlsGroupNoScrollbars {
            idc = 86410;
            x = 0; y = 0; w = 0; h = 0;
            colorBackground[] = {0, 0, 0, 0};
            class Controls {};
        };
        // tool slot, in the cric pattern: a black box, the chest-seal logo, a count and a transparent click button.
        class CS_SlotBG: RscText {
            idc = 86420;
            x = "safezoneX + safezoneW * 0.80"; y = "safezoneY + safezoneH * 0.40";
            w = "safezoneW * 0.10"; h = "safezoneH * 0.18";
            text = "";
            colorBackground[] = {0, 0, 0, 0.85};
        };
        class CS_SlotLogo: RscPicture {
            idc = 86422;
            x = "safezoneX + safezoneW * 0.806"; y = "safezoneY + safezoneH * 0.41";
            w = "safezoneW * 0.088"; h = "safezoneH * 0.14";
            text = "\x\acm\addons\breathing\ui\chestseal_ca.paa";
        };
        class CS_SlotCount: RscText {
            idc = 86423;
            x = "safezoneX + safezoneW * 0.80"; y = "safezoneY + safezoneH * 0.555";
            w = "safezoneW * 0.10"; h = "safezoneH * 0.03";
            style = 2;
            text = "";
            colorText[] = {0.93, 0.89, 0.80, 1};
            colorBackground[] = {0, 0, 0, 0};
            sizeEx = "0.024 * safezoneH";
        };
        // transparent click surface over the tray. this mirrors ACM's cric tool pickup, so the icon itself is a
        // reliable button rather than depending on display-wide hit testing.
        class CS_SlotClick: RscButton {
            idc = 86424;
            x = "safezoneX + safezoneW * 0.80"; y = "safezoneY + safezoneH * 0.40";
            w = "safezoneW * 0.10"; h = "safezoneH * 0.18";
            text = "";
            tooltip = "Pick up / return chest seal";
            onButtonClick = "[] call ACME_fnc_chestSealToggleHeld";
            colorText[] = {0,0,0,0};
            colorDisabled[] = {0,0,0,0};
            colorBackground[] = {0,0,0,0};
            colorBackgroundDisabled[] = {0,0,0,0};
            colorBackgroundActive[] = {1,1,1,0.04};
            colorFocused[] = {0,0,0,0};
            colorShadow[] = {0,0,0,0};
            colorBorder[] = {0,0,0,0};
            borderSize = 0;
        };

        // NAR SPEAR tray. it uses the same pickup and return interaction as the chest-seal tool above.
        class CS_SpearSlotBG: RscText {
            idc = 86430;
            x = 0; y = 0; w = 0; h = 0;
            text = "";
            colorBackground[] = {0, 0, 0, 0.85};
        };
        class CS_SpearSlotLogo: RscPicture {
            idc = 86432;
            x = 0; y = 0; w = 0; h = 0;
            text = "\acm_extended\ui\items\nar_spear_ca.paa";
        };
        class CS_SpearSlotCount: RscText {
            idc = 86433;
            x = 0; y = 0; w = 0; h = 0;
            style = 2;
            text = "";
            colorText[] = {0.93, 0.89, 0.80, 1};
            colorBackground[] = {0, 0, 0, 0};
            sizeEx = "0.024 * safezoneH";
        };
        class CS_SpearSlotClick: RscButton {
            idc = 86434;
            x = 0; y = 0; w = 0; h = 0;
            text = "";
            tooltip = "Pick up / return NAR SPEAR";
            onButtonClick = "[] call ACME_fnc_chestSealToggleSpear";
            colorText[] = {0,0,0,0};
            colorDisabled[] = {0,0,0,0};
            colorBackground[] = {0,0,0,0};
            colorBackgroundDisabled[] = {0,0,0,0};
            colorBackgroundActive[] = {1,1,1,0.04};
            colorFocused[] = {0,0,0,0};
            colorShadow[] = {0,0,0,0};
            colorBorder[] = {0,0,0,0};
            borderSize = 0;
        };
        // flip between the front and back of the body, to find and seal entry against exit wounds.
        class CS_Flip: RscButton {
            idc = 86426;
            x = "safezoneX + safezoneW * 0.80"; y = "safezoneY + safezoneH * 0.70";
            w = "safezoneW * 0.10"; h = "safezoneH * 0.055";
            text = "Flip";
            tooltip = "Turn the body over (front / back)";
            onButtonClick = "[] call ACME_fnc_chestSealFlip";
            colorBackground[] = {0.14, 0.20, 0.30, 0.90};
            colorText[] = {0.93, 0.89, 0.80, 1};
        };
        // this was the rake and feel mode toggle. the hands moved onto the mouse buttons, where lmb rakes and RMB is
        // the feeler, so the toggle is gone. because RMB no longer closes the dialog, this slot becomes the explicit
        // close.
        class CS_Close: RscButton {
            idc = 86427;
            text = "Close";
            onButtonClick = "[86400] call ACME_fnc_minigameClose;";
            colorBackground[] = {0.13, 0.22, 0.17, 0.90};
            colorText[] = {0.93, 0.89, 0.80, 1};
        };
        class CS_Cancel: RscButton {
            idc = 86425;
            x = "safezoneX + safezoneW * 0.80"; y = "safezoneY + safezoneH * 0.82";
            w = "safezoneW * 0.10"; h = "safezoneH * 0.05";
            text = "Done";
            action = "[86400] call ACME_fnc_minigameClose;";
            colorBackground[] = {0.30, 0.10, 0.10, 0.85};
            colorText[] = {0.93, 0.89, 0.80, 1};
        };
    };
};

// placed chest-seal mark. ctrlcreate makes one at each successful placement, which mirrors ACM's runtime
// incision visuals.
class ACME_CS_PlacedSeal: RscPicture {
    idc = -1;
    x = 0; y = 0; w = 0; h = 0;
    text = "\x\acm\addons\breathing\ui\chestseal_ca.paa";
    colorText[] = {1,1,1,0.95};
    show = 1;
};
// four fingertip circles that follow the cursor in an arch while a medic rakes. the runtime sets the color by
// wound proximity.
class ACME_CS_Dot: RscPicture {
    idc = -1;
    x = 0; y = 0; w = 0; h = 0;
    text = "\acm_extended\ui\dot_grad_ca.paa";
    colorText[] = {0.95, 0.95, 0.98, 0.85};
    show = 0;
};
// found-hole mark. it is one of the random hole_ca icons, ctrlcreate'd when a hole is revealed, and the runtime
// sets the texture.
class ACME_CS_Hole: RscPicture {
    idc = -1;
    x = 0; y = 0; w = 0; h = 0;
    text = "\acm_extended\ui\holes\hole1_ca.paa";
    colorText[] = {1,1,1,1};
    show = 1;
};

// full-canvas NAR SPEAR sprite. the supplied textures are authored against the body image, so the runtime
// controls use the same full-body rectangle and center on the cursor while a medic holds the needle.
class ACME_CS_NCDSprite: RscPicture {
    idc = -1;
    x = 0; y = 0; w = 0; h = 0;
    text = "\acm_extended\ui\items\nar_spear_left_ca.paa";
    colorText[] = {1,1,1,1};
    show = 1;
};

// thoracostomy mini-game, palpation. idd 86600.
// it uses the same interaction model as the chest seal: a dim, a side body image, a red 5th-ics zone overlay,
// and a transparent controls-group surface that reports the cursor in true ui coords. it is ultrawide-safe and
// reuses the chest-seal coord resolver. this wires palpation only, where a feel-dot becomes a red triangle and
// a click on green locks the site. the later work adds the drawicon map layer for the incision, the kelly
// clamp, the finger sweep and the tube.
class RscMapControl;
class ACME_Thora_DrawMap: RscMapControl {
    // a blank, non-interactive map, used purely as a rotatable drawicon canvas. every terrain color is zeroed, so
    // nothing but our drawicon calls is visible.
    colorBackground[] = {0, 0, 0, 0};
    colorSea[] = {0, 0, 0, 0};
    colorForest[] = {0, 0, 0, 0};
    colorForestBorder[] = {0, 0, 0, 0};
    colorRocks[] = {0, 0, 0, 0};
    colorRocksBorder[] = {0, 0, 0, 0};
    colorCountlines[] = {0, 0, 0, 0};
    colorMainCountlines[] = {0, 0, 0, 0};
    colorCountlinesWater[] = {0, 0, 0, 0};
    colorMainCountlinesWater[] = {0, 0, 0, 0};
    colorLinesWater[] = {0, 0, 0, 0};
    colorLinesRailway[] = {0, 0, 0, 0};
    colorLinesRoad[] = {0, 0, 0, 0};
    colorLinesMainRoad[] = {0, 0, 0, 0};
    colorLinesTrack[] = {0, 0, 0, 0};
    colorLinesTrail[] = {0, 0, 0, 0};
    colorGrid[] = {0, 0, 0, 0};
    colorGridMap[] = {0, 0, 0, 0};
    colorTracks[] = {0, 0, 0, 0};
    colorTracksFill[] = {0, 0, 0, 0};
    colorInactive[] = {0, 0, 0, 0};
    colorOutside[] = {0, 0, 0, 0};
    colorText[] = {0, 0, 0, 0};
    fontLabel = "PuristaMedium";
    sizeExGrid = 0;
    sizeExUnits = 0;
    sizeExNames = 0;
    sizeExInfo = 0;
    sizeExTownNames = 0;
    text = "";
    stickX[] = {0, 0};
    stickY[] = {0, 0};
    ptsPerSquareSea = 0.001;
    ptsPerSquareTxt = 0.001;
    ptsPerSquareCLn = 0.001;
    ptsPerSquareExp = 0.001;
    ptsPerSquareCost = 0.001;
    ptsPerSquareForEdge = 0.001;
    ptsPerSquareRoad = 0.001;
    ptsPerSquareObj = 0.001;
    showCountourInterval = 0;
    scaleMin = 0.001;
    scaleMax = 100000;
    scaleDefault = 0.1;
};
class ACME_Thora_SlotBtn: RscButton {
    colorText[] = {0, 0, 0, 0};
    colorDisabled[] = {0, 0, 0, 0};
    colorBackground[] = {0, 0, 0, 0};
    colorBackgroundDisabled[] = {0, 0, 0, 0};
    colorBackgroundActive[] = {0, 0, 0, 0};
    colorFocused[] = {0, 0, 0, 0};
    colorShadow[] = {0, 0, 0, 0};
    colorBorder[] = {0, 0, 0, 0};
    soundEnter[] = {"", 0, 1};
    soundPush[] = {"", 0, 1};
    soundClick[] = {"", 0, 1};
    soundEscape[] = {"", 0, 1};
};
class ACME_Thoracostomy_Dialog {
    idd = 86600;
    movingEnable = 0;
    onLoad = "[_this select 0] call ACME_fnc_minigameInputInstall; _this call ACME_fnc_thoraInit";
    onUnload = "[] call ACME_fnc_thoraClose";
    class ControlsBackground {
        class Thora_Dim: RscText {
            idc = -1;
            x = "safezoneX"; y = "safezoneY"; w = "safezoneW"; h = "safezoneH";
            text = ""; colorBackground[] = {0, 0, 0, 0.55};
        };
        class Thora_Body: RscPicture {
            idc = 86601;
            x = 0; y = 0; w = 0; h = 0;
            text = "\acm_extended\ui\chest_right_ca.paa";
            colorText[] = {1, 1, 1, 1};
        };
    };
    class Controls {
        class Thora_Zone: RscText {
            idc = 86604;
            x = 0; y = 0; w = 0; h = 0;
            text = "";
            colorBackground[] = {0.85, 0.12, 0.12, 0.35};
        };
        class Thora_Surface: RscControlsGroupNoScrollbars {
            idc = 86610;
            x = 0; y = 0; w = 0; h = 0;
            colorBackground[] = {0, 0, 0, 0};
            class Controls {};
        };
        class Thora_Flip: RscButton {
            idc = 86626;
            x = 0; y = 0; w = 0; h = 0;
            text = "Flip side";
            tooltip = "Switch between the right and left chest";
            onButtonClick = "[] call ACME_fnc_thoraFlip";
            colorText[] = {0.93, 0.89, 0.80, 1};
            colorBackground[] = {0, 0, 0, 0.85};
            colorBackgroundActive[] = {1, 1, 1, 0.06};
            sizeEx = "0.026 * safezoneH";
        };
        class Thora_Close: RscButton {
            idc = -1;
            x = "safezoneX + safezoneW * 0.44"; y = "safezoneY + safezoneH * 0.92";
            w = "safezoneW * 0.12"; h = "safezoneH * 0.05";
            text = "Done";
            // this must go through fn_minigameclose and not closedialog. in display mode, see fn_minigameopen, this panel
            // is not a dialog, so [86600] call ACME_fnc_minigameClose does nothing. this button is the only way out of a
            // thoracostomy and would stop working silently. an unclosable panel ends a session.
            onButtonClick = "[86600] call ACME_fnc_minigameClose;";
            colorText[] = {0.93, 0.89, 0.80, 1};
            colorBackground[] = {0, 0, 0, 0.85};
            colorBackgroundActive[] = {1, 1, 1, 0.06};
            sizeEx = "0.028 * safezoneH";
        };
    };
};

// iv placement mini-game, idd 86500.
// this is a single-finger feel-for-the-vein placement, built on the chest-seal interaction model. it has a limb
// silhouette, front or rear per site, the NAR BOA constricting band overlaid at the stick site, a transparent
// mouse-catching surface that reports the cursor in true ui coords and is ultrawide-safe, and a feel dot that
// tracks the fingertip. fn_ivminigameinit positions all the controls at runtime, and the limb and band
// textures swap per selected site.
class ACME_IVMinigame_Dialog {
    idd = 86500;
    movingEnable = 0;
    onLoad = "[_this select 0] call ACME_fnc_minigameInputInstall; _this call ACME_fnc_ivMinigameInit";
    onUnload = "_this call ACME_fnc_ivMinigameClose";
    class ControlsBackground {
        class IV_Dim: RscText {
            idc = -1;
            x = "safezoneX"; y = "safezoneY"; w = "safezoneW"; h = "safezoneH";
            text = ""; colorBackground[] = {0, 0, 0, 0.62};
        };
        // limb silhouette, front or rear. the texture and rect are set at init.
        class IV_Limb: RscPictureKeepAspect {
            idc = 86501;
            x = 0; y = 0; w = 0; h = 0;
            text = "\acm_extended\ui\iv\iv_left_arm_ca.paa";
            colorText[] = {1, 1, 1, 1};
        };
        // Prep redness stays beneath the band and every placed/removed-IV mark.
        class IV_PrepLayer: RscControlsGroupNoScrollbars {
            idc = 86508;
            x = "safezoneX"; y = "safezoneY"; w = "safezoneW"; h = "safezoneH";
            class Controls {};
        };
        // the item that follows the cursor while picked up. it shows the actual band, needle or catheter art. the
        // cursor-following item sprites, IV_CursorBand, needle and pad, are defined at the end of this controls block,
        // so they render on top of the buttons while carried.
        // the NAR BOA constricting band is baked at the band site in the art and transparent elsewhere. it shares the
        // limb rect so it aligns. it stays hidden until the medic applies it, then shows.
        class IV_Band: RscPictureKeepAspect {
            idc = 86502;
            x = 0; y = 0; w = 0; h = 0;
            text = "\acm_extended\ui\iv\iv_boa_left_arm_lower_ca.paa";
            colorText[] = {1, 1, 1, 1};
            show = 0;
        };
    };
    class Controls {
        class IV_Title: RscText {
            idc = -1;
            style = 2;
            x = "safezoneX"; y = "safezoneY + safezoneH * 0.035"; w = "safezoneW"; h = "safezoneH * 0.05";
            text = "";
            colorText[] = {0.93, 0.89, 0.80, 1};
            colorBackground[] = {0, 0, 0, 0};
            sizeEx = "0.042 * safezoneH";
        };
        // the site caption. ACME_IV_Label has been computed since the minigame was written and rendered by
        // nothing: fn_ivMinigameInit, fn_ivMinigameClick and fn_ivMinigameRestoreState all wrote it, and
        // fn_ivMinigameSaveState persisted it, but no control ever read it. it is now derived from
        // ACME_fnc_ivVeinCatalog rather than from a hardcoded literal per row, so it is finally worth showing.
        // it is a SEPARATE class rather than an idc on IV_Title, because IV_Instruction and IV_SlotHdr both
        // inherit from IV_Title and giving the base an idc would hand the same one to any child that did not
        // override it.
        // 86503 was the obvious candidate and is wrong: that is the step prompt, rewritten constantly by
        // fn_ivMinigameGrabLine and fifteen other places, so a caption there would be wiped within a frame.
        // it inherits IV_Title's position and size unchanged. that slot spans 0.035 to 0.085 of safezone
        // height, IV_Title carries text = "" and idc = -1 so nothing has ever drawn in it, and the instruction
        // line sits below at 0.09. no overlap.
        class IV_SiteHdr: IV_Title {
            idc = 86504;
            text = "";
            sizeEx = "0.030 * safezoneH";
            colorText[] = {0.55, 0.85, 1, 1};
        };
        class IV_Instruction: IV_Title {
            idc = 86503;
            y = "safezoneY + safezoneH * 0.09"; h = "safezoneH * 0.04";
            text = "";
            sizeEx = "0.026 * safezoneH";
            colorText[] = {0.82, 0.82, 0.82, 1};
        };
        // transparent interaction surface over the limb. it receives mouse-move events to report true ui coords. the
        // clicks route through a display-level MouseButtonDown handler, like the chest seal, so one robust hit-test
        // resolves the side slot buttons and the limb.
        class IV_Surface: RscControlsGroupNoScrollbars {
            idc = 86510;
            x = 0; y = 0; w = 0; h = 0;
            colorBackground[] = {0, 0, 0, 0};
            class Controls {};
        };

        // compact slot column, all on the right: BAND on top, then the 14, 16 and 18 g needles. every box is small. the
        // transparent click buttons sit on top of each box, and the display handler also hit-tests their rects as a
        // fallback.
        class IV_SlotHdr: IV_Title {
            idc = -1;
            style = 0;
            x = "safezoneX + safezoneW * 0.880"; y = "safezoneY + safezoneH * 0.135";
            w = "safezoneW * 0.10"; h = "safezoneH * 0.03";
            text = "";
            sizeEx = "0.020 * safezoneH";
            colorText[] = {0.55, 0.85, 1, 1};
        };
        class IV_BandSlotBG: RscText {
            idc = 86530; x = 0; y = 0; w = 0; h = 0; text = "";
            colorBackground[] = {0.10, 0.13, 0.17, 0.92};
        };
        class IV_BandSlotLogo: RscPictureKeepAspect {
            idc = 86531; x = 0; y = 0; w = 0; h = 0;
            text = "\acm_extended\ui\nar_boa_ca.paa";
            colorText[] = {1, 1, 1, 1};
        };
        class IV_BandSlotClick: RscButton {
            idc = 86532; x = 0; y = 0; w = 0; h = 0; text = ""; colorText[] = {0,0,0,0};
            colorBackground[] = {0,0,0,0}; colorBackgroundActive[] = {0.3,0.5,0.7,0.30}; colorFocused[] = {0,0,0,0};
            colorBackgroundDisabled[] = {0,0,0,0};
            tooltip = "Pick up the constricting band. Move it over the limb and click to apply.";
            onButtonClick = "[] call ACME_fnc_ivMinigameGrabBand";
        };
        // alcohol pad slot. a medic uses it to clean the site after palpating.
        class IV_BandLbl: RscText {
            idc = 86533; x = 0; y = 0; w = 0; h = 0; style = 2;
            text = "BAND"; colorText[] = {0.95, 0.80, 0.80, 1}; colorBackground[] = {0,0,0,0};
            sizeEx = "0.018 * safezoneH"; font = "RobotoCondensed";
        };
        class IV_PadLbl: RscText {
            idc = 86538; x = 0; y = 0; w = 0; h = 0; style = 2;
            text = "PAD"; colorText[] = {0.80, 0.92, 1, 1}; colorBackground[] = {0,0,0,0};
            sizeEx = "0.018 * safezoneH"; font = "RobotoCondensed";
        };
        class IV_PadBG: RscText {
            idc = 86535; x = 0; y = 0; w = 0; h = 0; text = "";
            colorBackground[] = {0.10, 0.13, 0.17, 0.92};
        };
        class IV_PadLogo: RscPictureKeepAspect {
            idc = 86536; x = 0; y = 0; w = 0; h = 0;
            text = "\acm_extended\ui\iv\alcohol_pad_left_ca.paa";
            colorText[] = {1, 1, 1, 1};
        };
        class IV_PadClick: RscButton {
            idc = 86537; x = 0; y = 0; w = 0; h = 0; text = ""; colorText[] = {0,0,0,0};
            colorBackground[] = {0,0,0,0}; colorBackgroundActive[] = {0.3,0.5,0.7,0.30}; colorFocused[] = {0,0,0,0};
            colorBackgroundDisabled[] = {0,0,0,0};
            tooltip = "Alcohol pad. Hold and wipe the site at least three times.";
            onButtonClick = "[] call ACME_fnc_ivMinigameGrabPad";
        };
        class IV_NeedleHdr: IV_SlotHdr {
            idc = 86539;
            text = "NEEDLE";
            colorText[] = {0.55, 0.85, 1, 1};
        };
        class IV_G14BG: RscText {
            idc = 86540; x = 0; y = 0; w = 0; h = 0; text = "";
            colorBackground[] = {0.10, 0.13, 0.17, 0.92};
        };
        class IV_G14Logo: RscPictureKeepAspect {
            idc = 86541; x = 0; y = 0; w = 0; h = 0;
            text = "\acm_extended\ui\iv\14g\base\iv_catheter_14g_base_frame_00_ready_ca.paa";
            colorText[] = {1, 0.55, 0.55, 1};
        };
        class IV_G14Lbl: RscText {
            idc = 86542; x = 0; y = 0; w = 0; h = 0; style = 2;
            text = "14g"; colorText[] = {0.95, 0.75, 0.75, 1}; colorBackground[] = {0,0,0,0};
            sizeEx = "0.018 * safezoneH"; font = "RobotoCondensed";
        };
        class IV_G14Click: RscButton {
            idc = 86543; x = 0; y = 0; w = 0; h = 0; text = ""; colorText[] = {0,0,0,0};
            colorBackground[] = {0,0,0,0}; colorBackgroundActive[] = {0.3,0.5,0.7,0.30}; colorFocused[] = {0,0,0,0};
            colorBackgroundDisabled[] = {0,0,0,0};
            // NO TOOLTIP ON THE NEEDLE SLOTS. the label under each box already says the gauge and the count, and
            // a hover box on top of the tray covered the limb while the medic was reaching for a catheter.
            // the band, pad and line slots keep theirs: those are not self-explanatory from a label.
            // the three smaller gauges inherit this class, so blanking it here blanks all four.
            tooltip = "";
            onButtonClick = "[14] call ACME_fnc_ivMinigameGrabNeedle";
        };
        class IV_G16BG: IV_G14BG { idc = 86544; };
        class IV_G16Logo: IV_G14Logo { idc = 86545; colorText[] = {1, 1, 1, 1}; text = "\acm_extended\ui\iv\16g\base\iv_catheter_16g_base_frame_00_ready_ca.paa"; };
        class IV_G16Lbl: IV_G14Lbl { idc = 86546; text = "16g"; colorText[] = {0.90, 0.95, 1, 1}; };
        class IV_G16Click: IV_G14Click { idc = 86547; onButtonClick = "[16] call ACME_fnc_ivMinigameGrabNeedle"; };
        class IV_G18BG: IV_G14BG { idc = 86548; };
        class IV_G18Logo: IV_G14Logo { idc = 86549; colorText[] = {0.70, 0.90, 1, 1}; text = "\acm_extended\ui\iv\18g\base\iv_catheter_18g_base_frame_00_ready_ca.paa"; };
        class IV_G18Lbl: IV_G14Lbl { idc = 86550; text = "18g"; colorText[] = {0.75, 0.90, 1, 1}; };
        class IV_G18Click: IV_G14Click { idc = 86551; onButtonClick = "[18] call ACME_fnc_ivMinigameGrabNeedle"; };
        // the 20g slot. idcs 86556 to 86559 were the only free block below IV_Flip at 86560.
        // the geometry is set in fn_ivMinigameInit from the _gauges table, like the other three, so the zeros here
        // are correct and must stay.
        class IV_G20BG: IV_G14BG { idc = 86556; };
        class IV_G20Logo: IV_G14Logo { idc = 86557; colorText[] = {0.60, 0.85, 1, 1}; text = "\acm_extended\ui\iv\20g\base\iv_catheter_20g_base_frame_00_ready_ca.paa"; };
        class IV_G20Lbl: IV_G14Lbl { idc = 86558; text = "20g"; colorText[] = {0.70, 0.88, 1, 1}; };
        class IV_G20Click: IV_G14Click { idc = 86559; onButtonClick = "[20] call ACME_fnc_ivMinigameGrabNeedle"; };

        // the saline line slot. it takes the tubing to a seated hub, so it is only useful once a catheter is in.
        // it holds no count, in the same way the pad does, because the line comes with the catheter.
        class IV_LineBG: IV_G14BG { idc = 86552; };
        class IV_LineLogo: IV_G14Logo {
            idc = 86553;
            text = "\acm_extended\ui\iv\iv_line\standalone\base\iv_line_floating_base_ca.paa";
            colorText[] = {0.80, 0.95, 1, 1};
        };
        class IV_LineLbl: IV_G14Lbl { idc = 86554; text = "LINE"; colorText[] = {0.80, 0.95, 1, 1}; };
        class IV_LineClick: IV_G14Click { idc = 86555; tooltip = "Saline line. Connect it to a seated hub"; onButtonClick = "[] call ACME_fnc_ivMinigameGrabLine"; };

        // flip the limb between the front and rear views, so the basilic and popliteal sites, which live on the rear,
        // are reachable. it sits bottom-left, clear of the right-side slot column.
        class IV_Flip: RscButton {
            idc = 86560;
            x = "safezoneX + safezoneW * 0.025"; y = "safezoneY + safezoneH * 0.84";
            w = "safezoneW * 0.12"; h = "safezoneH * 0.05";
            text = "Flip (Front/Back)";
            onButtonClick = "[] call ACME_fnc_ivMinigameFlip";
            colorBackground[] = {0.14, 0.18, 0.24, 0.90};
            colorText[] = {0.85, 0.92, 1, 1};
        };
        // remove an existing iv. click this, then click a placed catheter hub to pull it.
        class IV_Cancel: RscButton {
            idc = 86525;
            x = "safezoneX + safezoneW * 0.025"; y = "safezoneY + safezoneH * 0.90";
            w = "safezoneW * 0.12"; h = "safezoneH * 0.05";
            text = "Done";
            action = "[] call ACME_fnc_ivMinigameDone";
            colorBackground[] = {0.30, 0.10, 0.10, 0.85};
            colorText[] = {0.93, 0.89, 0.80, 1};
        };
        // cursor-following item sprites. they are defined last, so the carried band, needle and pad render on top of
        // the buttons and everything else. they stay hidden unless something is held, and are positioned at the cursor
        // each tick.
        class IV_CursorBand: RscPictureKeepAspect {
            idc = 86505;
            x = 0; y = 0; w = 0; h = 0;
            text = "\acm_extended\ui\nar_boa_ca.paa";
            colorText[] = {1, 1, 1, 0.95};
            show = 0;
        };
        class IV_CursorNeedle: RscPictureKeepAspect {
            idc = 86506;
            x = 0; y = 0; w = 0; h = 0;
            text = "\acm_extended\ui\iv\18g\base\iv_catheter_18g_base_frame_00_ready_ca.paa";
            colorText[] = {1, 1, 1, 0.95};
            show = 0;
        };
        class IV_CursorPad: RscPictureKeepAspect {
            idc = 86507;
            x = 0; y = 0; w = 0; h = 0;
            text = "\acm_extended\ui\iv\alcohol_pad_left_ca.paa";
            colorText[] = {1, 1, 1, 0.95};
            show = 0;
        };
    };
};

// feel dot. ctrlcreate makes it over the limb, centerd on the fingertip while a medic feels.
class ACME_IV_Dot: RscPicture {
    idc = -1;
    x = 0; y = 0; w = 0; h = 0;
    text = "\acm_extended\ui\dot_grad_ca.paa";
    colorText[] = {0.95, 0.95, 0.98, 0.85};
};

// target pip. it is a faint marker shown at the vein site as a guide, a subtle debug and learning aid.
class ACME_IV_Target: RscPicture {
    idc = -1;
    x = 0; y = 0; w = 0; h = 0;
    text = "\acm_extended\ui\dot_grad_ca.paa";
    colorText[] = {0.40, 0.95, 0.55, 0.30};
};

// Catheter sprite at the vein. One square pixel canvas rotates about the insertion point;
// base, inserted and hub frames share the same pose across placement stages.
class ACME_IV_Catheter: RscPictureKeepAspect {
    style = 48; // Geometry supplies a square pixel canvas before rigid rotation.
    idc = -1;
    x = 0; y = 0; w = 0; h = 0;
    text = "\acm_extended\ui\iv\18g\base\iv_catheter_18g_base_frame_00_ready_ca.paa";
    colorText[] = {1, 1, 1, 1};
};

// antiseptic stain left after a medic wipes the site. it is a faint red that fades out across about 30 s.
class ACME_IV_Clean: RscPicture {
    idc = -1;
    x = 0; y = 0; w = 0; h = 0;
    text = "\acm_extended\ui\dot_grad_ca.paa";
    colorText[] = {0.85, 0.20, 0.20, 0.35};
};

// tiny hole left by a missed stick or a removed iv. it uses the same icons a missed NAR SPEAR uses, and the
// runtime sets the texture.
class ACME_IV_Hole: RscPicture {
    idc = -1;
    x = 0; y = 0; w = 0; h = 0;
    text = "\acm_extended\ui\holes\hole1_ca.paa";
    colorText[] = {1, 1, 1, 0.9};
};

// Persistent placed-IV marker. Retain the live catheter's insertion point and rotation across opens.
class ACME_IV_HubMark: RscPictureKeepAspect {
    style = 48;
    idc = -1;
    x = 0; y = 0; w = 0; h = 0;
    text = "\acm_extended\ui\iv\18g\base\iv_catheter_18g_base_frame_14_catheter_hub_only_ca.paa";
    colorText[] = {1, 1, 1, 1};
};

// persistent miss-site bruise. it is drawn under the puncture hole and correlates with the gauge. the runtime
// drives the alpha, which fades from 0 to 1 across 15 s from the miss. fn_ivminigamerendermarks sets the
// texture, the size and the position.
class ACME_IV_Bruise: RscPictureKeepAspect {
    idc = -1;
    x = 0; y = 0; w = 0; h = 0;
    text = "\acm_extended\ui\iv\bruise_16g_ca.paa";
    colorText[] = {1, 1, 1, 0};
};

// the item currently in hand, which follows the cursor. ctrlcreate makes it at runtime so it always draws on
// top of the static buttons and boxes, and the texture and position are set every tick.
class ACME_IV_HeldCursor: RscPictureKeepAspect {
    idc = -1;
    x = 0; y = 0; w = 0; h = 0;
    text = "\acm_extended\ui\nar_boa_ca.paa";
    colorText[] = {1, 1, 1, 1};
};
class ACME_IV_CathCursor: ACME_IV_HeldCursor {
    style = 48;
};

// procedural fills, #(argb,8,8,3)color(1,1,1,1) tinted through ctrlSetTextColor, draw the barrel, the fluid,
// the plunger and the rod. the lists and buttons are populated and wired at runtime.
class ACME_SyringeKit_Dialog {
    idd = 86300;
    movingEnable = 0;
    enableSimulation = 1;
    onLoad = "[_this select 0] call ACME_fnc_minigameInputInstall; call ACME_fnc_syringeKitOnLoad";

    onUnload = "private _h = uiNamespace getVariable ['ACME_SK_PFH', -1]; if (_h >= 0) then {[_h] call CBA_fnc_removePerFrameHandler;}; uiNamespace setVariable ['ACME_SK_PFH', -1]; uiNamespace setVariable ['ACME_SK_DLG', displayNull]; uiNamespace setVariable ['ACME_SK_InitDisplay', displayNull]; uiNamespace setVariable ['ACME_SK_Grab', false]; uiNamespace setVariable ['ACME_SK_Shade', []]; uiNamespace setVariable ['ACME_SK_Shade_dlg', displayNull]; uiNamespace setVariable ['ACME_flashlightMenuActive', false];";

    class ControlsBackground {
        class ACME_SK_Backdrop: RscText {
            idc = 86310;
            text = "";
            x = "safeZoneX + (safeZoneW / 2) - (safeZoneW / 4.35)";
            y = "safeZoneY + (safeZoneH / 2) - (safeZoneH / 2.5)";
            w = "safeZoneW / 2.17";
            h = "safeZoneH / 1.25";
            colorBackground[] = {0,0,0,0.84};
            colorText[] = {1,1,1,1};
        };
        class ACME_SK_Title: RscText {
            idc = 86311;
            text = "Narc Box";
            x = "safeZoneX + (safeZoneW / 2) - (safeZoneW / 4.35)";
            y = "safeZoneY + (safeZoneH / 2) - (safeZoneH / 2.5)";
            w = "safeZoneW / 2.17";
            h = "safeZoneH / 20";
            colorText[] = {1,1,1,1};
            colorBackground[] = {0,0,0,0};
            font = "RobotoCondensed";
            sizeEx = "safeZoneH / 30";
            style = 2;
            shadow = 0;
        };
        class ACME_SK_BarrelBG: RscPicture {
            idc = 86312;
            text = "#(argb,8,8,3)color(1,1,1,1)";
            colorText[] = {1,1,1,0.1};
            x = "safeZoneX + (safeZoneW / 2)";
            y = "safeZoneY + (safeZoneH / 2) - (safeZoneH / 4)";
            w = "safeZoneW / 22";
            h = "safeZoneH / 3";
        };
    };

    class Controls {
        class ACME_SK_Fluid: RscPicture {
            idc = 86313;
            text = "#(argb,8,8,3)color(1,1,1,1)";
            colorText[] = {0.55,0.78,1,0.62};
            x = "safeZoneX + (safeZoneW / 2)";
            y = "safeZoneY + (safeZoneH / 2) - (safeZoneH / 4)";
            w = "safeZoneW / 22";
            h = "safeZoneH / 8";
        };
        // the real in-game saline-flush syringe, drawn on top of the blue fluid rect so the fluid reads as liquid
        // inside the translucent glass barrel. it is fully positioned in onload, and ACME_SK_Geo aligns the fluid
        // column and the moving plunger line to the barrel glass.
        class ACME_SK_Syringe: RscPicture {
            idc = 86326;
            text = "\acm_extended\ui\items\salineFlush_ca.paa";
            colorText[] = {1,1,1,1};
            x = "safeZoneX + (safeZoneW / 2)";
            y = "safeZoneY + (safeZoneH / 2) - (safeZoneH / 4)";
            w = "safeZoneW / 10";
            h = "safeZoneH / 3";
        };
        class ACME_SK_Plunger: RscPicture {
            idc = 86314;
            text = "#(argb,8,8,3)color(1,1,1,1)";
            colorText[] = {0.18,0.18,0.2,1};
            x = "safeZoneX + (safeZoneW / 2)";
            y = "safeZoneY + (safeZoneH / 2)";
            w = "safeZoneW / 22";
            h = "safeZoneH / 80";
        };
        class ACME_SK_Rod: RscPicture {
            idc = 86315;
            text = "#(argb,8,8,3)color(1,1,1,1)";
            colorText[] = {0.5,0.5,0.52,1};
            x = "safeZoneX + (safeZoneW / 2)";
            y = "safeZoneY + (safeZoneH / 2)";
            w = "safeZoneW / 90";
            h = "safeZoneH / 12";
        };
        class ACME_SK_Overlay: RscButton {
            idc = 86316;
            text = "";
            colorText[] = {1,1,1,0};
            colorDisabled[] = {1,1,1,0};
            colorBackground[] = {1,1,1,0.01};
            colorBackgroundDisabled[] = {1,1,1,0};
            colorBackgroundActive[] = {1,1,1,0.01};
            colorFocused[] = {1,1,1,0.01};
            colorBorder[] = {0,0,0,0};
            x = "safeZoneX + (safeZoneW / 2)";
            y = "safeZoneY + (safeZoneH / 2) - (safeZoneH / 4)";
            w = "safeZoneW / 22";
            h = "safeZoneH / 3";
            shadow = 0;
            font = "RobotoCondensed";
            sizeEx = "0";
            action = "";
            tooltip = "Click to grab the plunger, move the mouse to draw/expel, click again to set.";
        };
        class ACME_SK_SizesLabel: RscText {
            idc = 86319;
            text = "Syringe Size";
            x = "safeZoneX + (safeZoneW / 2) - (safeZoneW / 4.6)";
            y = "safeZoneY + (safeZoneH / 2) - (safeZoneH / 3)";
            w = "safeZoneW / 7";
            h = "safeZoneH / 28";
            colorText[] = {0.8,0.8,0.8,1};
            colorBackground[] = {0,0,0,0};
            font = "RobotoCondensed";
            sizeEx = "safeZoneH / 44";
            style = 0;
        };
        class ACME_SK_SourcesLabel: ACME_SK_SizesLabel {
            idc = 86320;
            text = "Source";
        };
        class ACME_SK_SizesList: RscListBox {
            idc = 86317;
            x = "safeZoneX + (safeZoneW / 2) - (safeZoneW / 4.6)";
            y = "safeZoneY + (safeZoneH / 2) - (safeZoneH / 4)";
            w = "safeZoneW / 7";
            h = "safeZoneH / 4";
            rowHeight = "safeZoneH / 22";
            colorText[] = {1,1,1,1};
            colorSelect[] = {0,0,0,1};
            colorSelect2[] = {0,0,0,1};
            colorBackground[] = {0,0,0,0.25};
            colorSelectBackground[] = {0.7,0.7,0.7,1};
            colorSelectBackground2[] = {0.7,0.7,0.7,1};
            sizeEx = "safeZoneH / 40";
            class Items {};
        };
        class ACME_SK_SourcesList: ACME_SK_SizesList {
            idc = 86318;
            y = "safeZoneY + (safeZoneH / 2)";
            h = "safeZoneH / 6";
        };
        class ACME_SK_VolText: RscText {
            idc = 86321;
            text = "0.0 mL";
            x = "safeZoneX + (safeZoneW / 2) - (safeZoneW / 30)";
            y = "safeZoneY + (safeZoneH / 2) - (safeZoneH / 3)";
            w = "safeZoneW / 8";
            h = "safeZoneH / 22";
            colorText[] = {1,1,1,1};
            colorBackground[] = {0,0,0,0};
            font = "RobotoCondensed";
            sizeEx = "safeZoneH / 28";
            style = 2;
            shadow = 0;
        };
        class ACME_SK_Info: RscText {
            idc = 86322;
            text = "";
            x = "safeZoneX + (safeZoneW / 2) - (safeZoneW / 4.35)";
            y = "safeZoneY + (safeZoneH / 2) + (safeZoneH / 3.4)";
            w = "safeZoneW / 2.17";
            h = "safeZoneH / 22";
            colorText[] = {0.85,0.85,0.85,1};
            colorBackground[] = {0,0,0,0.4};
            font = "RobotoCondensed";
            sizeEx = "safeZoneH / 46";
            style = 2;
            shadow = 0;
        };
        class ACME_SK_Waste: RscButton {
            idc = 86323;
            text = "Waste";
            x = "safeZoneX + (safeZoneW / 2) - (safeZoneW / 4.35)";
            y = "safeZoneY + (safeZoneH / 2) + (safeZoneH / 2.8)";
            w = "safeZoneW / 8";
            h = "safeZoneH / 22";
            colorText[] = {1,1,1,1};
            colorDisabled[] = {1,1,1,0.25};
            colorBackground[] = {0,0,0,1};
            colorBackgroundDisabled[] = {0,0,0,0.35};
            colorBackgroundActive[] = {0.12,0.12,0.12,1};
            colorFocused[] = {0,0,0,1};
            colorBorder[] = {0,0,0,0};
            style = 2;
            shadow = 0;
            font = "RobotoCondensed";
            sizeEx = "safeZoneH / 46";
            action = "";
            tooltip = "Expel down to the plunger and lock that as the saline base.";
        };
        class ACME_SK_Draw: ACME_SK_Waste {
            idc = 86324;
            text = "Draw";
            tooltip = "Store the prepared push-dose pressor.";
        };
        class ACME_SK_Close: ACME_SK_Waste {
            idc = 86325;
            text = "Close";
            tooltip = "Close the syringe kit.";
        };
    };
};

class ACM_circulation_TransfusionMenu_Dialog {
    class Controls {
        // forward-declare the button base chain of ACM, so our AddBagButton reopen inherits ACM's full property set.
        // that means style at st_center, plus the colors, font, sizeex, x, y, w and h. without this, a bare class
        // AddBagButton {} reopen can be binarized as a fresh class that drops every inherited field. the engine then
        // fails to resolve AddBagButton.style at dialog load and reports "No entry ...AddBagButton.style". declaring
        // the parent and inheriting from it explicitly keeps the chain intact whatever the mod load order.
        class StopTransfusionButton;
        // override ACM's add bag button. give it an idc, because ACM left it at -1, so the updater can relabel it as
        // spike bag, spiking bag or add bag, and route it through our spike-or-add gate.
        class AddBagButton: StopTransfusionButton {
            idc = 86140;
            text = "Spike Bag";
            action = "call ACME_fnc_transfusionSpikeOrAdd";
            tooltip = "Spike the selected bag (consumes one IV line), then press again to hang it.";
        };
        // a new pull bag button, for our exact-volume, y-preserving pull. it inherits the forward-declared
        // StopTransfusionButton exactly like AddBagButton above, which is the only safe way to add a transfusion
        // button. redeclaring the existing native remove button in config, in any form, even a no-parent property
        // patch, severs its inherited geometry and collapses the layout. that caused two earlier regressions.
        // at runtime fn_updatetransfusioncontrols hides ACM's native remove button and drops this one into its slot.
        class ACME_PullBagButton: StopTransfusionButton {
            idc = 86146;
            text = "Pull Bag";
            x = "safeZoneX - 1";  // parked off-screen until the runtime drops it into the native remove slot.
            action = "call ACME_fnc_transfusionPullBag";
            tooltip = "Pull the selected hung bag off (keeps the Y tube) into the used-bag set with its remaining volume.";
        };
        // repurposed. it was "Infuse", which opened the inject-into-bag flow. medication delivery now runs through
        // prep and give infusion and the narc box. this is the mod's own button, so an edit here is layout-safe.
        class ACME_InjectMedicationBagButton: RscButton {
            text = "Discard Y Tubing";
            colorText[] = {1,1,1,1};
            colorDisabled[] = {1,1,1,0.25};
            colorBackground[] = {0,0,0,1};
            colorBackgroundDisabled[] = {0,0,0,0.35};
            colorBackgroundActive[] = {0,0,0,1};
            colorFocused[] = {0,0,0,1};
            colorBorder[] = {0,0,0,0};
            idc = 86120;
            style = 2;
            x = "safeZoneX + (safeZoneW / 2) - (safeZoneW / 8)";
            y = "safeZoneY + (safeZoneH / 2) - (safeZoneH / 10)";
            w = "safeZoneW / 22";
            h = "safeZoneH / 40";
            shadow = 0;
            font = "RobotoCondensed";
            sizeEx = "safeZoneH / 50";
            action = "call ACME_fnc_discardYTubing";
            tooltip = "Cut the Y tubing off this access: remaining fluids go to the used-bag set, the tubing is consumed, and the site is freed for any other IV setup.";
        };
        // the restored infuse entry point. it opens the draw menu against the selected hung bag. only a plain normal
        // saline bag qualifies, with any remaining volume. the injected medication registers as an infusion and
        // appears in the infusions sub-list automatically. it is parked off-screen until the runtime stacks it into
        // the middle column below discard y tubing.
        class ACME_InfuseBagButton: ACME_InjectMedicationBagButton {
            idc = 86147;
            text = "Infuse";
            x = "safeZoneX - 1";
            action = "call ACME_fnc_openFromTransfusionMenu";
            tooltip = "Inject a medication into the selected normal saline bag (any volume). The bag becomes an infusion and moves to the Infusions list.";
        };
        class ACME_PrepMedicationBagButton: ACME_InjectMedicationBagButton {
            text = "Prep Infusion";
            idc = 86121;
            x = "safeZoneX + (safeZoneW / 2) + (safeZoneW / 6.8)";
            y = "safeZoneY + (safeZoneH / 2) - (safeZoneH / 6)";
            w = "safeZoneW / 12";
            h = "safeZoneH / 40";
            sizeEx = "safeZoneH / 50";
            action = "call ACME_fnc_openPrepFromInventoryMenu";
            tooltip = "Inject medication into a saline bag before starting the transfusion";
        };
        class ACME_GivePreparedBagButton: ACME_PrepMedicationBagButton {
            text = "Give Infusion";
            idc = 86122;
            y = "safeZoneY + (safeZoneH / 2) - (safeZoneH / 6) + (safeZoneH / 20)";
            action = "call ACME_fnc_givePreparedBag";
            tooltip = "Start the selected prepared medication saline bag";
        };
        // raise the selected hung bag for gravity-assisted high flow. the bag color matches the fluid, blood, plasma
        // or clear. only one bag can be up at a time, on an infusion or a transfusion. it slings the weapon smoothly
        // first, then runs a short raise countdown.
        class ACME_HangBagButton: ACME_GivePreparedBagButton {
            text = "Hang Bag";
            idc = 86134;
            // left column, one slot below "Infuse". move is at -h/6, remove at -h/7.5, infuse at -h/10 and hang bag at
            // -h/15. it uses the same x, width, height and padding as the move, remove and infuse stack, so it reads as
            // one group.
            x = "safeZoneX + (safeZoneW / 2) - (safeZoneW / 8)";
            y = "safeZoneY + (safeZoneH / 2) - (safeZoneH / 15)";
            w = "safeZoneW / 22";
            // ACM's move and remove buttons, the stack this button sits in, use
            // sizeex = gui_grid_h * 0.9 * normalize_sizeex
            // where gui_grid_h is (((safeZoneW/safeZoneH) min 1.2) / 1.2) / 25 and normalize_sizeex is 0.55 divided by
            // (getresolution select 5). the previous hardcoded 0.03921 did not match them, because it assumed wrongly that
            // those buttons were a plain RscButton. this replicates ACM's exact expression, so the label matches the stack
            // at every interface size.
            sizeEx = "(((((safeZoneW / safeZoneH) min 1.2) / 1.2) / 25) * 0.9) * (0.55 / (getResolution select 5))";
            action = "call ACME_fnc_hangBagFromMenu";
            tooltip = "Raise the selected hung IV/blood bag (gravity-assisted high flow). One bag at a time.";
        };
        // pressure infuser, directly under hang bag, because they are the two ways to make a bag run fast and the
        // medic should choose between them in one place. it uses the same column and width, one row down.
        class ACME_PressureInfuserButton: ACME_HangBagButton {
            text = "Pressure Infuse";
            // its own idc. inheriting the 86134 of hang bag meant two controls answered to the same number, so whichever
            // the engine resolved second won and the other vanished. that is why hang bag disappeared.
            idc = 86148;
            // centerd, with the same sizeex expression as the stack above it. it is stated rather than inherited, so a
            // later change to hang bag cannot pull this button out of alignment with its own row.
            style = 2;  // st_center.
            sizeEx = "(((((safeZoneW / safeZoneH) min 1.2) / 1.2) / 25) * 0.9) * (0.55 / (getResolution select 5))";
            // fn_updatetransfusioncontrols positions this at runtime one row below hang bag, exactly like every other
            // button in that column. the y here is the fallback only, for before that pass has run.
            y = "safeZoneY + (safeZoneH / 2) - (safeZoneH / 15) + (safeZoneH / 26)";
            action = "['transfusion'] call ACME_fnc_pressureInfuserAttach";
            tooltip = "Cuff the selected bag. Runs unattended and does not care about height, but bleeds down as the bag empties and must be pumped again. Use the Infusions pressure button for medicated bags.";
        };
        class ACME_InfusionPressureButton: ACME_PressureInfuserButton {
            idc = 86149;
            x = "safeZoneX - 1";
            action = "['infusion'] call ACME_fnc_pressureInfuserAttach";
            tooltip = "Apply or re-pump a cuff on the selected infusion. Pressure increases delivery through the set clamp; a closed clamp remains closed.";
        };
        // our own spike and add button. ACM's AddBagButton anchor would not render on the reflowed right column. a
        // brand-new control always renders. fn_updatetransfusioncontrols positions it under the bag list and cycles
        // its label from spike bag to spiking bag to add bag by spike state, and it routes through our spike-or-add
        // gate. the default geometry mirrors the right-column buttons, and the updater overrides it each frame.
        class ACME_SpikeBagButton: ACME_GivePreparedBagButton {
            text = "Spike Bag";
            idc = 86141;
            x = "safeZoneX + (safeZoneW / 2) + (safeZoneW / 7.75)";
            y = "safeZoneY + (safeZoneH / 2) - (safeZoneH / 12)";
            w = "safeZoneW / 8.5";
            action = "call ACME_fnc_transfusionSpikeOrAdd";
            tooltip = "Spike the selected bag (consumes one IV line), then press again to hang it.";
        };
        // y-tubing button. it appears next to spike bag when a medic selects a blood bag. it builds a y set, which
        // consumes a y-type tubing set and pairs a saline bag. the updater shows it and relabels it between y tubing
        // and pick saline.
        class ACME_YTubingButton: ACME_SpikeBagButton {
            text = "Spike Y tubing";
            idc = 86142;
            action = "call ACME_fnc_transfusionYTubing";
            tooltip = "Build a Y-type blood line: consumes a Y tubing set and pairs a saline bag to the blood unit.";
        };
        // flush line button. it appears above infuse when the selected blood line needs a flush between units.
        class ACME_FlushLineButton: ACME_SpikeBagButton {
            text = "Flush Line";
            idc = 86143;
            action = "call ACME_fnc_transfusionFlushLine";
            tooltip = "Flush the blood line with its paired saline so the next unit is ready to hang.";
        };
        // the prepared iv sets button. it toggles the right-hand fluid list between the normal loose and cooler bags
        // and the stored prepared iv sets of the provider. the updater positions it directly above the fluid list, and
        // it uses the same visual style as the other right-column buttons. a medic builds a set through spike y
        // tubing, then select flush saline, then build y tubing, and hangs it with the spike button, which is
        // relabeled "Hang Set" while this mode is on.
        class ACME_PreparedSetsButton: ACME_SpikeBagButton {
            text = "Prepared IV sets";
            idc = 86144;
            action = "call ACME_fnc_togglePreparedSets";
            tooltip = "Show your prepared IV sets. Build one with Spike Y tubing, Select Flush Saline, then Build Y Tubing.";
        };
        // overlay listbox for the prepared iv sets. it shows in place of the native bag list, 86005, while the prepared
        // iv sets mode is on. the updater hides 86005 and shows this, positioned over the same rectangle. it is a
        // separate control rather than a repopulated 86005, so ACM's own updatebaglist, which fully clears and
        // rebuilds 86005 on a body-part, iv or inventory change, never clobbers our rows. LeftPanelList, the
        // RscListBox-derived base the native lists use, is forward-declared so this reopen inherits its full property
        // set intact.
        class LeftPanelList;
        class ACME_PreparedSetsList: LeftPanelList {
            idc = 86145;
        };
        class ACME_PreparedInfusionTitle: RscText {
            idc = 86130;
            text = "Prepared Infusions";
            x = "safeZoneX + (safeZoneW / 2) + (safeZoneW / 7.75)";
            y = "safeZoneY + (safeZoneH / 2) - (safeZoneH / 6) + (safeZoneH / 10)";
            w = "safeZoneW / 8.5";
            h = "safeZoneH / 45";
            colorText[] = {1,1,1,1};
            colorBackground[] = {0,0,0,0.55};
            font = "RobotoCondensed";
            sizeEx = "safeZoneH / 58";
            style = 2;
            shadow = 0;
        };
        class ACME_PreparedInfusionList: RscListBox {
            idc = 86127;
            x = "safeZoneX + (safeZoneW / 2) + (safeZoneW / 7.75)";
            y = "safeZoneY + (safeZoneH / 2) - (safeZoneH / 6) + (safeZoneH / 10) + (safeZoneH / 45)";
            w = "safeZoneW / 8.5";
            h = "safeZoneH / 10";
            rowHeight = "safeZoneH / 25";
            colorText[] = {1,1,1,1};
            colorSelect[] = {0,0,0,1};
            colorSelect2[] = {0,0,0,1};
            colorBackground[] = {0,0,0,0.25};
            colorSelectBackground[] = {0.7,0.7,0.7,1};
            colorSelectBackground2[] = {0.7,0.7,0.7,1};
            font = "RobotoCondensed";
            sizeEx = "safeZoneH / 50";
            onLBSelChanged = "params ['_ctrl','_index']; if (_index >= 0) then {missionNamespace setVariable ['ACME_infusion_SelectedPreparedIndex', _ctrl lbValue _index];};";
        };
        class ACME_ActiveInfusionTitle: ACME_PreparedInfusionTitle {
            idc = 86128;
            text = "Infusions";
            x = "safeZoneX + (safeZoneW / 2) - (safeZoneW / 4.05)";
            y = "safeZoneY + (safeZoneH / 2) + (safeZoneH / 14)";
            w = "safeZoneW / 8.5";
        };
        class ACME_ActiveInfusionList: ACME_PreparedInfusionList {
            idc = 86129;
            x = "safeZoneX + (safeZoneW / 2) - (safeZoneW / 4.05)";
            y = "safeZoneY + (safeZoneH / 2) + (safeZoneH / 14) + (safeZoneH / 45)";
            w = "safeZoneW / 8.5";
            h = "safeZoneH / 8";
            onLBSelChanged = "params ['_ctrl','_index']; if (_index >= 0) then {private _v = _ctrl lbValue _index; missionNamespace setVariable ['ACME_infusion_SelectedActiveInfusionSelectionIndex', _v]; private _sel = missionNamespace getVariable ['ACM_circulation_TransfusionMenu_Selection_IVBags', []]; missionNamespace setVariable ['ACME_infusion_SelectedActiveInfusionTrueIndex', if (_v >= 0 && {_v < count _sel}) then {(_sel select _v) param [8, -1]} else {-1}]; private _native = ctrlParent _ctrl displayCtrl 86004; if (!isNull _native) then {_native lbSetCurSel -1;};};";
        };
        class ACME_RateReadout: RscText {
            idc = 86126;
            text = "Select medicated saline bag";
            x = "safeZoneX + (safeZoneW / 2) - (safeZoneW / 4.35)";
            y = "safeZoneY + (safeZoneH / 2) + (safeZoneH / 4.75)";
            w = "safeZoneW / 3.1";
            h = "safeZoneH / 32";
            colorText[] = {1,1,1,1};
            colorBackground[] = {0,0,0,0.55};
            font = "RobotoCondensed";
            sizeEx = "safeZoneH / 55";
            style = 2;
            shadow = 0;
        };
        class ACME_DropSetButton: ACME_InjectMedicationBagButton {
            text = "Drop Set";
            idc = 86123;
            x = "safeZoneX + (safeZoneW / 2) - (safeZoneW / 4.35)";
            y = "safeZoneY + (safeZoneH / 2) + (safeZoneH / 5.45)";
            w = "safeZoneW / 13";
            action = "call ACME_fnc_cycleDropSet";
            tooltip = "Cycle drop set: 10, 15, 20, or 60 gtt/mL";
        };
        class ACME_RateDownButton: ACME_DropSetButton {
            text = "Rate -";
            idc = 86124;
            x = "safeZoneX + (safeZoneW / 2) - (safeZoneW / 6.6)";
            action = "[-1] call ACME_fnc_adjustDripRate";
            tooltip = "Decrease medication drip rate";
        };
        class ACME_RateUpButton: ACME_DropSetButton {
            text = "Rate +";
            idc = 86125;
            x = "safeZoneX + (safeZoneW / 2) - (safeZoneW / 14.2)";
            action = "[1] call ACME_fnc_adjustDripRate";
            tooltip = "Increase medication drip rate";
        };
        class ACME_MoveInfusionButton: ACME_DropSetButton {
            text = "Move";
            idc = 86132;
            x = "safeZoneX + (safeZoneW / 2) - (safeZoneW / 4.05)";
            y = "safeZoneY + (safeZoneH / 2) + (safeZoneH / 5)";
            w = "safeZoneW / 8.5";
            h = "safeZoneH / 40";
            action = "call ACME_fnc_moveInfusionBag";
            tooltip = "Move the selected infusion's bag to another access site";
        };
        class ACME_RemoveInfusionButton: ACME_MoveInfusionButton {
            text = "Remove";
            idc = 86133;
            y = "safeZoneY + (safeZoneH / 2) + (safeZoneH / 4.4)";
            action = "call ACME_fnc_removeInfusionBag";
            tooltip = "Remove the selected infusion's bag";
        };
        class ACME_AdjustInfusionButton: ACME_DropSetButton {
            text = "Adjust Infusion";
            idc = 86131;
            colorText[] = {1, 0.85, 0.16, 1};
            colorDisabled[] = {1, 0.85, 0.16, 0.25};
            x = "safeZoneX + (safeZoneW / 2) - (safeZoneW / 4.05)";
            y = "safeZoneY + (safeZoneH / 2) + (safeZoneH / 14) - (safeZoneH / 38)";
            w = "safeZoneW / 8.5";
            h = "safeZoneH / 40";
            action = "call ACME_fnc_openRollerClamp";
            tooltip = "Open the roller clamp for the selected infusion";
        };
    };
};

// over-resuscitation pulmonary-edema breath sounds, the wet crackles. these are inlined from the former
// CfgSounds.hpp say3d definitions, so the build has no #include to drop.
// there is one per respiratory-rate bucket, so the rate selection of the stethoscope, fast, slow or normal,
// lines up with the actual respiration of the patient. they are selected when the stethoscope_lungstate field
// of the patient is 3, which the updateLungState override sets from ACM's Overload_Volume. the format mirrors
// ACM's own breath sounds: {file, db, pitch}.

class ACME_HangBag_Tuner {
    idd = 87100;
    movingEnable = 0;
    enableSimulation = 1;
    onLoad = "[_this select 0] call ACME_fnc_minigameInputInstall; _this call ACME_fnc_hangBagTuneLoad";
    class controlsBackground {
        class BG: RscText {
            idc = -1;
            x = "safeZoneX + safeZoneW - 0.44";
            y = "safeZoneY + 0.035";
            w = 0.42;
            h = 0.90;
            colorBackground[] = {0,0,0,0.88};
        };
        class Title: RscText {
            idc = -1;
            text = "RIGHT-HAND IV BAG + LINE LIVE PLACEMENT";
            x = "safeZoneX + safeZoneW - 0.43";
            y = "safeZoneY + 0.045";
            w = 0.40;
            h = 0.035;
            sizeEx = 0.028;
        };
        class BagPosTitle: RscText {
            idc = -1;
            text = "BAG POSITION ON RIGHT HAND  (-5.00 m to +5.00 m)";
            x = "safeZoneX + safeZoneW - 0.43";
            y = "safeZoneY + 0.087";
            w = 0.40;
            h = 0.03;
            sizeEx = 0.021;
            colorText[] = {0.70,0.88,1,1};
        };
        class BagRotTitle: BagPosTitle {
            text = "BAG ORIENTATION  (-360 deg to +360 deg)";
            y = "safeZoneY + 0.247";
        };
        class LinePosTitle: BagPosTitle {
            text = "IV PATIENT-END POSITION  (-5.00 m to +5.00 m)";
            y = "safeZoneY + 0.407";
        };
        class LineRotTitle: BagPosTitle {
            text = "IV PATIENT-END ORIENTATION  (-360 deg to +360 deg)";
            y = "safeZoneY + 0.567";
        };
    };
    class controls {
        class SX: RscXSliderH {
            idc = 87101;
            x = "safeZoneX + safeZoneW - 0.425";
            y = "safeZoneY + 0.122";
            w = 0.245;
            h = 0.024;
            onSliderPosChanged = "[] call ACME_fnc_hangBagTuneUpdate";
        };
        class SY: SX {idc = 87102; y = "safeZoneY + 0.162";};
        class SZ: SX {idc = 87103; y = "safeZoneY + 0.202";};
        class SYaw: SX {idc = 87104; y = "safeZoneY + 0.282";};
        class SPitch: SX {idc = 87105; y = "safeZoneY + 0.322";};
        class SRoll: SX {idc = 87106; y = "safeZoneY + 0.362";};
        class SLineX: SX {idc = 87107; y = "safeZoneY + 0.442";};
        class SLineY: SX {idc = 87108; y = "safeZoneY + 0.482";};
        class SLineZ: SX {idc = 87109; y = "safeZoneY + 0.522";};
        class SLineYaw: SX {idc = 87120; y = "safeZoneY + 0.602";};
        class SLinePitch: SX {idc = 87121; y = "safeZoneY + 0.642";};
        class SLineRoll: SX {idc = 87122; y = "safeZoneY + 0.682";};

        class LX: RscText {
            idc = 87111;
            x = "safeZoneX + safeZoneW - 0.175";
            y = "safeZoneY + 0.114";
            w = 0.145;
            h = 0.04;
            sizeEx = 0.020;
        };
        class LY: LX {idc = 87112; y = "safeZoneY + 0.154";};
        class LZ: LX {idc = 87113; y = "safeZoneY + 0.194";};
        class LYaw: LX {idc = 87114; y = "safeZoneY + 0.274";};
        class LPitch: LX {idc = 87115; y = "safeZoneY + 0.314";};
        class LRoll: LX {idc = 87116; y = "safeZoneY + 0.354";};
        class LLineX: LX {idc = 87117; y = "safeZoneY + 0.434";};
        class LLineY: LX {idc = 87118; y = "safeZoneY + 0.474";};
        class LLineZ: LX {idc = 87119; y = "safeZoneY + 0.514";};
        class LLineYaw: LX {idc = 87123; y = "safeZoneY + 0.594";};
        class LLinePitch: LX {idc = 87124; y = "safeZoneY + 0.634";};
        class LLineRoll: LX {idc = 87125; y = "safeZoneY + 0.674";};

        class Hint: RscText {
            idc = -1;
            text = "Bag is parented to RightHand. IV-end roll starts at 180 deg (top down). All changes apply live; F2 reopens.";
            x = "safeZoneX + safeZoneW - 0.425";
            y = "safeZoneY + 0.730";
            w = 0.395;
            h = 0.055;
            sizeEx = 0.019;
            colorText[] = {0.82,0.82,0.82,1};
        };
        class Report: RscButton {
            idc = -1;
            text = "REPORT VALUES";
            x = "safeZoneX + safeZoneW - 0.425";
            y = "safeZoneY + 0.805";
            w = 0.19;
            h = 0.04;
            action = "[] call ACME_fnc_hangBagTuneReport";
            tooltip = "Show exact right-hand bag and patient-end line values";
        };
        class Close: Report {
            text = "DONE";
            x = "safeZoneX + safeZoneW - 0.225";
            w = 0.195;
            action = "closeDialog 0";
            tooltip = "Close the tuner";
        };
    };
};

// live tilt tuner for "Elevate Head 30". it has sliders for the pitch angle, the pivot offset and the body
// lift, applied live to the currently elevated casualty. it mirrors the hang-bag tuner.
class ACME_HeadElev_Tuner {
    idd = 87200;
    movingEnable = 0;
    enableSimulation = 1;
    onLoad = "[_this select 0] call ACME_fnc_minigameInputInstall; _this call ACME_fnc_headElevTuneLoad";
    onUnload = "missionNamespace setVariable ['ACME_headElev_tuning', false]";
    class controlsBackground {
        class BG: RscText {
            idc = -1;
            x = "safeZoneX + safeZoneW - 0.44";
            y = "safeZoneY + 0.035";
            w = 0.42;
            h = 0.79;
            colorBackground[] = {0,0,0,0.88};
        };
        class Title: RscText {
            idc = -1;
            text = "HEAD / PLATE-CARRIER LIVE TUNER";
            x = "safeZoneX + safeZoneW - 0.43";
            y = "safeZoneY + 0.045";
            w = 0.40;
            h = 0.035;
            sizeEx = 0.028;
        };
        class TiltTitle: RscText {
            idc = -1;
            text = "EXTRA TILT  (0 = animation pose only)";
            x = "safeZoneX + safeZoneW - 0.43";
            y = "safeZoneY + 0.087";
            w = 0.40;
            h = 0.03;
            sizeEx = 0.021;
            colorText[] = {0.70,0.88,1,1};
        };
        class PivotTitle: TiltTitle {
            text = "POSITION NUDGE  (-2.00 m to +2.00 m)  X / Y / Z";
            y = "safeZoneY + 0.207";
        };
        class LiftTitle: TiltTitle {
            text = "BODY LIFT  (-1.00 m to +1.00 m)";
            y = "safeZoneY + 0.367";
        };
        class VestOffTitle: TiltTitle {
            text = "PLATE-CARRIER OFFSET  (m, Spine3)  X / Y / Z";
            y = "safeZoneY + 0.450";
            colorText[] = {1,0.85,0.55,1};
        };
        class VestRotTitle: VestOffTitle {
            text = "PLATE-CARRIER ORIENT  (deg)  Pitch / Yaw / Roll";
            y = "safeZoneY + 0.602";
        };
    };
    class controls {
        class STilt: RscXSliderH {
            idc = 87201;
            x = "safeZoneX + safeZoneW - 0.425";
            y = "safeZoneY + 0.122";
            w = 0.245;
            h = 0.024;
            onSliderPosChanged = "[] call ACME_fnc_headElevTuneUpdate";
        };
        class SPivotX: STilt {idc = 87202; y = "safeZoneY + 0.242";};
        class SPivotY: STilt {idc = 87203; y = "safeZoneY + 0.282";};
        class SPivotZ: STilt {idc = 87204; y = "safeZoneY + 0.322";};
        class SLift:   STilt {idc = 87205; y = "safeZoneY + 0.402";};
        class SVestOffX: STilt {idc = 87221; y = "safeZoneY + 0.482";};
        class SVestOffY: STilt {idc = 87222; y = "safeZoneY + 0.520";};
        class SVestOffZ: STilt {idc = 87223; y = "safeZoneY + 0.558";};
        class SVestPitch: STilt {idc = 87224; y = "safeZoneY + 0.634";};
        class SVestYaw:   STilt {idc = 87225; y = "safeZoneY + 0.672";};
        class SVestRoll:  STilt {idc = 87226; y = "safeZoneY + 0.710";};

        class LTilt: RscText {
            idc = 87211;
            x = "safeZoneX + safeZoneW - 0.175";
            y = "safeZoneY + 0.114";
            w = 0.145;
            h = 0.04;
            sizeEx = 0.020;
        };
        class LPivotX: LTilt {idc = 87212; y = "safeZoneY + 0.234";};
        class LPivotY: LTilt {idc = 87213; y = "safeZoneY + 0.274";};
        class LPivotZ: LTilt {idc = 87214; y = "safeZoneY + 0.314";};
        class LLift:   LTilt {idc = 87215; y = "safeZoneY + 0.394";};
        class LVestOffX: LTilt {idc = 87231; y = "safeZoneY + 0.474";};
        class LVestOffY: LTilt {idc = 87232; y = "safeZoneY + 0.512";};
        class LVestOffZ: LTilt {idc = 87233; y = "safeZoneY + 0.550";};
        class LVestPitch: LTilt {idc = 87234; y = "safeZoneY + 0.626";};
        class LVestYaw:   LTilt {idc = 87235; y = "safeZoneY + 0.664";};
        class LVestRoll:  LTilt {idc = 87236; y = "safeZoneY + 0.702";};

        class Hint: RscText {
            idc = -1;
            text = "Head rows tune the casualty pose. Plate-carrier rows move and rotate the upper-back prop live.";
            x = "safeZoneX + safeZoneW - 0.425";
            y = "safeZoneY + 0.752";
            w = 0.395;
            h = 0.055;
            sizeEx = 0.019;
            colorText[] = {0.82,0.82,0.82,1};
        };
        class Report: RscButton {
            idc = -1;
            text = "REPORT VALUES";
            x = "safeZoneX + safeZoneW - 0.425";
            y = "safeZoneY + 0.810";
            w = 0.19;
            h = 0.04;
            action = "[] call ACME_fnc_headElevTuneReport";
            tooltip = "Show exact tilt/pivot/lift values";
        };
        class Close: RscButton {
            idc = -1;
            text = "DONE";
            x = "safeZoneX + safeZoneW - 0.225";
            y = "safeZoneY + 0.810";
            w = 0.195;
            h = 0.04;
            action = "closeDialog 0";
            tooltip = "Close the tuner";
        };
    };
};

// zeus: the place IV module dialog.
// a small centered popup, opened when a curator drops the "Place IV" module on a casualty. three listboxes, limb,
// access site and gauge, then apply or cancel. the module function stashes the target in uiNamespace
// ACME_IVModule_target and ACME_fnc_zeusIVDialogConfirm reads the controls and applies it.
// idd 87900 was free. the taken set is 71500, 71510, 86200, 86300, 86400, 86500, 86600, 87100, 87200, 87300,
// 87310, 87400, 87500, 87600, 87620, 87700 and 87800.
class ACME_IVModule_Dialog {
    idd = 87900;
    movingEnable = 0;
    enableSimulation = 1;
    onLoad = "uiNamespace setVariable ['ACME_IVModule_display', _this select 0]; private _d = _this select 0; lbClear (_d displayCtrl 87901); { (_d displayCtrl 87901) lbAdd _x } forEach ['Left arm','Right arm','Left leg','Right leg','Neck (EJ)']; (_d displayCtrl 87901) lbSetCurSel 0; lbClear (_d displayCtrl 87902); { (_d displayCtrl 87902) lbAdd _x } forEach ['Upper','Middle','Lower','Left (EJ)','Right (EJ)']; (_d displayCtrl 87902) lbSetCurSel 1; call ACME_fnc_zeusIVDialogSite; lbClear (_d displayCtrl 87903); { (_d displayCtrl 87903) lbAdd _x } forEach ['14g','16g','18g','20g']; (_d displayCtrl 87903) lbSetCurSel 1;";
    class controlsBackground {
        class BG: RscText {
            idc = -1;
            x = 0.5 - 0.22;
            y = 0.5 - 0.20;
            w = 0.44;
            h = 0.40;
            colorBackground[] = {0,0,0,0.90};
        };
        class Title: RscText {
            idc = -1;
            text = "PLACE IV";
            x = 0.5 - 0.21;
            y = 0.5 - 0.19;
            w = 0.42;
            h = 0.035;
            sizeEx = 0.030;
            colorText[] = {0.70,0.88,1,1};
        };
        class LimbLabel: RscText {
            idc = -1;
            text = "Limb";
            x = 0.5 - 0.21;
            y = 0.5 - 0.145;
            w = 0.13;
            h = 0.03;
            sizeEx = 0.024;
        };
        class SiteLabel: RscText {
            idc = -1;
            text = "Access site";
            x = 0.5 - 0.07;
            y = 0.5 - 0.145;
            w = 0.13;
            h = 0.03;
            sizeEx = 0.024;
        };
        class GaugeLabel: RscText {
            idc = -1;
            text = "Gauge";
            x = 0.5 + 0.07;
            y = 0.5 - 0.145;
            w = 0.13;
            h = 0.03;
            sizeEx = 0.024;
        };
        // the neck takes left or right rather than a height. the site column carries both sets and greys the ones
        // that do not apply, in fn_zeusIVDialogSite, so this line only has to say which is which.
        class Hint: RscText {
            idc = -1;
            text = "Neck (EJ) takes a side. An arm or a leg takes a height. The rest grey out.";
            x = 0.5 - 0.21;
            y = 0.5 + 0.075;
            w = 0.42;
            h = 0.03;
            sizeEx = 0.020;
            colorText[] = {0.75,0.75,0.75,1};
        };
    };
    class controls {
        class LimbList: RscListBox {
            idc = 87901;
            // the neck takes a side and a limb takes a height, so changing the limb re-greys the site column.
            onLBSelChanged = "call ACME_fnc_zeusIVDialogSite";
            x = 0.5 - 0.21;
            y = 0.5 - 0.11;
            w = 0.13;
            h = 0.175;
            sizeEx = 0.024;
        };
        class SiteList: RscListBox {
            idc = 87902;
            // an RscListBox has a per-row colour and no per-row disable, so a click still lands on a greyed row.
            // this bounces it back to a row that applies.
            onLBSelChanged = "call ACME_fnc_zeusIVDialogSite";
            x = 0.5 - 0.07;
            y = 0.5 - 0.11;
            w = 0.13;
            h = 0.175;
            sizeEx = 0.024;
        };
        class GaugeList: RscListBox {
            idc = 87903;
            x = 0.5 + 0.07;
            y = 0.5 - 0.11;
            w = 0.13;
            h = 0.175;
            sizeEx = 0.024;
        };
        class BtnConfirm: RscButton {
            idc = -1;
            text = "Place";
            x = 0.5 + 0.045;
            y = 0.5 + 0.135;
            w = 0.165;
            h = 0.04;
            colorBackground[] = {0.12,0.28,0.16,1};
            action = "call ACME_fnc_zeusIVDialogConfirm";
        };
        class BtnCancel: RscButton {
            idc = -1;
            text = "Cancel";
            x = 0.5 - 0.21;
            y = 0.5 + 0.135;
            w = 0.165;
            h = 0.04;
            colorBackground[] = {0.20,0.20,0.20,1};
            action = "closeDialog 0";
        };
    };
};

// zeus: the inflict TBI module dialog.
// this is a small centerd popup, opened when a curator drops the "Inflict TBI" zeus module on a casualty. it
// has a severity slider, a state listbox and confirm and cancel. the module function stashes the target unit
// in uinamespace ACME_TBIModule_target, and the confirm handler, ACME_fnc_zeusTBIDialogConfirm, reads the
// controls and applies it.
class ACME_TBIModule_Dialog {
    idd = 87500;
    movingEnable = 0;
    enableSimulation = 1;
    onLoad = "uiNamespace setVariable ['ACME_TBIModule_display', _this select 0]; lbClear ((_this select 0) displayCtrl 87502); { ((_this select 0) displayCtrl 87502) lbAdd _x } forEach ['Mild','Moderate','Severe','Herniating']; ((_this select 0) displayCtrl 87502) lbSetCurSel 1; ((_this select 0) displayCtrl 87501) sliderSetRange [0, 1]; ((_this select 0) displayCtrl 87501) sliderSetPosition 0.5;";
    class controlsBackground {
        class BG: RscText {
            idc = -1;
            x = 0.5 - 0.18;
            y = 0.5 - 0.16;
            w = 0.36;
            h = 0.32;
            colorBackground[] = {0,0,0,0.90};
        };
        class Title: RscText {
            idc = -1;
            text = "INFLICT TRAUMATIC BRAIN INJURY";
            x = 0.5 - 0.17;
            y = 0.5 - 0.15;
            w = 0.34;
            h = 0.035;
            sizeEx = 0.030;
            colorText[] = {0.70,0.88,1,1};
        };
        class SevLabel: RscText {
            idc = -1;
            text = "Severity (0 = mild, 1 = maximal)";
            x = 0.5 - 0.17;
            y = 0.5 - 0.10;
            w = 0.34;
            h = 0.03;
            sizeEx = 0.024;
        };
        class StateLabel: RscText {
            idc = -1;
            text = "Initial state";
            x = 0.5 - 0.17;
            y = 0.5 - 0.005;
            w = 0.34;
            h = 0.03;
            sizeEx = 0.024;
        };
    };
    class controls {
        class SevSlider: RscXSliderH {
            idc = 87501;
            x = 0.5 - 0.17;
            y = 0.5 - 0.065;
            w = 0.34;
            h = 0.04;
        };
        class StateList: RscListBox {
            idc = 87502;
            x = 0.5 - 0.17;
            y = 0.5 + 0.03;
            w = 0.34;
            h = 0.075;
            sizeEx = 0.026;
        };
        class BtnConfirm: RscButton {
            idc = -1;
            text = "Apply";
            x = 0.5 + 0.005;
            y = 0.5 + 0.115;
            w = 0.165;
            h = 0.04;
            colorBackground[] = {0.30,0.12,0.12,1};
            action = "call ACME_fnc_zeusTBIDialogConfirm";
        };
        class BtnCancel: RscButton {
            idc = -1;
            text = "Cancel";
            x = 0.5 - 0.17;
            y = 0.5 + 0.115;
            w = 0.165;
            h = 0.04;
            colorBackground[] = {0.15,0.15,0.15,1};
            action = "closeDialog 2";
        };
    };
};

// zeus: the place blood fridge popup.
// it opens when a curator places the "Place Blood Fridge" module live. the sliders set the o+, o- and
// each-other counts, and the regen interval in hours and minutes. apply spawns the fridge at the stashed
// placement position, uinamespace ACME_bf_placePos and placedir. the value labels update through the
// onSliderPosChanged of each slider.

// blood fridge contents. this shows what is in there, by type, with what it is and how cold it is kept. the
// interaction menu could only ever be a list of take actions. this is the fridge itself, so a medic can look
// before they commit to opening it and see at a glance whether the type they need is present.
class ACME_BloodFridgeContents_Dialog {
    idd = 87620;
    movingEnable = 0;
    enableSimulation = 1;
    onLoad = "[_this select 0] call ACME_fnc_minigameInputInstall; uiNamespace setVariable ['ACME_bfc_dlg', _this select 0]; call ACME_fnc_bloodFridgeContentsFill;";
    class controlsBackground {
        class BG: RscText { idc = -1; x = 0.5 - 0.22; y = 0.5 - 0.28; w = 0.44; h = 0.56; colorBackground[] = {0.03,0.03,0.05,0.94}; };
        class Header: RscText { idc = -1; x = 0.5 - 0.22; y = 0.5 - 0.28; w = 0.44; h = 0.045; colorBackground[] = {0.30,0.10,0.10,1}; };
        class Title: RscText { idc = -1; text = "BLOOD FRIDGE"; x = 0.5 - 0.205; y = 0.5 - 0.277; w = 0.30; h = 0.04; sizeEx = 0.032; colorText[] = {0.95,0.90,0.85,1}; };
        class Sub: RscText { idc = 87621; text = ""; x = 0.5 - 0.205; y = 0.5 - 0.228; w = 0.41; h = 0.03; sizeEx = 0.022; colorText[] = {0.70,0.72,0.78,1}; };
        class HdrType: RscText { idc = -1; text = "TYPE"; x = 0.5 - 0.205; y = 0.5 - 0.192; w = 0.12; h = 0.028; sizeEx = 0.020; colorText[] = {0.55,0.60,0.68,1}; };
        class HdrQty:  RscText { idc = -1; text = "UNITS"; x = 0.5 - 0.055; y = 0.5 - 0.192; w = 0.08; h = 0.028; sizeEx = 0.020; colorText[] = {0.55,0.60,0.68,1}; };
        class HdrVol:  RscText { idc = -1; text = "VOLUME"; x = 0.5 + 0.035; y = 0.5 - 0.192; w = 0.10; h = 0.028; sizeEx = 0.020; colorText[] = {0.55,0.60,0.68,1}; };
        class Rule: RscText { idc = -1; x = 0.5 - 0.205; y = 0.5 - 0.166; w = 0.41; h = 0.002; colorBackground[] = {0.35,0.38,0.44,1}; };
    };
    class controls {
        class ListC: RscStructuredText { idc = 87622; x = 0.5 - 0.205; y = 0.5 - 0.158; w = 0.41; h = 0.30; size = 0.028; };
        class Foot: RscStructuredText { idc = 87623; x = 0.5 - 0.205; y = 0.5 + 0.152; w = 0.41; h = 0.08; size = 0.024; };
        class BtnClose: RscButton { idc = -1; text = "Close"; x = 0.5 + 0.025; y = 0.5 + 0.238; w = 0.18; h = 0.038; colorBackground[] = {0.15,0.15,0.15,1}; action = "closeDialog 0"; };
    };
};

class ACME_BloodFridge_Dialog {
    idd = 87600;
    movingEnable = 0;
    enableSimulation = 1;
    onLoad = "[_this select 0] call ACME_fnc_minigameInputInstall; uiNamespace setVariable ['ACME_bf_dlg', _this select 0]; ((_this select 0) displayCtrl 87604) setVariable ['on', true]; { private _c = (_this select 0) displayCtrl (_x select 0); _c sliderSetRange [(_x select 1), (_x select 2)]; _c sliderSetPosition (_x select 3); } forEach [[87601,0,40,6],[87602,0,40,2],[87603,0,40,0],[87605,0,72,24],[87606,0,59,0]];";
    class controlsBackground {
        class BG: RscText { idc = -1; x = 0.5 - 0.20; y = 0.5 - 0.24; w = 0.40; h = 0.48; colorBackground[] = {0,0,0,0.90}; };
        class Title: RscText { idc = -1; text = "PLACE BLOOD FRIDGE"; x = 0.5 - 0.19; y = 0.5 - 0.23; w = 0.38; h = 0.035; sizeEx = 0.030; colorText[] = {0.85,0.30,0.30,1}; };
        class LOPos: RscText { idc = -1; text = "O+ units";  x = 0.5 - 0.19; y = 0.5 - 0.185; w = 0.24; h = 0.03; sizeEx = 0.024; };
        class LONeg: RscText { idc = -1; text = "O- units";  x = 0.5 - 0.19; y = 0.5 - 0.130; w = 0.24; h = 0.03; sizeEx = 0.024; };
        class LOther: RscText { idc = -1; text = "Each other type"; x = 0.5 - 0.19; y = 0.5 - 0.075; w = 0.24; h = 0.03; sizeEx = 0.024; };
        class LRestock: RscText { idc = -1; text = "Regenerates"; x = 0.5 - 0.19; y = 0.5 - 0.020; w = 0.24; h = 0.03; sizeEx = 0.024; };
        class LHours: RscText { idc = -1; text = "Regen interval: hours"; x = 0.5 - 0.19; y = 0.5 + 0.035; w = 0.28; h = 0.03; sizeEx = 0.024; };
        class LMins: RscText { idc = -1; text = "Regen interval: minutes"; x = 0.5 - 0.19; y = 0.5 + 0.090; w = 0.28; h = 0.03; sizeEx = 0.024; };
    };
    class controls {
        class SOPos: RscXSliderH { idc = 87601; x = 0.5 - 0.19; y = 0.5 - 0.160; w = 0.30; h = 0.028; onSliderPosChanged = "((uiNamespace getVariable 'ACME_bf_dlg') displayCtrl 87611) ctrlSetText str (round (_this select 1));"; };
        class VOPos: RscText { idc = 87611; text = "6"; x = 0.5 + 0.12; y = 0.5 - 0.185; w = 0.07; h = 0.03; sizeEx = 0.026; colorText[] = {0.85,0.95,1,1}; };
        class SONeg: RscXSliderH { idc = 87602; x = 0.5 - 0.19; y = 0.5 - 0.105; w = 0.30; h = 0.028; onSliderPosChanged = "((uiNamespace getVariable 'ACME_bf_dlg') displayCtrl 87612) ctrlSetText str (round (_this select 1));"; };
        class VONeg: RscText { idc = 87612; text = "2"; x = 0.5 + 0.12; y = 0.5 - 0.130; w = 0.07; h = 0.03; sizeEx = 0.026; colorText[] = {0.85,0.95,1,1}; };
        class SOther: RscXSliderH { idc = 87603; x = 0.5 - 0.19; y = 0.5 - 0.050; w = 0.30; h = 0.028; onSliderPosChanged = "((uiNamespace getVariable 'ACME_bf_dlg') displayCtrl 87613) ctrlSetText str (round (_this select 1));"; };
        class VOther: RscText { idc = 87613; text = "0"; x = 0.5 + 0.12; y = 0.5 - 0.075; w = 0.07; h = 0.03; sizeEx = 0.026; colorText[] = {0.85,0.95,1,1}; };
        class BtnRestock: RscButton { idc = 87604; text = "Yes"; x = 0.5 + 0.05; y = 0.5 - 0.020; w = 0.14; h = 0.032; colorBackground[] = {0.15,0.35,0.15,1}; action = "private _c = (uiNamespace getVariable 'ACME_bf_dlg') displayCtrl 87604; private _on = !(_c getVariable ['on', true]); _c setVariable ['on', _on]; _c ctrlSetText (['No','Yes'] select _on); _c ctrlSetBackgroundColor ([[0.35,0.15,0.15,1],[0.15,0.35,0.15,1]] select _on);"; };
        class SHours: RscXSliderH { idc = 87605; x = 0.5 - 0.19; y = 0.5 + 0.060; w = 0.30; h = 0.028; onSliderPosChanged = "((uiNamespace getVariable 'ACME_bf_dlg') displayCtrl 87615) ctrlSetText str (round (_this select 1));"; };
        class VHours: RscText { idc = 87615; text = "24"; x = 0.5 + 0.12; y = 0.5 + 0.035; w = 0.07; h = 0.03; sizeEx = 0.026; colorText[] = {0.85,0.95,1,1}; };
        class SMins: RscXSliderH { idc = 87606; x = 0.5 - 0.19; y = 0.5 + 0.115; w = 0.30; h = 0.028; onSliderPosChanged = "((uiNamespace getVariable 'ACME_bf_dlg') displayCtrl 87616) ctrlSetText str (round (_this select 1));"; };
        class VMins: RscText { idc = 87616; text = "0"; x = 0.5 + 0.12; y = 0.5 + 0.090; w = 0.07; h = 0.03; sizeEx = 0.026; colorText[] = {0.85,0.95,1,1}; };
        class BtnApply: RscButton { idc = -1; text = "Place"; x = 0.5 + 0.02; y = 0.5 + 0.170; w = 0.18; h = 0.04; colorBackground[] = {0.30,0.12,0.12,1}; action = "call ACME_fnc_bloodFridgeDialogConfirm"; };
        class BtnCancel: RscButton { idc = -1; text = "Cancel"; x = 0.5 - 0.19; y = 0.5 + 0.170; w = 0.18; h = 0.04; colorBackground[] = {0.15,0.15,0.15,1}; action = "closeDialog 2"; };
    };
};

// ventilator panel, the ventway sparrow.
// the full device face is composited over the screen, with the live ui drawn into the screen cutout. the
// acme_vent_scr_* defines below tune the cutout position and size. dial them against an in-game screenshot,
// the same way the chest-seal ellipse and the iv body-rect were tuned. every screen control lives inside the
// screen region, and fn_ventpanelinit sets their coordinates at runtime from the face rect and these
// fractions, so a retune of the cutout moves the whole ui as one. the fn_ventpanel* functions drive the
// interaction.
// the screen cutout is expressed as fractions of the full 2048 face. it is approximate, verified visually and
// final-tuned in game.
#define ACME_VENT_SCR_X 0.330
#define ACME_VENT_SCR_Y 0.410
#define ACME_VENT_SCR_W 0.212
#define ACME_VENT_SCR_H 0.180
// shadow-free bases for the ventilator screen. ACE's RscText carries shadow = 2, which puts a drop shadow
// behind every glyph. on a small backlit lcd, and especially on the zero-padded values and the little 0 to 50
// pressure numerals beside the bar, that shadow smears the type and makes the screen look dirty. a real
// device's lcd has no drop shadow. there is no runtime setter for it, so config level is the only way. these
// bases kill it once, and every text control on the panel inherits from them instead of from RscText.
// there is also a picture base for the vent panel. the battery and plug glyph is art, and a text control
// cannot show a .paa. it would render nothing silently, which looks exactly like a missing texture path.
// the fill variant drops keep-aspect. it is for art whose control rect already matches the shape of the art,
// such as the battery, whose rect is the measured block rect, so it fills exactly instead of sitting
// letterboxed and small inside.
// the global, ctrlcreate-able value field class for the vent screens has three lessons baked in.
// 1. the ACME_VentBtn of the dialog is nested inside the controls class of the dialog, and ctrlcreate resolves
// classes at config root only, so every ctrlcreate ["ACME_VentBtn"] was quietly returning controlnull.
// 2. it is an RscText-style text control and not a button, on purpose. this panel already proved that
// RscButton does not reliably take ctrlSetBackgroundColor, and the entire job of a value field is to take the
// highlight. a value field is a readout, and the dial and MMB do the clicking.
// 3. it declares its own type, font, sizeex and rect and does not rely on inheriting them. RscText is
// forward-declared in this config only, as class RscText; with no body, so a subclass of it inherits nothing.
// it gets no type, and ctrlcreate needs type to build the control. a subclass of a bodyless forward-decl was
// therefore uncreatable, which is exactly why the whole custom layout came up blank. everything the engine
// needs is spelled out here.
class ACME_VentValG {
    type = 0;  // ct_static, a text control.
    idc = -1;
    style = 2;  // st_center. the number floats centerd in its padded box, like the device.
    shadow = 0;
    x = 0; y = 0; w = 0.1; h = 0.05;
    font = "PuristaMedium";
    sizeEx = 0.03;
    text = "";
    colorText[] = {0.92,0.92,0.92,1};
    colorBackground[] = {0,0,0,0};
};

class ACME_VentPicFill: RscPicture {
    style = 48;  // st_picture only, so it fills the rect.
    colorBackground[] = {0,0,0,0};
    colorText[] = {1,1,1,1};
};

class ACME_VentPic: RscPicture {
    // keep aspect. a plain RscPicture stretches its texture to fill the control rect, which is the real reason the
    // battery was distorted and clipped. no pixel-width math can fix a control that ignores aspect. 0x800 is
    // st_keep_aspect_ratio, so the art fits inside the rect at its own proportions and is letterboxed by its own
    // transparency. the battery can now sit on the whole block rect and look right.
    style = 48 + 2048;  // st_picture, 48, plus st_keep_aspect_ratio, 0x800 or 2048.
    colorBackground[] = {0,0,0,0};
    colorText[] = {1,1,1,1};
};

class ACME_VentText: RscText {
    shadow = 0;
};
// center-aligned variant, st_center, for text that must sit centerd in its rect. that is the name lines of the
// alarm popup, which are created dynamically through ctrlcreate and need the horizontal centring the base
// RscText does not give.
class ACME_VentTextC: RscText {
    shadow = 0;
    style = 2;
};
// right-aligned variant, st_right, for the left scale numbers of the graph, so they sit flush to the left of
// the plot box with their right edge against the box, instead of being drawn under its edge.
class ACME_VentTextR: RscText {
    shadow = 0;
    style = 1;
};
class ACME_VentStructuredText: RscStructuredText {
    shadow = 0;
};

class ACME_Ventilator_Dialog {
    idd = 87700;
    movingEnable = 0;
    enableSimulation = 1;
    onLoad = "[_this select 0] call ACME_fnc_minigameInputInstall; uiNamespace setVariable ['ACME_vent_dlg', _this select 0]; [] call ACME_fnc_ventPanelInit;";
    onUnload = "_this call ACME_fnc_ventPanelClose;";
    class controlsBackground {
        class Dim: ACME_VentText {
            idc = 87709;
            x = "safezoneX"; y = "safezoneY"; w = "safezoneW"; h = "safezoneH";
            colorBackground[] = {0,0,0,0.82};
        };
        class Face: RscPicture {
            idc = 87701;
            text = "\acm_extended\ui\vent\ventway_sparrow_robust_ca.paa";
            x = 0.30; y = 0.30; w = 0.40; h = 0.40;  // repositioned at init to a true-square rect.
            colorText[] = {1,1,1,1};
        };
        // white menu inlay. it is a full-canvas overlay authored on the same 2048 canvas as the device face, with the
        // white rounded screen shape painted in position. it is positioned at the exact face rect at init, so the
        // alignment is 1:1, and layered above the device art. it provides the white surround and bezel of the screen,
        // and the dark display area and all the ui sit on top of it.
        class MenuInlay: RscPicture {
            idc = 87702;
            // the default is the startup inlay, with no black cutout. boot and the self-test run before the first inlay
            // swap of the screen router, so whatever is set here is what shows on startup. the router swaps in the cutout
            // inlay on the live screen with a patient connected only.
            text = "\acm_extended\ui\vent\ventway_sparrow_robust_menu_startup_inlay.paa";
            x = 0.30; y = 0.30; w = 0.40; h = 0.40;  // repositioned to the face rect at init.
            colorText[] = {1,1,1,1};
        };
        // knob rotation flash. it is a full-canvas 1:1 overlay like the face and the MenuInlay, so the art positions
        // itself over the physical dial with no geometry of its own. it is declared after the inlay so it draws on top
        // of it. it stays hidden until a scroll step is accepted, then the knob handler flashes it and the tick clears
        // it.
        class KnobRotate: RscPicture {
            idc = 87703;
            text = "\acm_extended\ui\vent\ventway_sparrow_robust_knob_rotate_left_ca.paa";
            x = 0.30; y = 0.30; w = 0.40; h = 0.40;  // repositioned to the face rect at init.
            colorText[] = {1,1,1,1};
        };
    };
    class controls {
        class ScreenBG: ACME_VentText {
            idc = 87710;
            x = 0.4; y = 0.4; w = 0.2; h = 0.18;
            colorBackground[] = {0.02,0.03,0.04,1};
        };
        class TitleBar: ACME_VentText { idc = 87711; x=0.4;y=0.4;w=0.2;h=0.02; colorBackground[]={0.92,0.92,0.89,1}; };
        class BottomBar: ACME_VentText { idc = 87715; x=0.4;y=0.4;w=0.2;h=0.02; colorBackground[]={0.92,0.92,0.89,1}; };
        // style 0 is left aligned. it was centerd, so a title wider than its field overflowed both sides and the left
        // overflow slid under the black block of the inlay. left alignment makes the left edge a fixed pad from where
        // the white starts, on every inlay, and no width estimate can get it wrong.
        class TitleMode: ACME_VentText { idc = 87712; text="SIMV  VC  PS"; x=0.4;y=0.4;w=0.2;h=0.02; colorText[]={0.05,0.05,0.05,1}; colorBackground[]={0,0,0,0}; style=0; sizeEx=0.023; };
        // the alarm square on the top bar. it is black normally and red whenever an alarm is up. its whole job is to
        // be seen without being read.
        class TitleBatt: ACME_VentPicFill { idc = 87713; x=0.4;y=0.4;w=0.03;h=0.014; text=""; };
        // charge fill. the battery art is a hollow outline now, so the bar inside it is drawn rather than baked. it
        // shrinks with the charge and shifts color as it falls. it is declared after the outline so it sits inside
        // it, and the geometry comes from the art itself, measured off the decoded texture.
        class TitleBattFill: ACME_VentText { idc = 87716; x=0.4;y=0.4;w=0.02;h=0.01; colorBackground[]={0,0.988,0.992,1}; };
        // declared after the battery, so a red alarm covers the plug glyph, because its rect is the plug slot. at idle
        // it is fully transparent rather than black, because an opaque black box would blank the plug on a black
        // block.
        class TitleAlarmBox: ACME_VentText { idc = 87714; style=2; x=0.4;y=0.4;w=0.03;h=0.014; colorBackground[]={0,0,0,0}; };
        class LblBPM: ACME_VentText  { idc = 87720; text="BPM"; x=0.4;y=0.4;w=0.06;h=0.03; colorText[]={0.90,0.90,0.90,1}; colorBackground[]={0,0,0,0}; sizeEx=0.028; };
        class ValBPM: ACME_VentText  { idc = 87721; text="12 (11)"; x=0.4;y=0.4;w=0.12;h=0.03; colorText[]={1,1,1,1}; colorBackground[]={0,0,0,0}; sizeEx=0.030; };
        class LblMV: ACME_VentText   { idc = 87722; text="M.V"; x=0.4;y=0.4;w=0.06;h=0.03; colorText[]={0.90,0.90,0.90,1}; colorBackground[]={0,0,0,0}; sizeEx=0.028; };
        class ValMV: ACME_VentText   { idc = 87723; text="07.49"; x=0.4;y=0.4;w=0.12;h=0.03; colorText[]={0.56,0.84,1,1}; colorBackground[]={0,0,0,0}; sizeEx=0.030; };
        class LblVT: ACME_VentText   { idc = 87724; text="VTi"; x=0.4;y=0.4;w=0.06;h=0.03; colorText[]={0.90,0.90,0.90,1}; colorBackground[]={0,0,0,0}; sizeEx=0.028; };
        class ValVTBox: ACME_VentText{ idc = 87725; x=0.4;y=0.4;w=0.12;h=0.03; colorBackground[]={0,0,0,0}; };
        class ValVT: ACME_VentText   { idc = 87726; text="0681"; x=0.4;y=0.4;w=0.12;h=0.03; colorText[]={1,1,1,1}; colorBackground[]={0,0,0,0}; sizeEx=0.030; };
        class RowParams: ACME_VentText { idc = 87727; text="PEEP 5.0        I:E 1:2.0"; x=0.4;y=0.4;w=0.2;h=0.025; colorText[]={0.80,0.80,0.80,1}; colorBackground[]={0,0,0,0}; sizeEx=0.022; };
        // the auto-PEEP figure of PEEP and the i:e ratio, split out of the PEEP row into their own fixed-position
        // controls. they used to be one formatted string, so the moment auto-PEEP appeared the whole line grew and
        // pushed i:e off the end of the screen. separate controls at a fixed x cannot push each other.
        class RowAutoPeep: ACME_VentText { idc = 87767; text=""; x=0.4;y=0.4;w=0.10;h=0.03; style=0; colorText[]={0.80,0.80,0.80,1}; colorBackground[]={0,0,0,0}; };
        class RowIE:       ACME_VentText { idc = 87768; text=""; x=0.4;y=0.4;w=0.20;h=0.03; style=0; colorText[]={0.80,0.80,0.80,1}; colorBackground[]={0,0,0,0}; };
        class GaugeFrame: ACME_VentText { idc = 87730; x=0.4;y=0.4;w=0.02;h=0.14; colorBackground[]={0.05,0.06,0.07,1}; };
        class GaugeGreen: ACME_VentText { idc = 87731; x=0.4;y=0.4;w=0.02;h=0.05; colorBackground[]={0.23,0.56,0.29,1}; };
        class GaugeBlue: ACME_VentText  { idc = 87732; x=0.4;y=0.4;w=0.02;h=0.04; colorBackground[]={0.12,0.45,0.75,1}; };
        // pressure scale to the left of the gauge. it runs 0 to 50 cmH2O in tens, and each step is a numeral plus a
        // short tick mark, like the real device. it is positioned at init, and shown and hidden with the live
        // screen.
        class GaugeLbl50: ACME_VentText { idc = 87733; x=0.4;y=0.4;w=0.03;h=0.02; colorText[]={1,1,1,1}; colorBackground[]={0,0,0,0}; style=1; text="50"; };
        class GaugeLbl40: GaugeLbl50 { idc = 87734; text="40"; };
        class GaugeLbl30: GaugeLbl50 { idc = 87735; text="30"; };
        class GaugeLbl20: GaugeLbl50 { idc = 87736; text="20"; };
        class GaugeLbl10: GaugeLbl50 { idc = 87737; text="10"; };
        class GaugeLbl0:  GaugeLbl50 { idc = 87738; text="0"; };
        class GaugeLbl60: GaugeLbl50 { idc = 87769; text="60"; };  // seventh step. the scale now runs 60 down to 0.
        class GaugeTick50: ACME_VentText { idc = 87739; x=0.4;y=0.4;w=0.006;h=0.002; colorBackground[]={1,1,1,1}; };
        class GaugeTick40: GaugeTick50 { idc = 87759; };
        class GaugeTick30: GaugeTick50 { idc = 87761; };
        class GaugeTick20: GaugeTick50 { idc = 87762; };
        class GaugeTick10: GaugeTick50 { idc = 87763; };
        class GaugeTick0:  GaugeTick50 { idc = 87764; };
        class GaugeTick60: GaugeTick50 { idc = 87774; };
        // sound-suppressed button base for the whole ventilator. it has no stock arma click, enter, push or escape
        // sounds, because the vent has its own dial and click sfx, and its active or pressed state never turns the
        // text dark, which would vanish on the black screen. every vent screen button inherits this.
        class ACME_VentBtn: RscButton {
            // no text shadow. a stock RscButton carries one, and every list row, strip button and nav chevron inherits
            // from here. on the dark screen a black outline is invisible, so it went unnoticed. the moment a row is
            // selected and turns light blue the outline appears around the text and reads as a stroke. ACME_VentText has
            // always set this and the button base never did.
            shadow = 0;
            soundEnter[] = {"", 0, 1};
            soundPush[] = {"", 0, 1};
            soundClick[] = {"", 0, 1};
            soundEscape[] = {"", 0, 1};
            colorText[] = {0.92,0.92,0.92,1};
            colorFocused[] = {0,0,0,0};
            colorBackgroundActive[] = {0,0,0,0};
            colorDisabled[] = {0.92,0.92,0.92,1};
            colorBackgroundDisabled[] = {0,0,0,0};
        };
        class BtnAlarm: ACME_VentBtn { idc = 87740; text=""; x=0.4;y=0.4;w=0.04;h=0.03; colorBackground[]={0,0,0,0}; };
        // selection highlight box behind the alarm icon. an RscText background renders reliably, unlike a button
        // background. it is defined before the icon so it sits behind it, and the refresh toggles it light blue when
        // selected.
        class HlAlarm: ACME_VentText { idc = 87748; text=""; x=0.4;y=0.4;w=0.03;h=0.03; colorBackground[]={0,0,0,0}; };
        class IcoAlarm: RscPicture { idc = 87741; text="\acm_extended\ui\vent\alarm_ca.paa"; x=0.4;y=0.4;w=0.03;h=0.03; colorText[]={0.10,0.10,0.10,1}; };
        // live alarm count, drawn next to the bell. it is a real control precisely because the number has to change:
        // it is the length of ACME_vent_alarms. the count cannot live in the icon artwork, because a baked "(0)" is a
        // picture of a zero and will read zero while the patient is dying.
        // the ventway sparrow status box is the small black square in the header, right of the battery. it shows t for
        // a patient trigger, z for zeroing transducers, or c for cough. it is a black box with a white glyph, as on
        // the device.
        class VentStatusBox: ACME_VentText { idc = 87766; text=""; x=0.4;y=0.4;w=0.03;h=0.03; style=2; colorText[]={1,1,1,1}; colorBackground[]={0,0,0,0}; };
        class TxtAlarmCount: ACME_VentText { idc = 87765; text="(0)"; x=0.4;y=0.4;w=0.04;h=0.03; style=0; colorText[]={0.10,0.10,0.10,1}; colorBackground[]={0,0,0,0}; };
        class BtnGraph: ACME_VentBtn { idc = 87742; text=""; x=0.4;y=0.4;w=0.04;h=0.03; colorBackground[]={0,0,0,0}; colorFocused[]={0,0,0,0}; };
        class HlGraph: ACME_VentText { idc = 87749; text=""; x=0.4;y=0.4;w=0.03;h=0.03; colorBackground[]={0,0,0,0}; };
        class IcoGraph: RscPicture { idc = 87743; text="\acm_extended\ui\vent\graphs_ca.paa"; x=0.4;y=0.4;w=0.03;h=0.03; colorText[]={0.10,0.10,0.10,1}; };
        class BtnBreath: ACME_VentBtn { idc = 87744; text=""; x=0.4;y=0.4;w=0.04;h=0.03; colorBackground[]={0,0,0,0}; colorFocused[]={0,0,0,0}; };
        class HlBreath: ACME_VentText { idc = 87752; text=""; x=0.4;y=0.4;w=0.03;h=0.03; colorBackground[]={0,0,0,0}; };
        class IcoBreath: RscPicture { idc = 87745; text="\acm_extended\ui\vent\manual_breath_ca.paa"; x=0.4;y=0.4;w=0.03;h=0.03; colorText[]={0.10,0.10,0.10,1}; };
        class BtnMenu: ACME_VentBtn { idc = 87746; text=""; x=0.4;y=0.4;w=0.04;h=0.03; colorBackground[]={0,0,0,0}; colorFocused[]={0,0,0,0}; };
        class HlMenu: ACME_VentText { idc = 87753; text=""; x=0.4;y=0.4;w=0.03;h=0.03; colorBackground[]={0,0,0,0}; };
        class IcoMenu: RscPicture { idc = 87747; text="\acm_extended\ui\vent\main_menu_ca.paa"; x=0.4;y=0.4;w=0.03;h=0.03; colorText[]={0.10,0.10,0.10,1}; };
        class HitBPM: ACME_VentBtn { idc = 87750; text=""; x=0.4;y=0.4;w=0.18;h=0.03; colorBackground[]={0,0,0,0}; colorFocused[]={0,0,0,0}; };
        class HitVT: ACME_VentBtn { idc = 87751; text=""; x=0.4;y=0.4;w=0.18;h=0.03; colorBackground[]={0,0,0,0}; colorFocused[]={0,0,0,0}; };
        class BootLogo: RscPictureKeepAspect { idc = 87760; text="\acm_extended\ui\vent\sparrow_startup_icon_ca.paa"; x=0.4;y=0.4;w=0.1;h=0.1; colorText[]={1,1,1,1}; };
        // keybind hint below the ventilator, in the ACM and ACE style of a mouse image plus a label. it is a dial-only
        // device, so a player scrolls to move the selection and middle-clicks to select. it is positioned under the
        // device face at init.
        class HintScrollIco: RscPictureKeepAspect { idc = 87770; text="\z\ace\addons\interaction\UI\mouse_scroll_ca.paa"; x=0.4;y=0.4;w=0.03;h=0.03; colorText[]={1,1,1,0.9}; };
        class HintScrollTxt: ACME_VentText { idc = 87771; text="Scroll: Move Selection"; x=0.4;y=0.4;w=0.20;h=0.03; colorText[]={0.9,0.9,0.9,1}; colorBackground[]={0,0,0,0}; sizeEx=0.030; };
        class HintSelIco: RscPictureKeepAspect { idc = 87772; text="\z\ace\addons\interaction\UI\mouse_scroll_ca.paa"; x=0.4;y=0.4;w=0.03;h=0.03; colorText[]={1,1,1,0.9}; };
        class HintSelTxt: ACME_VentText { idc = 87773; text="Middle Click: Select"; x=0.4;y=0.4;w=0.20;h=0.03; colorText[]={0.9,0.9,0.9,1}; colorBackground[]={0,0,0,0}; sizeEx=0.030; };
        // a keycap, not an icon. ACE's ui set has no "F" glyph, and borrowing the scroll wheel for it was wrong. it is
        // drawn as a bordered letter, which also means any rebind reads correctly.
        class HintFlipIco: ACME_VentTextC { idc = 87776; text="F"; x=0.4;y=0.4;w=0.03;h=0.03; colorText[]={0.95,0.97,1,1}; colorBackground[]={1,1,1,0.14}; sizeEx=0.026; };
        class HintFlipTxt: ACME_VentText { idc = 87777; text="Flip Device"; x=0.4;y=0.4;w=0.20;h=0.03; colorText[]={0.9,0.9,0.9,1}; colorBackground[]={0,0,0,0}; sizeEx=0.030; };
        // reverse side. these are two invisible hit zones over the battery hatch and the power button, positioned from
        // the annotated reference. they are transparent buttons rather than pictures, so they take hover and click.
        // the bounds are fully invisible. every color state is zeroed, not the resting one alone, because RscButton
        // also paints on hover, on focus and when disabled, and draws a border and a shadow. any of those left at an
        // inherited value shows the hit box as a rectangle floating on the device. the hover tooltip is the feedback,
        // so an invisible box loses nothing.
        class RevBattery: ACME_VentBtn {
            idc = 87778; text=""; x=0.4;y=0.4;w=0.1;h=0.05;
            borderSize = 0;
            colorBackground[]={0,0,0,0}; colorBackgroundActive[]={0,0,0,0}; colorBackgroundDisabled[]={0,0,0,0};
            colorFocused[]={0,0,0,0}; colorBorder[]={0,0,0,0}; colorShadow[]={0,0,0,0};
            colorText[]={0,0,0,0}; colorDisabled[]={0,0,0,0};
        };
        class RevPower: RevBattery { idc = 87779; w=0.05; };
        // hover tooltip and the swap banner. they are drawn on the device rather than the screen, because the screen is
        // not facing the medic while any of this happens.
        class RevTip:  ACME_VentTextC { idc = 88000; text=""; x=0.4;y=0.4;w=0.2;h=0.03; colorText[]={0.95,0.97,1,1}; colorBackground[]={0,0,0,0.72}; sizeEx=0.030; };
        class RevBanner: ACME_VentTextC { idc = 88001; text=""; x=0.4;y=0.4;w=0.3;h=0.04; colorText[]={0,0.988,0.992,1}; colorBackground[]={0,0,0,0.78}; sizeEx=0.036; };

        // generic list screen, reused by weight, mode, interface, connect, menu and params. it has a title label, up to
        // 6 selectable rows, and a nav strip with confirm, home, back and next. fn_ventpanelshowscreen positions and
        // populates it at runtime, and it is hidden on the live screen.
        // style 0 is left. this is the control that draws every list-screen title, and 87712 carries the mode of the
        // live screen only. it was centerd across the full screen width, so a long title reached back under the black
        // block of the inlay whatever the field was set to.
        class ListTitle: ACME_VentText { idc = 87780; text=""; x=0.4;y=0.4;w=0.2;h=0.02; colorText[]={0.05,0.05,0.05,1}; colorBackground[]={0,0,0,0}; style=0; sizeEx=0.023; };
        class ListRow0: ACME_VentBtn { idc = 87781; style=2; text=""; x=0.4;y=0.4;w=0.2;h=0.03; colorBackground[]={0,0,0,0}; colorText[]={0.92,0.92,0.92,1}; colorFocused[]={0,0,0,0}; colorBackgroundDisabled[]={0,0,0,0}; colorDisabled[]={0.92,0.92,0.92,1}; };
        class ListRow1: ACME_VentBtn { idc = 87782; style=2; text=""; x=0.4;y=0.4;w=0.2;h=0.03; colorBackground[]={0,0,0,0}; colorText[]={0.92,0.92,0.92,1}; colorFocused[]={0,0,0,0}; colorBackgroundDisabled[]={0,0,0,0}; colorDisabled[]={0.92,0.92,0.92,1}; };
        class ListRow2: ACME_VentBtn { idc = 87783; style=2; text=""; x=0.4;y=0.4;w=0.2;h=0.03; colorBackground[]={0,0,0,0}; colorText[]={0.92,0.92,0.92,1}; colorFocused[]={0,0,0,0}; colorBackgroundDisabled[]={0,0,0,0}; colorDisabled[]={0.92,0.92,0.92,1}; };
        class ListRow3: ACME_VentBtn { idc = 87784; style=2; text=""; x=0.4;y=0.4;w=0.2;h=0.03; colorBackground[]={0,0,0,0}; colorText[]={0.92,0.92,0.92,1}; colorFocused[]={0,0,0,0}; colorBackgroundDisabled[]={0,0,0,0}; colorDisabled[]={0.92,0.92,0.92,1}; };
        class ListRow4: ACME_VentBtn { idc = 87785; style=2; text=""; x=0.4;y=0.4;w=0.2;h=0.03; colorBackground[]={0,0,0,0}; colorText[]={0.92,0.92,0.92,1}; colorFocused[]={0,0,0,0}; colorBackgroundDisabled[]={0,0,0,0}; colorDisabled[]={0.92,0.92,0.92,1}; };
        class ListRow5: ACME_VentBtn { idc = 87786; style=2; text=""; x=0.4;y=0.4;w=0.2;h=0.03; colorBackground[]={0,0,0,0}; colorText[]={0.92,0.92,0.92,1}; colorFocused[]={0,0,0,0}; colorBackgroundDisabled[]={0,0,0,0}; colorDisabled[]={0.92,0.92,0.92,1}; };
        class ListPrompt: ACME_VentStructuredText { idc = 87787; text=""; x=0.4;y=0.4;w=0.2;h=0.06; size=0.022; class Attributes { align="center"; color="#EAEAEA"; }; };
        // nav strip on the bottom bar of the list screen.
        class HlNavConfirm: ACME_VentText { idc = 87754; text=""; x=0.4;y=0.4;w=0.03;h=0.03; colorBackground[]={0,0,0,0}; };
        class NavConfirm: ACME_VentBtn { idc = 87790; text=""; x=0.4;y=0.4;w=0.04;h=0.03; colorBackground[]={0,0,0,0}; colorFocused[]={0,0,0,0}; action=""; };
        class IcoNavConfirm: RscPicture { idc = 87791; text="\acm_extended\ui\vent\confirm_ca.paa"; x=0.4;y=0.4;w=0.03;h=0.03; colorText[]={0.10,0.10,0.10,1}; };
        class HlNavHome: ACME_VentText { idc = 87755; text=""; x=0.4;y=0.4;w=0.03;h=0.03; colorBackground[]={0,0,0,0}; };
        class NavHome: ACME_VentBtn { idc = 87792; text=""; x=0.4;y=0.4;w=0.04;h=0.03; colorBackground[]={0,0,0,0}; colorFocused[]={0,0,0,0}; action=""; };
        class IcoNavHome: RscPicture { idc = 87793; text="\acm_extended\ui\vent\home_ca.paa"; x=0.4;y=0.4;w=0.03;h=0.03; colorText[]={0.10,0.10,0.10,1}; };
        class HlNavBack: ACME_VentText { idc = 87756; text=""; x=0.4;y=0.4;w=0.03;h=0.03; colorBackground[]={0,0,0,0}; };
        class NavBack: ACME_VentBtn { idc = 87794; text=""; x=0.4;y=0.4;w=0.04;h=0.03; colorBackground[]={0,0,0,0}; colorFocused[]={0,0,0,0}; action=""; };
        class IcoNavBack: RscPicture { idc = 87795; text="\acm_extended\ui\vent\back_ca.paa"; x=0.4;y=0.4;w=0.03;h=0.03; colorText[]={0.10,0.10,0.10,1}; };
        class HlNavNext: ACME_VentText { idc = 87757; text=""; x=0.4;y=0.4;w=0.03;h=0.03; colorBackground[]={0,0,0,0}; };
        class NavNext: ACME_VentBtn { idc = 87796; text=""; x=0.4;y=0.4;w=0.04;h=0.03; colorBackground[]={0,0,0,0}; colorFocused[]={0,0,0,0}; action=""; };
        class IcoNavNext: RscPicture { idc = 87797; text="\acm_extended\ui\vent\next_screen_ca.paa"; x=0.4;y=0.4;w=0.03;h=0.03; colorText[]={0.10,0.10,0.10,1}; };
        // graph screen. it has a title, a black plot field, and a strip of vertical bars drawn as the waveform, up to
        // 40 slices. the knob switches between PRESSURE and FLOW. it is cosmetic and the tick animates it.
        // style 0 is left, matching ListTitle. it was style 2, so PRESSURE and FLOW rendered centerd in the same field
        // every other title is left aligned in, which is why they sat noticeably right of the rest.
        class GraphTitle: ACME_VentText { idc = 87800; text="PRESSURE"; x=0.4;y=0.4;w=0.2;h=0.02; colorText[]={0.05,0.05,0.05,1}; colorBackground[]={0,0,0,0}; style=0; sizeEx=0.02; };
        class GraphField: ACME_VentText { idc = 87801; x=0.4;y=0.4;w=0.2;h=0.1; colorBackground[]={0.02,0.03,0.05,1}; };
        class GraphAxis: ACME_VentText { idc = 87802; x=0.4;y=0.4;w=0.2;h=0.001; colorBackground[]={0.35,0.38,0.42,1}; };  // zero line.
        class BtnClose: RscButton { shadow = 0; idc = 87775; text="Close"; x="safezoneX + safezoneW - 0.12"; y="safezoneY + 0.02"; w=0.10; h=0.035; colorBackground[]={0.15,0.15,0.15,0.9}; colorBackgroundActive[]={0.15,0.15,0.15,0.9}; colorFocused[]={0.15,0.15,0.15,0.9}; soundEnter[]={"",0,1}; soundPush[]={"",0,1}; soundClick[]={"",0,1}; soundEscape[]={"",0,1}; action="closeDialog 0"; };
    };
};

// laryngoscopy intubation mini-game, idd 87800.
// this is direct-vision orotracheal intubation, in the style of the iv and chest-seal engines. the airway view
// is a composited scene from the laryngoscopy art bundle, with the cords by cormack-lehane, the tongue by
// mallampati, and the blade and tube as fixed overlays. the tongue depresses through a five-state flipbook as
// the medic lifts.
// it is tray-based. grab the laryngoscope from the tray, click the airway to seat the blade, then hold lmb and
// pull up to open the airway. at full open it locks with the cords in view. grab the et tube and click the
// middle of the cords to pass it. on target the airway is secured, and off target the tube goes toward the
// esophagus and fails. the engine is in fn_laryngo*.
class ACME_Laryngoscopy_Dialog {
    idd = 87800;
    movingEnable = 0;
    onLoad = "[_this select 0] call ACME_fnc_minigameInputInstall; _this call ACME_fnc_laryngoInit";
    onUnload = "[] call ACME_fnc_laryngoClose";
    class ControlsBackground {
        class LG_Dim: RscText {
            idc = -1;
            x = "safezoneX"; y = "safezoneY"; w = "safezoneW"; h = "safezoneH";
            colorBackground[] = {0,0,0,0.72};
        };
        // layered airway scene. these are full-canvas rgba layers from the laryngoscopy art bundle, all pinned to the
        // same square rect, because the registration matches, with keepaspect so nothing distorts on ultrawide. the
        // cords, tongue, blade and tube textures are set per mallampati and cormack-lehane grade at init, and the
        // defaults below only keep the controls valid before onload runs.
        // the draw order, back to front, is: cl pharynx, cl larynx, shared palate, shared cavity, shared teeth, shared
        // lips, blade master + fulcrum frames, tube stages, then the Mallampati tongue
        // flipbook, five states from rest to s4 driven by lift, last and therefore on top.
        // this departs from the bundle manifest, which puts both instruments in front of everything. here the
        // instruments sit directly under the tongue and over the teeth and lips, so the blade and the tube visibly
        // pass behind the tongue as it is depressed while the shaft still draws across the incisors. that is what
        // makes blade-on-teeth contact readable. to revert, move the five tongue controls, 87801, 87851, 87852 and
        // 87853, back to immediately after LG_Cavity.
        // the tongue flipbook has five states, rest and s1 to s4, of the selected mallampati tongue. fn_laryngoframes
        // cross-fades them as the lift ramps, and the textures are set per mallampati grade at init. these five
        // controls were the old m1_x mouth flipbook and now carry the tongue layer.
        // the shared teeth and then the lips are drawn over the tongue.
        // the laryngoscope blade overlay uses the master view plus the five active fulcrum frames.
        // the blade light glow is a separate layer over the blade.
        // the et tube has eight insertion stages, f1 entering to f8 seated, as stacked layers. fn_laryngotubeframes
        // crossfades them by push depth as the medic clicks and drags the tube in. all start hidden.
        class LG_Pharynx: RscPictureKeepAspect {
            idc = 87803;
            x = 0.35; y = 0.10; w = 0.30; h = 0.60;
            text = "\acm_extended\ui\laryngo\cl1_pharynx.paa";
            colorText[] = {1,1,1,1};
        };
        class LG_Larynx: RscPictureKeepAspect {
            idc = 87804;
            x = 0.35; y = 0.10; w = 0.30; h = 0.60;
            text = "\acm_extended\ui\laryngo\cl1_larynx.paa";
            colorText[] = {1,1,1,1};
        };
        class LG_Palate: RscPictureKeepAspect {
            idc = 87805;
            x = 0.35; y = 0.10; w = 0.30; h = 0.60;
            text = "\acm_extended\ui\laryngo\sh_palate.paa";
            colorText[] = {1,1,1,1};
        };
        class LG_Cavity: RscPictureKeepAspect {
            idc = 87806;
            x = 0.35; y = 0.10; w = 0.30; h = 0.60;
            text = "\acm_extended\ui\laryngo\sh_cavity.paa";
            colorText[] = {1,1,1,1};
        };
        class LG_Teeth: RscPictureKeepAspect {
            idc = 87807;
            x = 0.35; y = 0.10; w = 0.30; h = 0.60;
            text = "\acm_extended\ui\laryngo\sh_teeth.paa";
            colorText[] = {1,1,1,1};
        };
        class LG_TeethBroken: RscPictureKeepAspect {
            idc = 87878;
            x = 0.35; y = 0.10; w = 0.30; h = 0.60;
            text = "\acm_extended\ui\laryngo\sh_teeth_fractured.paa";
            colorText[] = {1,1,1,0};
        };
        class LG_Lips: RscPictureKeepAspect {
            idc = 87808;
            x = 0.35; y = 0.10; w = 0.30; h = 0.60;
            text = "\acm_extended\ui\laryngo\sh_lips.paa";
            colorText[] = {1,1,1,1};
        };
        class LG_Tube1: RscPictureKeepAspect {
            idc = 87900;
            x = 0.35; y = 0.10; w = 0.30; h = 0.60;
            text = "\acm_extended\ui\laryngo\ett_f1.paa";
            colorText[] = {1,1,1,0};
        };
        class LG_Tube2: RscPictureKeepAspect {
            idc = 87901;
            x = 0.35; y = 0.10; w = 0.30; h = 0.60;
            text = "\acm_extended\ui\laryngo\ett_f2.paa";
            colorText[] = {1,1,1,0};
        };
        class LG_Tube3: RscPictureKeepAspect {
            idc = 87902;
            x = 0.35; y = 0.10; w = 0.30; h = 0.60;
            text = "\acm_extended\ui\laryngo\ett_f3.paa";
            colorText[] = {1,1,1,0};
        };
        class LG_Tube4: RscPictureKeepAspect {
            idc = 87903;
            x = 0.35; y = 0.10; w = 0.30; h = 0.60;
            text = "\acm_extended\ui\laryngo\ett_f4.paa";
            colorText[] = {1,1,1,0};
        };
        class LG_Tube5: RscPictureKeepAspect {
            idc = 87904;
            x = 0.35; y = 0.10; w = 0.30; h = 0.60;
            text = "\acm_extended\ui\laryngo\ett_f5.paa";
            colorText[] = {1,1,1,0};
        };
        class LG_Tube6: RscPictureKeepAspect {
            idc = 87905;
            x = 0.35; y = 0.10; w = 0.30; h = 0.60;
            text = "\acm_extended\ui\laryngo\ett_f6.paa";
            colorText[] = {1,1,1,0};
        };
        class LG_Tube7: RscPictureKeepAspect {
            idc = 87906;
            x = 0.35; y = 0.10; w = 0.30; h = 0.60;
            text = "\acm_extended\ui\laryngo\ett_f7.paa";
            colorText[] = {1,1,1,0};
        };
        class LG_Tube8: RscPictureKeepAspect {
            idc = 87907;
            x = 0.35; y = 0.10; w = 0.30; h = 0.60;
            text = "\acm_extended\ui\laryngo\ett_f8.paa";
            colorText[] = {1,1,1,0};
        };
        class LG_TubeBlocked: RscPictureKeepAspect {
            idc = 87908;
            x = 0.35; y = 0.10; w = 0.30; h = 0.60;
            text = "\acm_extended\ui\laryngo\ett_blocked.paa";
            colorText[] = {1,1,1,0};
        };
        class LG_FrameA: RscPictureKeepAspect {
            idc = 87801;
            x = 0.35; y = 0.10; w = 0.30; h = 0.60;
            text = "\acm_extended\ui\laryngo\tongue_mp1_1.paa";
            colorText[] = {1,1,1,1};
        };
        class LG_Frame2: RscPictureKeepAspect {
            idc = 87851;
            x = 0.35; y = 0.10; w = 0.30; h = 0.60;
            text = "\acm_extended\ui\laryngo\tongue_mp1_1.paa";
            colorText[] = {1,1,1,0};
        };
        class LG_Frame3: RscPictureKeepAspect {
            idc = 87852;
            x = 0.35; y = 0.10; w = 0.30; h = 0.60;
            text = "\acm_extended\ui\laryngo\tongue_mp1_2.paa";
            colorText[] = {1,1,1,0};
        };
        class LG_Frame4: RscPictureKeepAspect {
            idc = 87853;
            x = 0.35; y = 0.10; w = 0.30; h = 0.60;
            text = "\acm_extended\ui\laryngo\tongue_mp1_3.paa";
            colorText[] = {1,1,1,0};
        };
        class LG_Fluid: RscPictureKeepAspect {
            idc = 87915;
            x = 0.35; y = 0.10; w = 0.30; h = 0.60;
            text = "";
            colorText[] = {1,1,1,0};
        };
        // fractured teeth. they swap in for the intact ones once the blade has broken something, so the damage stays
        // visible for the rest of the attempt instead of being a number in a log.
        // airway fluid: vomitus, secretions or blood. it is one control whose texture is swapped per frame. the art is
        // 11 fill stages by 4 percolation phases per fluid, and holding 132 controls open would be absurd. it is drawn
        // above the tongue so it fills the mouth, and below the instruments so they stay readable through it.
        class LG_Blade: RscPictureKeepAspect {
            idc = 87802;
            x = 0.35; y = 0.10; w = 0.30; h = 0.60;
            text = "\acm_extended\ui\laryngo\blade_master.paa";
            colorText[] = {1,1,1,0};
        };
        class LG_BladeFulc1: RscPictureKeepAspect {
            idc = 87811;
            x = 0.35; y = 0.10; w = 0.30; h = 0.60;
            text = "\acm_extended\ui\laryngo\blade_fulc_1.paa";
            colorText[] = {1,1,1,0};
        };
        class LG_BladeFulc2: RscPictureKeepAspect {
            idc = 87812;
            x = 0.35; y = 0.10; w = 0.30; h = 0.60;
            text = "\acm_extended\ui\laryngo\blade_fulc_2.paa";
            colorText[] = {1,1,1,0};
        };
        class LG_BladeFulc3: RscPictureKeepAspect {
            idc = 87911;
            x = 0.35; y = 0.10; w = 0.30; h = 0.60;
            text = "\acm_extended\ui\laryngo\blade_fulc_3.paa";
            colorText[] = {1,1,1,0};
        };
        class LG_BladeFulc4: RscPictureKeepAspect {
            idc = 87912;
            x = 0.35; y = 0.10; w = 0.30; h = 0.60;
            text = "\acm_extended\ui\laryngo\blade_fulc_4.paa";
            colorText[] = {1,1,1,0};
        };
        class LG_BladeFulc5: RscPictureKeepAspect {
            idc = 87913;
            x = 0.35; y = 0.10; w = 0.30; h = 0.60;
            text = "\acm_extended\ui\laryngo\blade_fulc_5.paa";
            colorText[] = {1,1,1,0};
        };
        class LG_Light: RscPictureKeepAspect {
            idc = 87809;
            x = 0.35; y = 0.10; w = 0.30; h = 0.60;
            text = "";
            colorText[] = {1,1,1,0};
        };
        // tube-securing collar. f1 is the loose collar the medic positions and f2 is it fastened. it sits with the
        // instruments, above the tongue.
        class LG_Collar: RscPictureKeepAspect {
            idc = 87909;
            x = 0.35; y = 0.10; w = 0.30; h = 0.60;
            text = "\acm_extended\ui\laryngo\ett_secured_f1.paa";
            colorText[] = {1,1,1,0};
        };
        class LG_CollarSet: RscPictureKeepAspect {
            idc = 87910;
            x = 0.35; y = 0.10; w = 0.30; h = 0.60;
            text = "\acm_extended\ui\laryngo\ett_secured_f2.paa";
            colorText[] = {1,1,1,0};
        };
        // B39 cuff inflation uses ACM's real 10 mL Narc Box syringe layers. The plunger layer moves
        // independently while the backbit/barrel remain fixed, so hold-to-inflate visibly drives to 0 mL.
        class LG_Syringe: RscPicture {
            idc = 87814;
            x = 0.35; y = 0.10; w = 0.30; h = 0.30;
            text = "\x\ACM\addons\circulation\ui\syringe\syringe_10_backbit_ca.paa";
            colorText[] = {1,1,1,0};
        };
        class LG_SyringePlunger: LG_Syringe {
            idc = 87817;
            text = "\x\ACM\addons\circulation\ui\syringe\syringe_10_plunger_ca.paa";
        };
        class LG_SyringeBarrel: LG_Syringe {
            idc = 87818;
            text = "\acm_extended\ui\syringe\syringe_flush_10_barrel_ca.paa";
        };
        // yankauer. its canvas is 2048 by 4096, so unlike everything else here it is a 1:2 sprite, and the control has
        // to be twice as tall as it is wide or keepaspect letterboxes it down to half size. it is positioned and sized
        // entirely at runtime, and these numbers only keep the control valid before onload.
        class LG_Suction: RscPictureKeepAspect {
            idc = 87916;
            x = 0.40; y = 0.05; w = 0.20; h = 0.80;
            text = "\acm_extended\ui\laryngo\suction\yank_master.paa";
            colorText[] = {1,1,1,0};
        };
    };
    class Controls {
        class LG_Title: RscText {
            idc = -1;
            style = 2;
            x = "safezoneX"; y = "safezoneY + safezoneH * 0.035"; w = "safezoneW"; h = "safezoneH * 0.05";
            text = "";
            colorText[] = {0.93,0.89,0.80,1};
            colorBackground[] = {0,0,0,0};
            sizeEx = "0.042 * safezoneH";
        };
        class LG_Instruction: RscText {
            idc = 87810;
            style = 2;
            x = "safezoneX"; y = "safezoneY + safezoneH * 0.09"; w = "safezoneW"; h = "safezoneH * 0.04";
            text = "";
            colorText[] = {0.82,0.82,0.82,1};
            colorBackground[] = {0,0,0,0};
            sizeEx = "0.026 * safezoneH";
        };
        // success banner. it is held for a beat after the cuff is up, then the dialog closes itself.
        class LG_Success: RscText {
            idc = 87816;
            style = 2;
            x = "safezoneX"; y = "safezoneY + safezoneH * 0.42"; w = "safezoneW"; h = "safezoneH * 0.09";
            text = "";
            colorText[] = {0.55,0.92,0.60,1};
            colorBackground[] = {0,0,0,0};
            sizeEx = "0.055 * safezoneH";
        };
        // interaction surface over the airway view. it is a controls-group, so it receives mouse events, and its
        // MouseMoving and MouseButtonDown handlers report the cursor in dialog ui coords, which is ultrawide-safe. the
        // blade placement, the pull-up-to-open drag and the cords click are all read from this surface. it is
        // positioned to the airway rect at init.
        class LG_Surface: RscControlsGroupNoScrollbars {
            idc = 87830;
            x = 0.35; y = 0.10; w = 0.30; h = 0.60;
            colorBackground[] = {0,0,0,0};
            class Controls {};
        };
        // laryngoscope tray slot, in the chest-seal and cric pattern: a black box, an icon, a count and a transparent
        // click target.
        class LG_ScopeBG: RscText {
            idc = 87860;
            x = "safezoneX + safezoneW * 0.82"; y = "safezoneY + safezoneH * 0.30";
            w = "safezoneW * 0.08"; h = "safezoneH * 0.16";
            colorBackground[] = {0,0,0,0.85};
        };
        class LG_ScopeLogo: RscPictureKeepAspect {
            idc = 87861;
            x = "safezoneX + safezoneW * 0.826"; y = "safezoneY + safezoneH * 0.31";
            w = "safezoneW * 0.068"; h = "safezoneH * 0.12";
            text = "\acm_extended\ui\vent\laryngoscope_ca.paa";
        };
        class LG_ScopeCount: RscText {
            idc = 87862;
            x = "safezoneX + safezoneW * 0.82"; y = "safezoneY + safezoneH * 0.445";
            w = "safezoneW * 0.08"; h = "safezoneH * 0.03";
            style = 2; text = "";
            colorText[] = {0.93,0.89,0.80,1}; colorBackground[] = {0,0,0,0};
            sizeEx = "0.022 * safezoneH";
        };
        class LG_ScopeClick: RscButton {
            idc = 87863;
            x = "safezoneX + safezoneW * 0.82"; y = "safezoneY + safezoneH * 0.30";
            w = "safezoneW * 0.08"; h = "safezoneH * 0.16";
            text = ""; tooltip = "Pick up / return laryngoscope";
            onButtonClick = "['scope'] call ACME_fnc_laryngoGrab";
            colorText[]={0,0,0,0}; colorDisabled[]={0,0,0,0}; colorBackground[]={0,0,0,0};
            colorBackgroundDisabled[]={0,0,0,0}; colorBackgroundActive[]={1,1,1,0.04};
            colorFocused[]={0,0,0,0}; colorShadow[]={0,0,0,0}; colorBorder[]={0,0,0,0}; borderSize=0;
        };
        // et tube tray slot.
        class LG_TubeBG: RscText {
            idc = 87864;
            x = "safezoneX + safezoneW * 0.82"; y = "safezoneY + safezoneH * 0.50";
            w = "safezoneW * 0.08"; h = "safezoneH * 0.16";
            colorBackground[] = {0,0,0,0.85};
        };
        class LG_TubeLogo: RscPictureKeepAspect {
            idc = 87865;
            x = "safezoneX + safezoneW * 0.826"; y = "safezoneY + safezoneH * 0.51";
            w = "safezoneW * 0.068"; h = "safezoneH * 0.12";
            text = "\acm_extended\ui\vent\et_tube_ca.paa";
        };
        class LG_TubeCount: RscText {
            idc = 87866;
            x = "safezoneX + safezoneW * 0.82"; y = "safezoneY + safezoneH * 0.645";
            w = "safezoneW * 0.08"; h = "safezoneH * 0.03";
            style = 2; text = "";
            colorText[] = {0.93,0.89,0.80,1}; colorBackground[] = {0,0,0,0};
            sizeEx = "0.022 * safezoneH";
        };
        class LG_TubeClick: RscButton {
            idc = 87867;
            x = "safezoneX + safezoneW * 0.82"; y = "safezoneY + safezoneH * 0.50";
            w = "safezoneW * 0.08"; h = "safezoneH * 0.16";
            text = ""; tooltip = "Pick up / return ET tube";
            onButtonClick = "['tube'] call ACME_fnc_laryngoGrab";
            colorText[]={0,0,0,0}; colorDisabled[]={0,0,0,0}; colorBackground[]={0,0,0,0};
            colorBackgroundDisabled[]={0,0,0,0}; colorBackgroundActive[]={1,1,1,0.04};
            colorFocused[]={0,0,0,0}; colorShadow[]={0,0,0,0}; colorBorder[]={0,0,0,0}; borderSize=0;
        };
        // cuff syringe tray slot, using ACM's own 10 ml syringe icon.
        class LG_SyrBG: RscText {
            idc = 87870;
            x = "safezoneX + safezoneW * 0.82"; y = "safezoneY + safezoneH * 0.70";
            w = "safezoneW * 0.08"; h = "safezoneH * 0.16";
            colorBackground[] = {0,0,0,0.85};
        };
        class LG_SyrLogo: RscPictureKeepAspect {
            idc = 87871;
            x = "safezoneX + safezoneW * 0.826"; y = "safezoneY + safezoneH * 0.71";
            w = "safezoneW * 0.068"; h = "safezoneH * 0.12";
            text = "\acm_extended\ui\laryngo\active_syringe.paa";
        };
        class LG_SyrCount: RscText {
            idc = 87872;
            x = "safezoneX + safezoneW * 0.82"; y = "safezoneY + safezoneH * 0.845";
            w = "safezoneW * 0.08"; h = "safezoneH * 0.03";
            style = 2; text = "";
            colorText[] = {0.93,0.89,0.80,1}; colorBackground[] = {0,0,0,0};
            sizeEx = "0.022 * safezoneH";
        };
        class LG_SyrClick: RscButton {
            idc = 87873;
            x = "safezoneX + safezoneW * 0.82"; y = "safezoneY + safezoneH * 0.70";
            w = "safezoneW * 0.08"; h = "safezoneH * 0.16";
            text = ""; tooltip = "Pick up / return cuff syringe";
            onButtonClick = "['syringe'] call ACME_fnc_laryngoGrab";
            colorText[]={0,0,0,0}; colorDisabled[]={0,0,0,0}; colorBackground[]={0,0,0,0};
            colorBackgroundDisabled[]={0,0,0,0}; colorBackgroundActive[]={1,1,1,0.04};
            colorFocused[]={0,0,0,0}; colorShadow[]={0,0,0,0}; colorBorder[]={0,0,0,0}; borderSize=0;
        };
        // securing-collar tray slot.
        class LG_ColBG: RscText {
            idc = 87874;
            x = "safezoneX + safezoneW * 0.82"; y = "safezoneY + safezoneH * 0.86";
            w = "safezoneW * 0.08"; h = "safezoneH * 0.16";
            colorBackground[] = {0,0,0,0.85};
        };
        class LG_ColLogo: RscPictureKeepAspect {
            idc = 87875;
            x = "safezoneX + safezoneW * 0.826"; y = "safezoneY + safezoneH * 0.87";
            w = "safezoneW * 0.068"; h = "safezoneH * 0.12";
            text = "\acm_extended\ui\laryngo\ett_secured_f2.paa";
        };
        class LG_ColCount: RscText {
            idc = 87876;
            x = "safezoneX + safezoneW * 0.82"; y = "safezoneY + safezoneH * 0.99";
            w = "safezoneW * 0.08"; h = "safezoneH * 0.03";
            style = 2; text = "";
            colorText[] = {0.93,0.89,0.80,1}; colorBackground[] = {0,0,0,0};
            sizeEx = "0.022 * safezoneH";
        };
        class LG_ColClick: RscButton {
            idc = 87877;
            x = "safezoneX + safezoneW * 0.82"; y = "safezoneY + safezoneH * 0.86";
            w = "safezoneW * 0.08"; h = "safezoneH * 0.16";
            text = ""; tooltip = "Pick up / return securing collar";
            onButtonClick = "['collar'] call ACME_fnc_laryngoGrab";
            colorText[]={0,0,0,0}; colorDisabled[]={0,0,0,0}; colorBackground[]={0,0,0,0};
            colorBackgroundDisabled[]={0,0,0,0}; colorBackgroundActive[]={1,1,1,0.04};
            colorFocused[]={0,0,0,0}; colorShadow[]={0,0,0,0}; colorBorder[]={0,0,0,0}; borderSize=0;
        };
        // suction tray slot, for the yankauer.
        class LG_SucBG: RscText {
            idc = 87880;
            x = "safezoneX + safezoneW * 0.82"; y = "safezoneY + safezoneH * 0.86";
            w = "safezoneW * 0.08"; h = "safezoneH * 0.16";
            colorBackground[] = {0,0,0,0.85};
        };
        class LG_SucLogo: RscPictureKeepAspect {
            idc = 87881;
            x = "safezoneX + safezoneW * 0.826"; y = "safezoneY + safezoneH * 0.87";
            w = "safezoneW * 0.068"; h = "safezoneH * 0.12";
            text = "\acm_extended\ui\laryngo\suction\yank_master.paa";
        };
        class LG_SucCount: RscText {
            idc = 87882;
            x = "safezoneX + safezoneW * 0.82"; y = "safezoneY + safezoneH * 0.99";
            w = "safezoneW * 0.08"; h = "safezoneH * 0.03";
            style = 2; text = "";
            colorText[] = {0.93,0.89,0.80,1}; colorBackground[] = {0,0,0,0};
            sizeEx = "0.022 * safezoneH";
        };
        class LG_SucClick: RscButton {
            idc = 87883;
            x = "safezoneX + safezoneW * 0.82"; y = "safezoneY + safezoneH * 0.86";
            w = "safezoneW * 0.08"; h = "safezoneH * 0.16";
            text = ""; tooltip = "Pick up / return Yankauer suction";
            onButtonClick = "['suction'] call ACME_fnc_laryngoGrab";
            colorText[]={0,0,0,0}; colorDisabled[]={0,0,0,0}; colorBackground[]={0,0,0,0};
            colorBackgroundDisabled[]={0,0,0,0}; colorBackgroundActive[]={1,1,1,0.04};
            colorFocused[]={0,0,0,0}; colorShadow[]={0,0,0,0}; colorBorder[]={0,0,0,0}; borderSize=0;
        };
        class LG_Cancel: RscButton {
            idc = 87868;
            x = "safezoneX + safezoneW * 0.82"; y = "safezoneY + safezoneH * 0.82";
            w = "safezoneW * 0.08"; h = "safezoneH * 0.05";
            text = "Done";
            colorBackground[] = {0.30,0.10,0.10,0.85};
            colorText[] = {0.93,0.89,0.80,1};
            action = "closeDialog 0";
        };
    };
};

// megacode kelly, the instructor control panel.
// this is a lean static frame: a dark backdrop, a title, the black waveform field, and the main-menu button
// row. everything that animates, the four sweep traces, the big vitals readouts, and the sliders and buttons
// of each category, is built at runtime by ACME_fnc_megacodePanelLoad and _megacodemenu.
class ACME_MC_MenuBtn: RscButton {
    idc = -1;
    colorText[] = {0.92,0.95,1,1};
    colorDisabled[] = {1,1,1,0.25};
    colorBackground[] = {0.10,0.13,0.18,1};
    colorBackgroundDisabled[] = {0.06,0.07,0.09,1};
    colorBackgroundActive[] = {0.16,0.42,0.58,1};
    colorFocused[] = {0.12,0.16,0.22,1};
    colorBorder[] = {0,0,0,0};
    font = "PuristaBold";
    sizeEx = "safeZoneH * 0.022";
    style = 2;
    shadow = 0;
    y = "safeZoneY + safeZoneH*0.075 + safeZoneH*0.85*0.600";
    h = "safeZoneH * 0.045";
    w = "((safeZoneH*0.85*1.61) - 0.028)/9 - 0.004";
};

class ACME_Megacode_Panel {
    idd = 87300;
    movingEnable = 0;
    enableSimulation = 1;
    onLoad = "_this call ACME_fnc_megacodePanelLoad";
    onUnload = "_this call ACME_fnc_megacodeClosePanel";

    class ControlsBackground {
        class MC_Backdrop: RscText {
            idc = -1;
            text = "";
            x = "safeZoneX + (safeZoneW-(safeZoneH*0.85*1.61))/2";
            y = "safeZoneY + safeZoneH * 0.075";
            w = "(safeZoneH*0.85*1.61)";
            h = "safeZoneH * 0.85";
            colorBackground[] = {0.02,0.03,0.05,0.97};
        };
        class MC_TitleBar: RscText {
            idc = -1;
            text = "  MEGACODE KELLY   //   INSTRUCTOR CONTROL PANEL";
            x = "safeZoneX + (safeZoneW-(safeZoneH*0.85*1.61))/2";
            y = "safeZoneY + safeZoneH * 0.075";
            w = "(safeZoneH*0.85*1.61)";
            h = "safeZoneH * 0.045";
            colorBackground[] = {0.07,0.10,0.14,1};
            colorText[] = {0.50,0.85,1,1};
            sizeEx = "safeZoneH * 0.026";
            font = "PuristaBold";
        };
        class MC_WaveBG: RscText {
            idc = -1;
            text = "";
            x = "safeZoneX + (safeZoneW-(safeZoneH*0.85*1.61))/2 + 0.010";
            y = "safeZoneY + safeZoneH*0.075 + safeZoneH*0.050";
            w = "(safeZoneH*0.85*1.61)*0.605";
            h = "safeZoneH*0.85*0.50 + 0.004";
            colorBackground[] = {0,0,0,1};
        };
        class MC_VitalsBG: MC_WaveBG {
            x = "safeZoneX + (safeZoneW-(safeZoneH*0.85*1.61))/2 + (safeZoneH*0.85*1.61)*0.625 - 0.004";
            w = "(safeZoneH*0.85*1.61)*0.36";
            colorBackground[] = {0.015,0.02,0.03,1};
        };
        class MC_ContentBG: MC_WaveBG {
            x = "safeZoneX + (safeZoneW-(safeZoneH*0.85*1.61))/2 + 0.010";
            y = "safeZoneY + safeZoneH*0.075 + safeZoneH*0.85*0.655";
            w = "(safeZoneH*0.85*1.61) - 0.020";
            h = "safeZoneH*0.85*0.330";
            colorBackground[] = {0.04,0.05,0.07,1};
        };
    };

    class Controls {
        class MC_BtnVitals: ACME_MC_MenuBtn {
            text = "VITALS";
            x = "safeZoneX + (safeZoneW-(safeZoneH*0.85*1.61))/2 + 0.014 + ((safeZoneH*0.85*1.61) - 0.028)*(0/9)";
            action = "[87300, 'vitals'] call ACME_fnc_megacodeMenu";
            tooltip = "Heart rate, SpO2, BP, RR, EtCO2, temperature, pulse";
        };
        class MC_BtnRhythm: ACME_MC_MenuBtn {
            text = "RHYTHM";
            x = "safeZoneX + (safeZoneW-(safeZoneH*0.85*1.61))/2 + 0.014 + ((safeZoneH*0.85*1.61) - 0.028)*(1/9)";
            action = "[87300, 'rhythm'] call ACME_fnc_megacodeMenu";
            tooltip = "Cardiac rhythm library (sinus through asystole)";
        };
        class MC_BtnAirway: ACME_MC_MenuBtn {
            text = "AIRWAY";
            x = "safeZoneX + (safeZoneW-(safeZoneH*0.85*1.61))/2 + 0.014 + ((safeZoneH*0.85*1.61) - 0.028)*(2/9)";
            action = "[87300, 'airway'] call ACME_fnc_megacodeMenu";
            tooltip = "Airway / breathing states and tension pneumothorax";
        };
        class MC_BtnWounds: ACME_MC_MenuBtn {
            text = "WOUNDS";
            x = "safeZoneX + (safeZoneW-(safeZoneH*0.85*1.61))/2 + 0.014 + ((safeZoneH*0.85*1.61) - 0.028)*(3/9)";
            action = "[87300, 'wounds'] call ACME_fnc_megacodeMenu";
            tooltip = "Add wounds of any type to any region";
        };
        class MC_BtnNeuro: ACME_MC_MenuBtn {
            text = "NEURO/+";
            x = "safeZoneX + (safeZoneW-(safeZoneH*0.85*1.61))/2 + 0.014 + ((safeZoneH*0.85*1.61) - 0.028)*(4/9)";
            action = "[87300, 'neuro'] call ACME_fnc_megacodeMenu";
            tooltip = "ICP, GCS, herniation, seizure, posturing, pupils";
        };
        class MC_BtnScenario: ACME_MC_MenuBtn {
            text = "SCENARIO";
            x = "safeZoneX + (safeZoneW-(safeZoneH*0.85*1.61))/2 + 0.014 + ((safeZoneH*0.85*1.61) - 0.028)*(5/9)";
            colorBackground[] = {0.20,0.12,0.28,1};
            action = "[87300, 'scenario'] call ACME_fnc_megacodeMenu";
            tooltip = "Run an evolving clinical scenario that deteriorates toward arrest";
        };
        class MC_BtnLog: ACME_MC_MenuBtn {
            text = "LOG";
            x = "safeZoneX + (safeZoneW-(safeZoneH*0.85*1.61))/2 + 0.014 + ((safeZoneH*0.85*1.61) - 0.028)*(6/9)";
            colorBackground[] = {0.10,0.20,0.16,1};
            action = "[87300, 'log'] call ACME_fnc_megacodeMenu";
            tooltip = "Activity log of everything applied to the manikin";
        };
        class MC_BtnReset: ACME_MC_MenuBtn {
            text = "RESET";
            x = "safeZoneX + (safeZoneW-(safeZoneH*0.85*1.61))/2 + 0.014 + ((safeZoneH*0.85*1.61) - 0.028)*(7/9)";
            colorBackground[] = {0.35,0.20,0.10,1};
            action = "call ACME_fnc_megacodeReset";
            tooltip = "Reset the manikin to a clean baseline";
        };
        class MC_BtnDone: ACME_MC_MenuBtn {
            text = "DONE";
            x = "safeZoneX + (safeZoneW-(safeZoneH*0.85*1.61))/2 + 0.014 + ((safeZoneH*0.85*1.61) - 0.028)*(8/9)";
            colorBackground[] = {0.30,0.10,0.12,1};
            action = "closeDialog 0";
            tooltip = "Close the control panel";
        };
    };
};

// megacode laptop cable tuner. it has live sliders for the cable attach points, the laptop rotation and the
// rope slack. ACME_fnc_megacodeCableTunerLoad builds every control, the sliders and the close button, at
// runtime.
class ACME_MC_CableTuner {
    idd = 87310;
    movingEnable = 0;
    enableSimulation = 1;
    onLoad = "_this call ACME_fnc_megacodeCableTunerLoad";
    class ControlsBackground {
        class CT_Backdrop: RscText {
            idc = -1;
            text = "";
            x = "safeZoneX + safeZoneW * 0.05";
            y = "safeZoneY + safeZoneH * 0.685";
            w = "safeZoneW * 0.90";
            h = "safeZoneH * 0.300";
            colorBackground[] = {0.02,0.03,0.05,0.97};
        };
        class CT_TitleBar: RscText {
            idc = -1;
            text = "  MEGACODE CABLE TUNER";
            x = "safeZoneX + safeZoneW * 0.05";
            y = "safeZoneY + safeZoneH * 0.685";
            w = "safeZoneW * 0.90";
            h = "safeZoneH * 0.034";
            colorBackground[] = {0.07,0.10,0.14,1};
            colorText[] = {0.50,0.85,1,1};
            sizeEx = "safeZoneH * 0.024";
            font = "PuristaBold";
        };
    };
    class Controls {};
};

// cooler manager dialog.
// a double-click on a blood cooler in the inventory opens this. the left list is the units currently inside the
// cooler, which are cold, and the right list is the blood bags loose in your inventory. load moves a loose bag
// in and it goes cold. unload moves a unit out and it starts warming. the open function stashes the cooler
// class being managed in uinamespace ACME_CLR_Class.
class ACME_CoolerManager_Dialog {
    idd = 87400;
    movingEnable = 0;
    enableSimulation = 1;
    onLoad = "[_this select 0] call ACME_fnc_minigameInputInstall; uiNamespace setVariable ['ACME_CLR_DLG', (_this select 0)]; call ACME_fnc_coolerRefresh; [{ if (!isNull (uiNamespace getVariable ['ACME_CLR_DLG', displayNull])) then { call ACME_fnc_coolerRefresh; }; }, []] call CBA_fnc_execNextFrame;";
    onUnload = "uiNamespace setVariable ['ACME_CLR_DLG', displayNull]; call ACME_fnc_coolerClearSlots;";
    class ControlsBackground {
        class ACME_CLR_Backdrop: RscText {
            idc = 87401;
            text = "";
            x = "safeZoneX + (safeZoneW / 2) - (safeZoneW / 5)";
            y = "safeZoneY + (safeZoneH / 2) - (safeZoneH / 2.9)";
            w = "safeZoneW / 2.5";
            h = "safeZoneH / 1.55";
            colorBackground[] = {0.04,0.06,0.09,0.94};
        };
        // thin red rule under the header. it is the field-kit identity bar.
        class ACME_CLR_HeaderRule: RscText {
            idc = 87420;
            text = "";
            x = "safeZoneX + (safeZoneW / 2) - (safeZoneW / 5)";
            y = "safeZoneY + (safeZoneH / 2) - (safeZoneH / 2.9) + (safeZoneH / 13)";
            w = "safeZoneW / 2.5";
            h = "safeZoneH / 240";
            colorBackground[] = {0.74,0.12,0.12,1};
        };
        class ACME_CLR_Title: RscText {
            idc = 87402;
            text = "Blood Cooler";
            x = "safeZoneX + (safeZoneW / 2) - (safeZoneW / 5) + (safeZoneW / 90)";
            y = "safeZoneY + (safeZoneH / 2) - (safeZoneH / 2.9) + (safeZoneH / 90)";
            w = "safeZoneW / 3";
            h = "safeZoneH / 22";
            colorText[] = {0.92,0.24,0.24,1};
            colorBackground[] = {0,0,0,0};
            font = "PuristaBold";
            sizeEx = "safeZoneH * 0.032";
            style = 0;
            shadow = 0;
        };
        // capacity badge, top right, such as "x2 UNITS", so the carry count reads at a glance even before the slots
        // draw.
        class ACME_CLR_CapBadge: RscText {
            idc = 87421;
            text = "";
            x = "safeZoneX + (safeZoneW / 2) + (safeZoneW / 5) - (safeZoneW / 6.5) - (safeZoneW / 90)";
            y = "safeZoneY + (safeZoneH / 2) - (safeZoneH / 2.9) + (safeZoneH / 120)";
            w = "safeZoneW / 6.5";
            h = "safeZoneH / 20";
            colorText[] = {0.55,0.88,1,1};
            colorBackground[] = {0.07,0.13,0.18,0.85};
            font = "PuristaBold";
            sizeEx = "safeZoneH * 0.026";
            style = 2;
            shadow = 0;
        };
        class ACME_CLR_Readout: RscText {
            idc = 87403;
            text = "";
            x = "safeZoneX + (safeZoneW / 2) - (safeZoneW / 5) + (safeZoneW / 90)";
            y = "safeZoneY + (safeZoneH / 2) - (safeZoneH / 2.9) + (safeZoneH / 11.5)";
            w = "safeZoneW / 2.5";
            h = "safeZoneH / 30";
            colorText[] = {0.70,0.80,0.90,1};
            colorBackground[] = {0,0,0,0};
            font = "RobotoCondensed";
            sizeEx = "safeZoneH * 0.022";
            style = 0;
            shadow = 0;
        };
        // label over the slot bay grid, in the left column.
        class ACME_CLR_LabelIn: RscText {
            idc = 87404;
            text = "COOLER BAYS";
            x = "safeZoneX + (safeZoneW * 0.312)";
            y = "safeZoneY + (safeZoneH / 2) - (safeZoneH / 4.1)";
            w = "safeZoneW * 0.2016";
            h = "safeZoneH / 30";
            colorText[] = {0.50,0.85,1,1};
            colorBackground[] = {0,0,0,0};
            font = "PuristaBold";
            sizeEx = "safeZoneH * 0.021";
            shadow = 0;
        };
        class ACME_CLR_LabelOut: RscText {
            idc = 87405;
            text = "INVENTORY (warming)";
            x = "safeZoneX + (safeZoneW * 0.53)";
            y = "safeZoneY + (safeZoneH / 2) - (safeZoneH / 4.1)";
            w = "safeZoneW * 0.158";
            h = "safeZoneH / 30";
            colorText[] = {0.90,0.70,0.40,1};
            colorBackground[] = {0,0,0,0};
            font = "PuristaBold";
            sizeEx = "safeZoneH * 0.021";
            shadow = 0;
        };
    };
    class Controls {
        // fn_coolerrefresh builds the slot bay grid at runtime into this group, with the count set to the cooler
        // capacity, so the panel always shows exactly as many bays as the cooler holds. 1u gives 1, 2u gives 2 and 4u
        // gives 4.
        class ACME_CLR_SlotGroup: RscControlsGroupNoScrollbars {
            idc = 87415;
            x = "safeZoneX + (safeZoneW * 0.312)";
            y = "safeZoneY + (safeZoneH / 2) - (safeZoneH / 4.7)";
            w = "safeZoneW * 0.2016";
            h = "safeZoneH / 2.4";
            class Controls {};
        };
        // kept, hidden and off-screen, so legacy code paths that still reference the old in-cooler list, idc 87410, do
        // not error. the visible representation is the slot grid above, and lbdata[idx] still mirrors the contents
        // order.
        class ACME_CLR_ListIn: RscListBox {
            idc = 87410;
            x = -1;
            y = -1;
            w = 0.001;
            h = 0.001;
            colorBackground[] = {0,0,0,0};
            sizeEx = "safeZoneH * 0.001";
            font = "RobotoCondensed";
        };
        class ACME_CLR_ListOut: RscListBox {
            idc = 87411;
            x = "safeZoneX + (safeZoneW * 0.53)";
            y = "safeZoneY + (safeZoneH / 2) - (safeZoneH / 4.7)";
            w = "safeZoneW * 0.158";
            h = "safeZoneH / 2.7";
            colorBackground[] = {0.02,0.04,0.07,0.9};
            sizeEx = "safeZoneH * 0.021";
            font = "RobotoCondensed";
        };
        class ACME_CLR_Unload: RscButton {
            idc = 87412;
            text = "Unload selected bay >";
            tooltip = "Take the selected unit out of the cooler (it starts warming).";
            action = "call ACME_fnc_coolerUnload;";
            x = "safeZoneX + (safeZoneW * 0.312)";
            y = "safeZoneY + (safeZoneH / 2) + (safeZoneH / 4.6)";
            w = "safeZoneW * 0.2016";
            h = "safeZoneH / 26";
            colorBackground[] = {0.16,0.20,0.24,1};
            colorText[] = {0.85,0.95,1,1};
            font = "RobotoCondensed";
            sizeEx = "safeZoneH * 0.021";
        };
        class ACME_CLR_Load: RscButton {
            idc = 87413;
            text = "< Load into cooler";
            tooltip = "Put the selected blood bag into the cooler (it stays cold).";
            action = "call ACME_fnc_coolerLoad;";
            x = "safeZoneX + (safeZoneW * 0.53)";
            y = "safeZoneY + (safeZoneH / 2) + (safeZoneH / 4.6)";
            w = "safeZoneW * 0.158";
            h = "safeZoneH / 26";
            colorBackground[] = {0.16,0.20,0.24,1};
            colorText[] = {0.85,0.95,1,1};
            font = "RobotoCondensed";
            sizeEx = "safeZoneH * 0.021";
        };
        class ACME_CLR_Close: RscButton {
            idc = 87414;
            text = "Close";
            action = "closeDialog 0;";
            x = "safeZoneX + (safeZoneW / 2) - (safeZoneW / 5)";
            y = "safeZoneY + (safeZoneH / 2) + (safeZoneH / 2.9) - (safeZoneH / 22)";
            w = "safeZoneW / 2.5";
            h = "safeZoneH / 24";
            colorBackground[] = {0.45,0.12,0.12,1};
            colorText[] = {1,1,1,1};
            font = "PuristaBold";
            sizeEx = "safeZoneH * 0.024";
            style = 2;
        };
    };
};


class CfgSounds {

    class ACME_VentBoot {
        name = "ACME_VentBoot";
        sound[] = {"acm_extended\sound\vent_boot_sfx.ogg", 1.0, 1};
        titles[] = {};
    };
    class ACME_VentDial {
        name = "ACME_VentDial";
        sound[] = {"acm_extended\sound\vent_rotary_dial_sfx.ogg", 1.0, 1};
        titles[] = {};
    };
    class ACME_VentClick {
        name = "ACME_VentClick";
        sound[] = {"acm_extended\sound\vent_rotary_dial_click_sfx.ogg", 1.0, 1};
        titles[] = {};
    };
    class ACME_VentPower {
        name = "ACME_VentPower";
        sound[] = {"acm_extended\sound\vent_power_btn_sfx.ogg", 1.0, 1};
        titles[] = {};
    };
    // 4.375 s. the swap banner is held for exactly this long, so the battery lands the moment the sound ends.
    class ACME_VentBattSwap {
        name = "ACME_VentBattSwap";
        sound[] = {"acm_extended\sound\vent_battery_swap_sfx.ogg", 1.0, 1};
        titles[] = {};
    };
    // kelly clamp thoracostomy sfx. a random cut plays on each accepted left-click, and the close plays on
    // release.
    class ACME_KellyCut_1 {
        name = "ACME_KellyCut_1";
        sound[] = {"acm_extended\sound\kelly_clamps_cut1_sfx.ogg", 1.0, 1};
        titles[] = {};
    };
    class ACME_KellyCut_2: ACME_KellyCut_1 {
        name = "ACME_KellyCut_2";
        sound[] = {"acm_extended\sound\kelly_clamps_cut2_sfx.ogg", 1.0, 1};
    };
    class ACME_KellyCut_3: ACME_KellyCut_1 {
        name = "ACME_KellyCut_3";
        sound[] = {"acm_extended\sound\kelly_clamps_cut3_sfx.ogg", 1.0, 1};
    };
    class ACME_KellyCut_4: ACME_KellyCut_1 {
        name = "ACME_KellyCut_4";
        sound[] = {"acm_extended\sound\kelly_clamps_cut4_sfx.ogg", 1.0, 1};
    };
    class ACME_KellyClose: ACME_KellyCut_1 {
        name = "ACME_KellyClose";
        sound[] = {"acm_extended\sound\kelly_clamps_close_sfx.ogg", 1.0, 1};
    };
    // patient respiration sfx. there are 3 depth tiers, shallow, medium and deep through gain, by 6 variants, for
    // inhale and exhale.
    class ACME_BreathIn_S_1 {
        name = "ACME_BreathIn_S_1";
        sound[] = {"acm_extended\sound\breath_in_1_sfx.ogg", "db-9", 1, 18};
        titles[] = {};
    };
    class ACME_BreathIn_S_2: ACME_BreathIn_S_1 {
        name = "ACME_BreathIn_S_2";
        sound[] = {"acm_extended\sound\breath_in_2_sfx.ogg", "db-9", 1, 18};
    };
    class ACME_BreathIn_S_3: ACME_BreathIn_S_1 {
        name = "ACME_BreathIn_S_3";
        sound[] = {"acm_extended\sound\breath_in_3_sfx.ogg", "db-9", 1, 18};
    };
    class ACME_BreathIn_S_4: ACME_BreathIn_S_1 {
        name = "ACME_BreathIn_S_4";
        sound[] = {"acm_extended\sound\breath_in_4_sfx.ogg", "db-9", 1, 18};
    };
    class ACME_BreathIn_S_5: ACME_BreathIn_S_1 {
        name = "ACME_BreathIn_S_5";
        sound[] = {"acm_extended\sound\breath_in_5_sfx.ogg", "db-9", 1, 18};
    };
    class ACME_BreathIn_S_6: ACME_BreathIn_S_1 {
        name = "ACME_BreathIn_S_6";
        sound[] = {"acm_extended\sound\breath_in_6_sfx.ogg", "db-9", 1, 18};
    };
    class ACME_BreathIn_M_1: ACME_BreathIn_S_1 {
        name = "ACME_BreathIn_M_1";
        sound[] = {"acm_extended\sound\breath_in_1_sfx.ogg", "db-2", 1, 18};
    };
    class ACME_BreathIn_M_2: ACME_BreathIn_S_1 {
        name = "ACME_BreathIn_M_2";
        sound[] = {"acm_extended\sound\breath_in_2_sfx.ogg", "db-2", 1, 18};
    };
    class ACME_BreathIn_M_3: ACME_BreathIn_S_1 {
        name = "ACME_BreathIn_M_3";
        sound[] = {"acm_extended\sound\breath_in_3_sfx.ogg", "db-2", 1, 18};
    };
    class ACME_BreathIn_M_4: ACME_BreathIn_S_1 {
        name = "ACME_BreathIn_M_4";
        sound[] = {"acm_extended\sound\breath_in_4_sfx.ogg", "db-2", 1, 18};
    };
    class ACME_BreathIn_M_5: ACME_BreathIn_S_1 {
        name = "ACME_BreathIn_M_5";
        sound[] = {"acm_extended\sound\breath_in_5_sfx.ogg", "db-2", 1, 18};
    };
    class ACME_BreathIn_M_6: ACME_BreathIn_S_1 {
        name = "ACME_BreathIn_M_6";
        sound[] = {"acm_extended\sound\breath_in_6_sfx.ogg", "db-2", 1, 18};
    };
    class ACME_BreathIn_D_1: ACME_BreathIn_S_1 {
        name = "ACME_BreathIn_D_1";
        sound[] = {"acm_extended\sound\breath_in_1_sfx.ogg", "db+4", 1, 18};
    };
    class ACME_BreathIn_D_2: ACME_BreathIn_S_1 {
        name = "ACME_BreathIn_D_2";
        sound[] = {"acm_extended\sound\breath_in_2_sfx.ogg", "db+4", 1, 18};
    };
    class ACME_BreathIn_D_3: ACME_BreathIn_S_1 {
        name = "ACME_BreathIn_D_3";
        sound[] = {"acm_extended\sound\breath_in_3_sfx.ogg", "db+4", 1, 18};
    };
    class ACME_BreathIn_D_4: ACME_BreathIn_S_1 {
        name = "ACME_BreathIn_D_4";
        sound[] = {"acm_extended\sound\breath_in_4_sfx.ogg", "db+4", 1, 18};
    };
    class ACME_BreathIn_D_5: ACME_BreathIn_S_1 {
        name = "ACME_BreathIn_D_5";
        sound[] = {"acm_extended\sound\breath_in_5_sfx.ogg", "db+4", 1, 18};
    };
    class ACME_BreathIn_D_6: ACME_BreathIn_S_1 {
        name = "ACME_BreathIn_D_6";
        sound[] = {"acm_extended\sound\breath_in_6_sfx.ogg", "db+4", 1, 18};
    };
    class ACME_BreathOut_S_1: ACME_BreathIn_S_1 {
        name = "ACME_BreathOut_S_1";
        sound[] = {"acm_extended\sound\breath_out_1_sfx.ogg", "db-9", 1, 18};
    };
    class ACME_BreathOut_S_2: ACME_BreathIn_S_1 {
        name = "ACME_BreathOut_S_2";
        sound[] = {"acm_extended\sound\breath_out_2_sfx.ogg", "db-9", 1, 18};
    };
    class ACME_BreathOut_S_3: ACME_BreathIn_S_1 {
        name = "ACME_BreathOut_S_3";
        sound[] = {"acm_extended\sound\breath_out_3_sfx.ogg", "db-9", 1, 18};
    };
    class ACME_BreathOut_S_4: ACME_BreathIn_S_1 {
        name = "ACME_BreathOut_S_4";
        sound[] = {"acm_extended\sound\breath_out_4_sfx.ogg", "db-9", 1, 18};
    };
    class ACME_BreathOut_S_5: ACME_BreathIn_S_1 {
        name = "ACME_BreathOut_S_5";
        sound[] = {"acm_extended\sound\breath_out_5_sfx.ogg", "db-9", 1, 18};
    };
    class ACME_BreathOut_S_6: ACME_BreathIn_S_1 {
        name = "ACME_BreathOut_S_6";
        sound[] = {"acm_extended\sound\breath_out_6_sfx.ogg", "db-9", 1, 18};
    };
    class ACME_BreathOut_M_1: ACME_BreathIn_S_1 {
        name = "ACME_BreathOut_M_1";
        sound[] = {"acm_extended\sound\breath_out_1_sfx.ogg", "db-2", 1, 18};
    };
    class ACME_BreathOut_M_2: ACME_BreathIn_S_1 {
        name = "ACME_BreathOut_M_2";
        sound[] = {"acm_extended\sound\breath_out_2_sfx.ogg", "db-2", 1, 18};
    };
    class ACME_BreathOut_M_3: ACME_BreathIn_S_1 {
        name = "ACME_BreathOut_M_3";
        sound[] = {"acm_extended\sound\breath_out_3_sfx.ogg", "db-2", 1, 18};
    };
    class ACME_BreathOut_M_4: ACME_BreathIn_S_1 {
        name = "ACME_BreathOut_M_4";
        sound[] = {"acm_extended\sound\breath_out_4_sfx.ogg", "db-2", 1, 18};
    };
    class ACME_BreathOut_M_5: ACME_BreathIn_S_1 {
        name = "ACME_BreathOut_M_5";
        sound[] = {"acm_extended\sound\breath_out_5_sfx.ogg", "db-2", 1, 18};
    };
    class ACME_BreathOut_M_6: ACME_BreathIn_S_1 {
        name = "ACME_BreathOut_M_6";
        sound[] = {"acm_extended\sound\breath_out_6_sfx.ogg", "db-2", 1, 18};
    };
    class ACME_BreathOut_D_1: ACME_BreathIn_S_1 {
        name = "ACME_BreathOut_D_1";
        sound[] = {"acm_extended\sound\breath_out_1_sfx.ogg", "db+4", 1, 18};
    };
    class ACME_BreathOut_D_2: ACME_BreathIn_S_1 {
        name = "ACME_BreathOut_D_2";
        sound[] = {"acm_extended\sound\breath_out_2_sfx.ogg", "db+4", 1, 18};
    };
    class ACME_BreathOut_D_3: ACME_BreathIn_S_1 {
        name = "ACME_BreathOut_D_3";
        sound[] = {"acm_extended\sound\breath_out_3_sfx.ogg", "db+4", 1, 18};
    };
    class ACME_BreathOut_D_4: ACME_BreathIn_S_1 {
        name = "ACME_BreathOut_D_4";
        sound[] = {"acm_extended\sound\breath_out_4_sfx.ogg", "db+4", 1, 18};
    };
    class ACME_BreathOut_D_5: ACME_BreathIn_S_1 {
        name = "ACME_BreathOut_D_5";
        sound[] = {"acm_extended\sound\breath_out_5_sfx.ogg", "db+4", 1, 18};
    };
    class ACME_BreathOut_D_6: ACME_BreathIn_S_1 {
        name = "ACME_BreathOut_D_6";
        sound[] = {"acm_extended\sound\breath_out_6_sfx.ogg", "db+4", 1, 18};
    };
    // ROSC gasp. the patient gasps audibly on return of spontaneous circulation, through say3d to nearby
    // players.
    class ACME_RoscGasp: ACME_KellyCut_1 {
        name = "ACME_RoscGasp";
        sound[] = {"acm_extended\sound\rosc_gasp_sfx.ogg", "db+6", 1, 25};
    };
    // iv catheter cap and lock click. it plays only when a medic returns an item to its tray slot.
    class ACME_IVCap {
        name = "ACME_IVCap";
        sound[] = {"acm_extended\sound\iv_cap_sfx.ogg", 1.0, 1};
        titles[] = {};
    };
    // iv catheter un-cap and peel. it plays when a medic picks the catheter up off the tray.
    class ACME_IVUncap {
        name = "ACME_IVUncap";
        sound[] = {"acm_extended\sound\iv_uncap_sfx.ogg", 1.0, 1};
        titles[] = {};
    };
    // blood fridge door sfx, a mono .ogg, played through say3d on the open and closed model swap.
    // these are renamed. they used to be ACME_BloodFridge_Open and ACME_BloodFridge_Closed, which are also the
    // classnames of the two fridge models in CfgVehicles. say3d resolves against CfgSounds, and naming a sound and
    // a vehicle identically invites exactly the kind of silent lookup failure where the door swaps and nothing is
    // heard. the door sounds have their own names now.
    // manual suction bag: one squeeze of the bulb. it is a mono ogg, as every sound in this addon is.
    class ACME_ManualSuction {
        name = "ACME_ManualSuction";
        sound[] = {"\acm_extended\sound\manual_suction_sfx.ogg", 1.0, 1};
        titles[] = {};
    };
    class ACME_BloodFridgeDoorOpen {
        name = "ACME_BloodFridgeDoorOpen";
        sound[] = {"acm_extended\sound\bloodfridge_open.ogg", 1.0, 1, 30};
        titles[] = {};
    };
    class ACME_BloodFridgeDoorClose {
        name = "ACME_BloodFridgeDoorClose";
        sound[] = {"acm_extended\sound\bloodfridge_closed.ogg", 1.0, 1, 30};
        titles[] = {};
    };
    // narc box open and close, a mono .ogg. these are 2d ui sounds through playsound, fired on a genuine dialog
    // open or close. they are suppressed on a size-switch re-open, which reuses ACME_SK_RestoreMouse, so they play
    // on a real open or close only.
    class ACME_NarcBoxOpen {
        name = "ACME_NarcBoxOpen";
        sound[] = {"acm_extended\sound\narc_box_open.ogg", 1.0, 1};
        titles[] = {};
    };
    class ACME_NarcBoxClosed {
        name = "ACME_NarcBoxClosed";
        sound[] = {"acm_extended\sound\narc_box_closed.ogg", 1.0, 1};
        titles[] = {};
    };
    class ACM_Stethoscope_Breath_Normal_Crackles {
        name = "ACM_Stethoscope_Breath_Normal_Crackles";
        sound[] = {"acm_extended\sound\breathing_normal_crackles.ogg", "db+10", 1};
        titles[] = {};
    };
    class ACM_Stethoscope_Breath_Fast_Crackles {
        name = "ACM_Stethoscope_Breath_Fast_Crackles";
        sound[] = {"acm_extended\sound\breathing_fast_crackles.ogg", "db+10", 1};
        titles[] = {};
    };
    class ACM_Stethoscope_Breath_Slow_Crackles {
        name = "ACM_Stethoscope_Breath_Slow_Crackles";
        sound[] = {"acm_extended\sound\breathing_slow_crackles.ogg", "db+10", 1};
        titles[] = {};
    };
    // HPMK deploy, one-shot. it is the foil and shell rustle when a medic wraps the blanket.
    class ACM_HPMK_Wrap {
        name = "ACM_HPMK_Wrap";
        sound[] = {"acm_extended\sound\HPMK_sfx.ogg", "db+4", 1};
        titles[] = {};
    };
    // HPMK remove, one-shot. it is the unwrap and pack-away rustle.
    class ACM_HPMK_Remove {
        name = "ACM_HPMK_Remove";
        sound[] = {"acm_extended\sound\HPMK_remove_sfx.ogg", "db+4", 1};
        titles[] = {};
    };
    // chest seal apply, one-shot. it is the peel and stick.
    class ACM_ChestSeal_Apply {
        name = "ACM_ChestSeal_Apply";
        sound[] = {"acm_extended\sound\chest_seal_sfx.ogg", "db+4", 1};
        titles[] = {};
    };
    // chest seal hole reveal, one-shot. it plays when a rake over the chest uncovers a wound.
    class ACME_CS_HoleReveal {
        name = "ACME_CS_HoleReveal";
        sound[] = {"acm_extended\sound\chest_seal_hole_sfx.ogg", "db+2", 1};
        titles[] = {};
    };
    // NAR SPEAR pickup from the tray, one-shot. it plays when a medic takes the decompression needle in hand.
    class ACME_NARSPEAR_Open {
        name = "ACME_NARSPEAR_Open";
        sound[] = {"acm_extended\sound\nar_spear_open_sfx.ogg", "db+3", 1};
        titles[] = {};
    };
    // NAR SPEAR returned to the tray, one-shot. it plays when a medic puts the needle back.
    class ACME_NARSPEAR_Close {
        name = "ACME_NARSPEAR_Close";
        sound[] = {"acm_extended\sound\nar_spear_close_sfx.ogg", "db+3", 1};
        titles[] = {};
    };
    // NAR SPEAR needle pierce, one-shot. it plays on a correct 5th-ics decompression placement.
    class ACME_NARSPEAR_Pierce {
        name = "ACME_NARSPEAR_Pierce";
        sound[] = {"acm_extended\sound\nar_spear_pierce_sfx.ogg", "db+4", 1};
        titles[] = {};
    };
    // ACCUVAC power-down, one-shot. it plays when the suction timer completes.
    class ACM_Suction_Off {
        name = "ACM_Suction_Off";
        sound[] = {"acm_extended\sound\suction_off_sfx.ogg", "db+2", 1};
        titles[] = {};
    };
    // expose sfx, staged for a future system that cuts and exposes the casualty. they ship and register now so
    // they are ready to trigger, and no action is wired to them yet.
    class ACM_Expose_1 {
        name = "ACM_Expose_1";
        sound[] = {"acm_extended\sound\expose1_sfx.ogg", "db+2", 1};
        titles[] = {};
    };
    class ACM_Expose_2 {
        name = "ACM_Expose_2";
        sound[] = {"acm_extended\sound\expose2_sfx.ogg", "db+2", 1};
        titles[] = {};
    };
    class ACM_Expose_3 {
        name = "ACM_Expose_3";
        sound[] = {"acm_extended\sound\expose3_sfx.ogg", "db+2", 1};
        titles[] = {};
    };
    class ACM_Expose_4 {
        name = "ACM_Expose_4";
        sound[] = {"acm_extended\sound\expose4_sfx.ogg", "db+2", 1};
        titles[] = {};
    };
    class ACM_Expose_Chest {
        name = "ACM_Expose_Chest";
        sound[] = {"acm_extended\sound\expose_chest.ogg", "db+2", 1};
        titles[] = {};
    };
    // syringe plunger and vial draw. it runs for the full medication draw progress bar.
    class ACME_SyringeDraw {
        name = "ACME_SyringeDraw";
        sound[] = {"acm_extended\sound\syringe_draw.ogg", "db+3", 1};
        titles[] = {};
    };
    class ACME_SyringePush {
        name = "ACME_SyringePush";
        sound[] = {"acm_extended\sound\syringe_push.ogg", "db+5", 1};
        titles[] = {};
    };
    // EMMA inline capnograph connection sounds. the supplied wav files are converted to 44.1 khz mono ogg.
    class ACME_EMMA_Attach {
        name = "ACME_EMMA_Attach";
        sound[] = {"acm_extended\sound\emma_attach_sfx.ogg", "db+3", 1};
        titles[] = {};
    };
    class ACME_EMMA_Detach {
        name = "ACME_EMMA_Detach";
        sound[] = {"acm_extended\sound\emma_detach_sfx.ogg", "db+3", 1};
        titles[] = {};
    };
    // junctional treatment sfx.
    // packing, with combat gauze. the one-shot below is about 15.9 s and is no longer used by the action.
    class ACME_JunctionalPacking {
        name = "ACME_JunctionalPacking";
        sound[] = {"acm_extended\sound\junctionalwound_packing_sfx.ogg", "db+3", 1};
        titles[] = {};
    };
    // wrapping, with a pressure bandage, is about 7.3 s, looped for the duration of the wrap timer.
    // fn_junctionalwrapsfxstart replays it, so it still covers the timer if treatmenttime is retuned.
    class ACME_JunctionalWrapping {
        name = "ACME_JunctionalWrapping";
        sound[] = {"acm_extended\sound\junctionalwound_wrapping_sfx.ogg", "db+3", 1};
        titles[] = {};
    };
    // tie-off, about 0.85 s. it is a one-shot and always plays when the wrap timer completes.
    class ACME_JunctionalTie {
        name = "ACME_JunctionalTie";
        sound[] = {"acm_extended\sound\junctionalwound_packing_tie_sfx.ogg", "db+3", 1};
        titles[] = {};
    };
    // HPMK wrap, one-shot. it plays when a medic presses "Wrap in HPMK".
    class ACME_HPMK_Wrap {
        name = "ACME_HPMK_Wrap";
        sound[] = {"acm_extended\sound\HPMK_wrap.ogg", "db+4", 1};
        titles[] = {};
    };
    // HPMK unwrap, one-shot. it plays when a medic presses "Unwrap HPMK".
    class ACME_HPMK_Unwrap {
        name = "ACME_HPMK_Unwrap";
        sound[] = {"acm_extended\sound\HPMK_unwrap.ogg", "db+4", 1};
        titles[] = {};
    };
    // HPMK partial chest expose, one-shot. it plays when a medic presses "Partially Expose Chest".
    class ACME_HPMK_Expose {
        name = "ACME_HPMK_Expose";
        sound[] = {"acm_extended\sound\HPMK_expose_sfx.ogg", "db+4", 1};
        titles[] = {};
    };
    // direct pressure, a one-shot of about 0.85 s. it is the hands-on-wound press, and it plays the instant a
    // medic presses "Apply Direct Pressure", from the ACME_DirectPressure callbackstart.
    class ACME_DirectPressure {
        name = "ACME_DirectPressure";
        sound[] = {"acm_extended\sound\direct_pressure_sfx.ogg", "db+3", 1};
        titles[] = {};
    };
    // junctional leaking, a one-shot of about 2.4 s. it is an ambient wet arterial leak, and the junctional bleed
    // pfh replays it at random 5 to 10 s intervals while the wound still bleeds.
    class ACME_JunctionalLeaking {
        name = "ACME_JunctionalLeaking";
        sound[] = {"acm_extended\sound\junctionalwound_leaking_sfx.ogg", "db+2", 1};
        titles[] = {};
    };
};

// looping positional sound effects for createSoundSource. both are made into sound-source objects, in
// CfgVehicles below, so a delete stops them instantly.
// NRB is a continuous o2-flow hiss that plays the whole time the mask is on.
// suction is the accuvac and suction-bag aspiration, and it plays for the duration of the suction timer.
// the sound array format is name[] = {file, volume, pitch, distance, ...}. the trailing zeros set a 0 s
// interval, so the source repeats back to back and loops continuously while the object exists.
class CfgSFX {
    class ACM_NRB_SFX {
        sounds[] = {"nrb"};
        nrb[] = {"acm_extended\sound\nrbmask_sfx.ogg", 1.0, 1, 22, 1, 0, 0, 0};
        empty[] = {"", 0, 0, 0, 0, 0, 0, 0};
    };
    // looping packing sound for the junctional pressure-bandage wrap. it plays through a sound source so it can be
    // deleted the instant the wrap timer ends, because say3d cannot be stopped mid-clip.
    // the syringe draw is a source rather than a fired sound, so it can be stopped dead. a fired sound cannot be
    // stopped in this engine, and deleting the source object is the only immediate stop there is. cuff inflation
    // needs the sound to cut the instant the button comes up.
    class ACME_SyringeDraw_SFX {
        sounds[] = {"draw"};
        draw[] = {"acm_extended\sound\syringe_draw.ogg", 1.2, 1, 18, 0, 0, 0, 0};
        empty[] = {"", 0, 0, 0, 0, 0, 0, 0};
    };
    // the packing loop, as a deletable sound source. the packing action used to fire a 15.9 s say3d one-shot that
    // matched a 15 s timer and could not be stopped. the timer is 10 s now, so the sound is a loop that ends with
    // the action.
    class ACME_JunctionalPackLoop_SFX {
        sounds[] = {"pack"};
        pack[] = {"acm_extended\sound\junctionalwound_packing_sfx.ogg", 1.3, 1, 16, 1, 0, 0, 0};
        empty[] = {"", 0, 0, 0, 0, 0, 0, 0};
    };
    class ACME_JunctionalPack_SFX {
        sounds[] = {"wrap"};
        wrap[] = {"acm_extended\sound\junctionalwound_wrapping_sfx.ogg", 1.3, 1, 16, 1, 0, 0, 0};
        empty[] = {"", 0, 0, 0, 0, 0, 0, 0};
    };
    class ACME_JunctionalLeak_SFX {
        sounds[] = {"leak"};
        leak[] = {"acm_extended\sound\junctionalwound_leaking_sfx.ogg", 1.15, 1, 16, 1, 0, 0, 0};
        empty[] = {"", 0, 0, 0, 0, 0, 0, 0};
    };
    // ventilator running loop. the engine loops this, at delay 0, so it is gapless and cannot overlap itself, which
    // the old playSound3D retrigger could not guarantee. crucially, a sound source can be deleted, and a delete
    // stops the sound instantly. that is the only way a fade-out is possible at all, because arma cannot ramp the
    // volume of a sound that is already playing.
    class ACME_VentRun_SFX {
        sounds[] = {"run"};
        run[] = {"acm_extended\sound\ventilator_running_sfx.ogg", 1.6, 1, 30, 1, 0, 0, 0};
        empty[] = {"", 0, 0, 0, 0, 0, 0, 0};
    };
    class ACM_Suction_SFX {
        sounds[] = {"suction"};
        suction[] = {"acm_extended\sound\suction.ogg", 1.3, 1, 30, 1, 0, 0, 0};
        empty[] = {"", 0, 0, 0, 0, 0, 0, 0};
    };
};

// self-interaction radial. the saline-flush into push-dose prep sits next to ACM's own "Syringes" entry, under
// CAManBase > ACE_SelfActions > ACM_Equipment. ACM compiles the self menu purely from ACE_SelfActions config,
// and treatment-action data does not appear in the self menu automatically. that is why the flush was
// invisible. the statements call ACME_fnc_salineFlush directly, and _patient is unused for a self prep.
// the curator, or zeus, category is what the spawn megacode kelly module is filed under in the modules list.
class CfgFactionClasses {
    class NO_CATEGORY;
    class ACME_Curator_Category: NO_CATEGORY {
        displayName = "ACM Extended";
        priority = 3;
        side = 7;
    };
};

class CfgVehicles {
    // iv line, bag and anchor classes, moved here from the former second CfgVehicles block.
    class Rope;
    // thin, pale-blue PhysX iv line. it is ACE's fuelhose shape, shrunk to about 5 mm and recolored, and it needs
    // binarizing. this is the default line, for saline, crystalloid and medication, and it is clear. the blood and
    // plasma variants below reuse the same binarized model and swap the procedural rope color only, so they need
    // no extra art and no extra binarizing.
    class ACME_IVLine_Rope: Rope {
        scope = 1;
        model = "\acm_extended\models\iv_line_segment.p3d";
        segmentType = "ACME_IVLine_Segment";
        hiddenSelections[] = {"rope"};
        hiddenSelectionsTextures[] = {"#(argb,8,8,3)color(0.64,0.86,0.95,1.0,co)"};
    };
    // blood line, deep red. the runtime selects it when the hung unit is blood or fresh blood.
    class ACME_IVLine_Rope_Blood: ACME_IVLine_Rope {
        hiddenSelectionsTextures[] = {"#(argb,8,8,3)color(0.55,0.05,0.05,1.0,co)"};
    };
    // plasma line, amber or straw. the runtime selects it when the hung unit is plasma.
    class ACME_IVLine_Rope_Plasma: ACME_IVLine_Rope {
        hiddenSelectionsTextures[] = {"#(argb,8,8,3)color(0.86,0.72,0.32,1.0,co)"};
    };
    // pale-blue line that reuses ACE's refuel hose. it is binarized, so it always loads, and it is hose-thick. it
    // is the no-binarize fallback.
    class ACME_IVLine_BlueHose: Rope {
        scope = 1;
        model = "\z\ace\addons\refuel\data\hose.p3d";
        segmentType = "ace_refuel_fuelHoseSegment";
        hiddenSelections[] = {"rope"};
        hiddenSelectionsTextures[] = {"#(argb,8,8,3)color(0.64,0.86,0.95,1.0,co)"};
    };
    class ThingX;
    // the iv bag that attaches to the raised hand of the medic. it uses ACE's iv bag model.
    class ACME_IVBagObject: ThingX {
        scope = 1;
        scopeCurator = 0;
        displayName = "IV Bag";
        model = "\z\ace\addons\medical_treatment\data\IVBag_500ml.p3d";
        hiddenSelections[] = {"camo"};
        hiddenSelectionsTextures[] = {"\z\ace\addons\medical_treatment\data\IVBag_saline_500ml_ca.paa"};
    };
    // volume-matched iv bag models, at 250 and 1000 ml. the hung bag picks the class whose model matches the real
    // volume of the bag, and the runtime applies the fluid texture, blood, plasma or saline at that volume,
    // through setObjectTextureGlobal on the "camo" hidden selection. the grip calibration is the same as the 500
    // ml, because the ACE bag models share an origin. per-volume hand offsets can be added if a size sits off in
    // the hand.
    class ACME_IVBagObject_250: ACME_IVBagObject {
        model = "\z\ace\addons\medical_treatment\data\IVBag_250ml.p3d";
        hiddenSelectionsTextures[] = {"\z\ace\addons\medical_treatment\data\IVBag_saline_250ml_ca.paa"};
    };
    class ACME_IVBagObject_1000: ACME_IVBagObject {
        model = "\z\ace\addons\medical_treatment\data\IVBag_1000ml.p3d";
        hiddenSelectionsTextures[] = {"\z\ace\addons\medical_treatment\data\IVBag_saline_1000ml_ca.paa"};
    };
    // invisible, rope-capable anchor. ropecreate endpoints must be physics objects, and a person is rejected and
    // returns objnull, which is why roping straight to the patient always failed. this is the same trick ACE
    // towing uses for its rope endpoint: a ThingX with the vanilla empty model, attached to the iv site of the
    // patient.
    class ACME_RopeHelper: ThingX {
        scope = 1;
        scopeCurator = 0;
        displayName = "IV Line Anchor";
        model = "\A3\Weapons_f\empty";
    };

    // blood cooler boxes, as real containers.
    // blood lives as real ACM blood bags in the box cargo, so it travels with the box when a player drags it,
    // drops it, stashes it in a vehicle or hands it to a teammate, and it is shared natively. the box opens like
    // any container and carries through ACE drag, and an ACE "Pick Up Cooler" action folds it back into the
    // carried item. maximumload is sized to the rated unit count, where a 500 ml blood bag is mass 5.
    // the models are placeholders inherited from vanilla boxes: 1u is land_ammobox_rounds_f, 2u is Box_NATO_Ammo_F
    // and 4u is Box_NATO_Wps_F. each is tinted red through the "camo" hidden selection of the model when the model
    // exposes one. that is best-effort, and a guaranteed red needs a custom texture.
    // on the models: 2u and 4u keep their containers, and the 1u now uses the ammo-box container as well. its old
    // land_ammobox_rounds_f was a static prop with no inventory and no paintable selection, so it could neither
    // store blood nor go red. the 1u and 2u therefore share the ammo-box look for now.
    class Box_NATO_Ammo_F;
    class Box_NATO_Wps_F;
    class ACME_BloodCoolerBox_CSWB1U: Box_NATO_Ammo_F {
        scope = 2;
        scopeCurator = 2;
        author = "mavis";
        displayName = "Blood Cooler 1U (Box)";
        maximumLoad = 6;  // about 1 bag of 500 ml.
        transportMaxWeapons = 0;
        transportMaxMagazines = 0;
        transportMaxBackpacks = 0;
        hiddenSelections[] = {"camo"};
        hiddenSelectionsTextures[] = {"#(argb,8,8,3)color(0.62,0.10,0.10,1.0,co)"};
        ace_dragging_canDrag = 1;
        ace_dragging_dragPosition[] = {0, 1.0, 0};
        ace_dragging_dragDirection = 0;
        ace_dragging_canCarry = 1;
        ace_dragging_carryPosition[] = {0, 1.0, 1};
        ace_dragging_carryDirection = 0;
        class ACE_Actions {
            class ACE_MainActions {
                displayName = "Blood Cooler";
                selection = "";
                distance = 4;
                condition = "true";
                class ACME_PackUpCooler {
                    displayName = "Pick Up Cooler";
                    distance = 4;
                    condition = "true";
                    statement = "[_target] call ACME_fnc_coolerBoxPackUp";
                };
            };
        };
    };
    class ACME_BloodCoolerBox_CSWB2U: Box_NATO_Ammo_F {
        scope = 2;
        scopeCurator = 2;
        author = "mavis";
        displayName = "Blood Cooler 2U (Box)";
        maximumLoad = 11;  // about 2 bags of 500 ml.
        transportMaxWeapons = 0;
        transportMaxMagazines = 0;
        transportMaxBackpacks = 0;
        hiddenSelections[] = {"camo"};
        hiddenSelectionsTextures[] = {"#(argb,8,8,3)color(0.62,0.10,0.10,1.0,co)"};
        ace_dragging_canDrag = 1;
        ace_dragging_dragPosition[] = {0, 1.0, 0};
        ace_dragging_dragDirection = 0;
        ace_dragging_canCarry = 1;
        ace_dragging_carryPosition[] = {0, 1.0, 1};
        ace_dragging_carryDirection = 0;
        class ACE_Actions {
            class ACE_MainActions {
                displayName = "Blood Cooler";
                selection = "";
                distance = 4;
                condition = "true";
                class ACME_PackUpCooler {
                    displayName = "Pick Up Cooler";
                    distance = 4;
                    condition = "true";
                    statement = "[_target] call ACME_fnc_coolerBoxPackUp";
                };
            };
        };
    };
    class ACME_BloodCoolerBox_CSWB4U: Box_NATO_Wps_F {
        scope = 2;
        scopeCurator = 2;
        author = "mavis";
        displayName = "Blood Cooler 4U (Box)";
        maximumLoad = 21;  // about 4 bags of 500 ml.
        transportMaxWeapons = 0;
        transportMaxMagazines = 0;
        transportMaxBackpacks = 0;
        hiddenSelections[] = {"camo"};
        hiddenSelectionsTextures[] = {"#(argb,8,8,3)color(0.62,0.10,0.10,1.0,co)"};
        ace_dragging_canDrag = 1;
        ace_dragging_dragPosition[] = {0, 1.0, 0};
        ace_dragging_dragDirection = 0;
        ace_dragging_canCarry = 1;
        ace_dragging_carryPosition[] = {0, 1.0, 1};
        ace_dragging_carryDirection = 0;
        class ACE_Actions {
            class ACE_MainActions {
                displayName = "Blood Cooler";
                selection = "";
                distance = 4;
                condition = "true";
                class ACME_PackUpCooler {
                    displayName = "Pick Up Cooler";
                    distance = 4;
                    condition = "true";
                    statement = "[_target] call ACME_fnc_coolerBoxPackUp";
                };
            };
        };
    };

    class Man;
    class CAManBase: Man {
        class ACE_SelfActions {
            // one light at a time. ACE's map flashlight menu is an insertchildren node in CfgVehicles rather than a
            // registered action, so addactiontoclass cannot reach it. its condition is extended here instead: the original
            // clause is preserved verbatim and the laryngoscope block is added to it.
            // while a blade is in hand it is the light of the medic. without this they could switch to a torch they are
            // not holding, or switch off the light the blade is using, and end up dark with a lit instrument. put the
            // scope down and the entry returns on its own.
            class ACE_Equipment {
                class ACE_MapFlashlight {
                    condition = "(ace_map_mapIllumination && visibleMap) && {!(['blocked'] call ACME_fnc_laryngoFlash)}";
                };
            };

            // flashlights, in a minigame. this is the whole answer, and it is small.
            // ACE's own flashlight menu is defined in ace_map like this:
            // class ACE_MapFlashlight {
            // condition = quote(gvar(mapillumination) && visiblemap);
            // insertchildren = quote(call dfunc(compileflashlightmenu));
            // };
            // the condition is visiblemap. it only exists while the map is open. it was never a general pick-a-light-source
            // menu at all. it is a map feature, built to light the map. so however perfectly ACE's interaction menu opens
            // over our panel, that entry was never going to be in it. three builds went into getting ACE to open a menu
            // that could not contain the thing we wanted, because the thing we wanted is conditioned on a map we were not
            // looking at.
            // so this uses the same action, the same icon and the same insertchildren, ACE's own compileflashlightmenu, so
            // it lists ACE's items with ACE's names, switched by ACE's function. the only change is when it appears: when
            // a minigame panel is open, instead of when the map is.
            // it uses finddisplay rather than our stored handles, so it can never go stale. 86500 is iv, 86400 is chest
            // seal and 86600 is thoracostomy.
            class ACME_MinigameFlashlight {
                displayName = "Flashlights";
                icon = "\a3\ui_f\data\IGUI\Cfg\VehicleToggles\lightsiconon_ca.paa";
                // the condition is a plain boolean. there is no array, no findif and no _x.
                // the previous version did this:
                // (['ACME_IV_DLG', ...] findif { !isnull (uinamespace getvariable [_x, displaynull]) }) >= 0
                // and the entry never appeared.
                // ACE evaluates action conditions from inside its own foreach loop over the action list, so _x is already
                // bound to an ACE action when our condition runs. a findif with _x inside that is the oldest shadowing trap in
                // sqf. a condition that runs in someone else's scope should touch nothing but a variable it owns, so this
                // reads one boolean, set by each minigame when it opens and cleared when it closes. there is nothing left in
                // it to shadow, misparse or get wrong.
                // the value is derived and not stored. see fn_postInit. a boolean flag that ACE reads can strand ACE forever
                // if a single close path is missed, and that is exactly what happened. the base self-interaction menu stayed
                // filtered to this one entry for the rest of the mission and no object could be interacted with. a display
                // handle nulls itself when the engine destroys the display, so there is nothing to clear.
                // it is written longhand on purpose, with no findif and no _x, because this runs inside ACE's own foreach.
                // the airway screen and the syringe kit were missing from this list. the airway screen is also the
                // standalone suction screen, so neither of those could offer a light except through the flag, which is
                // only up during the ctrl+win handoff. that is why the flashlight worked on most minigames and not all.
                condition = "(missionNamespace getVariable ['ACME_flashlightMenuActive', false]) || (!isNull (uiNamespace getVariable ['ACME_IV_DLG', displayNull])) || (!isNull (uiNamespace getVariable ['ACME_CS_DLG', displayNull])) || (!isNull (uiNamespace getVariable ['ACME_Thora_DLG', displayNull])) || (!isNull (uiNamespace getVariable ['ACME_laryngo_dlg', displayNull])) || (!isNull (uiNamespace getVariable ['ACME_SK_DLG', displayNull]))";
                exceptions[] = {"isNotDragging", "notOnMap", "isNotInside", "isNotSitting"};
                // ACE's own list, plus anything else on the medic that emits light. see fn_lightextras.
                insertChildren = "(call ace_map_fnc_compileFlashlightMenu) + ([] call ACME_fnc_lightExtras)";
            };

            // block the patient's own "Get Up" while obtunded. ACM exposes this self-action in the lying state through the
            // isnotinlyingstate exception. with that removed, the self-menu of an obtunded patient has nothing left that
            // bypasses the lying gate, so they have no usable personal menu while obtunded. the re-open keeps ACM's
            // statement and exceptions and overrides the condition only.
            // HEAD ELEVATION COUNTS AS DOWN. a conscious casualty can be placed in semi-Fowler's since r-58, and the
            // person in that position needs a way out of it that does not require a second player. ACM tests the lying
            // state alone, so a casualty whose lying state was cleared underneath them while the pose still held had no
            // Get Up at all. either flag now offers it.
            // the statement is ACM's, which routes to the getUp override. that override already tears the elevation
            // down, re-vests the plate carrier, deletes the bolster and then stands the casualty up, so there is
            // nothing to add here.
            class ACM_Action_GetUp {
                condition = "((_player getVariable ['ACM_core_Lying_State', false]) || {_player getVariable ['ACME_headElevated', false]})";
                statement = "[_player, true] call ACM_core_fnc_getUp";
            };
            class ACM_Equipment {
                class ACME_FlushMenu {
                    displayName = "Saline Flush / Push-Dose Epi";
                    icon = "\acm_extended\ui\items\salineFlush_ca.paa";
                    condition = "(missionNamespace getVariable ['ACME_sys_sk', true]) && {((([_player, 'ACM_SalineFlush_10'] call ACME_fnc_itemCount) > 0) || {(_player getVariable ['ACME_flush_State', []]) isNotEqualTo []})}";
                    statement = "";
                    exceptions[] = {"isNotInside", "isNotSitting"};
                    showDisabled = 0;
                    class ACME_Flush_Prep {
                        displayName = "Saline Flush / Push-Dose (Syringe)";
                        icon = "\acm_extended\ui\items\salineFlush_ca.paa";
                        condition = "([_player, 'ACM_SalineFlush_10'] call ACME_fnc_itemCount) > 0";
                        statement = "uiNamespace setVariable ['ACME_SK_AutoSaline', true]; call ACME_fnc_syringeKitOpen";
                        exceptions[] = {"isNotInside", "isNotSitting"};
                        showDisabled = 0;
                    };
                    // pull a push-dose from a prepared, un-hung, dirty-epi bag in your kit.
                    class ACME_Flush_DrawDirtyPrep {
                        displayName = "Draw Push-Dose from Prepped Epi (10mcg)";
                        icon = "\acm_extended\ui\items\salineFlush_ca.paa";
                        condition = "false";  // B13: retired unmetered bag-charge route
                        statement = "playSound 'ACME_SyringeDraw'; [4.946, [_player], {(_this select 0) params ['_medic']; [_medic, _medic, '', ['drawDirtyPrep']] call ACME_fnc_salineFlush}, {}, 'Drawing from prepared epi bag...', {true}, ['isNotInside','isNotSwimming','isNotInZeus']] call ace_common_fnc_progressBar";
                        exceptions[] = {"isNotInside", "isNotSitting"};
                        showDisabled = 0;
                    };
                };
                // custom syringe kit. it is always accessible. it draws any medication through ACM's own syringe-draw dialog,
                // with the same drug list as "Use Syringe", plus a one-tap push-dose epi at 10 mcg/ml. the self side draws
                // into your own syringe with no patient inject.
                class ACME_SyringeKit {
                    displayName = "Narc Box";
                    icon = "\acm_extended\ui\items\narc_box_ca.paa";
                    condition = "true";
                    statement = "";
                    exceptions[] = {"isNotInside", "isNotSitting"};
                    showDisabled = 0;
                    class ACME_SyringeKit_Draw {
                        displayName = "Open Narc Box";
                        icon = "\acm_extended\ui\items\narc_box_ca.paa";
                        condition = "!isNil ""ACM_circulation_fnc_Syringe_Draw""";
                        statement = "ACME_infusion_pendingContext = nil; [10] call ACME_fnc_skOpenDraw";
                        exceptions[] = {"isNotInside", "isNotSitting"};
                        showDisabled = 1;
                    };
                    class ACME_SyringeKit_PushEpi {
                        displayName = "Draw Push-Dose Epi (10 mcg/mL)";
                        condition = "(([_player, 'ACM_SalineFlush_10'] call ACME_fnc_itemCount) > 0) && {([_player, 'EpinephrineCardiac'] call ACME_fnc_infusionVialVolume) >= 1}";
                        statement = "[_player, _player, '', ['pushDoseOneShot']] call ACME_fnc_salineFlush";
                        exceptions[] = {"isNotInside", "isNotSitting"};
                        showDisabled = 1;
                    };
                };
                // B59: prepared syringes are first-class personal medical equipment for this life; their stable IDs are shared by Syringe Menu and Body Map.
                class ACME_DrawnSyringes {
                    displayName = "Drawn Syringes";
                    icon = "\x\ACM\addons\circulation\ui\syringe_10_ca.paa";
                    condition = "!((_player getVariable ['ACME_narcStore', []]) isEqualTo [])";
                    statement = "";
                    insertChildren = "_this call ACME_fnc_skSyringeSelfMenu";
                    exceptions[] = {"isNotInside", "isNotSitting"};
                    showDisabled = 0;
                };
                // pull a golden hour 4u out of a nearby vehicle or container into the kit, which overloads the inventory. the
                // 4u is too heavy to take the normal way, and this is the deliberate carry-it-anyway path. it shows only when
                // a nearby source actually holds a 4u.
                class ACME_Take4U {
                    displayName = "Take Golden Hour 4U (overload)";
                    icon = "\acm_extended\ui\items\goldenhour_cswb4u_ca.paa";
                    condition = "(((nearestObjects [_player, ['AllVehicles','ReammoBox_F','WeaponHolderSimulated','GroundWeaponHolder'], 6]) findIf {_x != _player && {'ACME_BloodCooler_CSWB4U' in (itemCargo _x)}}) >= 0)";
                    statement = "call ACME_fnc_take4U";
                    exceptions[] = {"isNotInside", "isNotSitting"};
                    showDisabled = 0;
                };
                // blood cooler manager. it opens the cold-chain carrier you are holding. it is a reliable self-menu entry
                // alongside the inventory double-click, which can miss depending on the filter and list state. it is visible
                // only while a cooler is in the kit.
                class ACME_BloodCooler {
                    displayName = "Blood Cooler";
                    icon = "\acm_extended\ui\items\goldenhour_cswb1u_ca.paa";
                    condition = "({_x in (items _player)} count ['ACME_BloodCooler_CSWB1U','ACME_BloodCooler_CSWB2U','ACME_BloodCooler_CSWB4U']) > 0";
                    statement = "";
                    exceptions[] = {"isNotInside", "isNotSitting"};
                    showDisabled = 0;
                    class ACME_BloodCooler_Open {
                        displayName = "Open Blood Cooler";
                        icon = "\acm_extended\ui\items\goldenhour_cswb1u_ca.paa";
                        condition = "({_x in (items _player)} count ['ACME_BloodCooler_CSWB1U','ACME_BloodCooler_CSWB2U','ACME_BloodCooler_CSWB4U']) > 0";
                        statement = "call ACME_fnc_coolerOpenCarried";
                        exceptions[] = {"isNotInside", "isNotSitting"};
                        showDisabled = 0;
                    };
                    // prototype. set the carried cooler down as a real, openable container box. the blood becomes real bags in the
                    // box cargo and travels with the box when a player drags, drops, stashes or hands it off.
                    class ACME_BloodCooler_SetDown {
                        displayName = "Set Down as Box";
                        icon = "\acm_extended\ui\items\goldenhour_cswb4u_ca.paa";
                        condition = "({_x in (items _player)} count ['ACME_BloodCooler_CSWB1U','ACME_BloodCooler_CSWB2U','ACME_BloodCooler_CSWB4U']) > 0";
                        statement = "call ACME_fnc_coolerBoxDeploy";
                        exceptions[] = {"isNotInside", "isNotSitting"};
                        showDisabled = 0;
                    };
                };
                class ACME_VentilatorOpen {
                    // the same ventilator as the one on the patient menu. it is one machine. if it is already on a casualty it
                    // opens on them. if it is not, you are presetting the machine itself, which is a real workflow. presetting
                    // configures it and never connects it. that distinction is what stops the medic becoming their own second
                    // ventilated patient. see fn_ventpanelopen.
                    displayName = "Open Ventilator";
                    icon = "\acm_extended\ui\vent\ventway_sparrow_robust_ca.paa";
                    condition = "([_player, 'ACME_Ventilator'] call ACME_fnc_itemCount) > 0";
                    statement = "[] call ACME_fnc_ventPanelOpen";
                    exceptions[] = {"isNotInside", "isNotSitting"};
                    showDisabled = 0;
                };
            };
        };
        class ACE_Actions {
            class ACE_MainActions {
                // block a provider's "Get Up" on a patient who is obtunded. ACM_LyingState_GetUp already hides for player
                // targets through !isplayer. this covers ai as well and is the explicit guard.
                class ACM_LyingState_GetUp {
                    condition = "!(isPlayer _target) && {(_target getVariable ['ACM_core_Lying_State', false]) && {alive _target} && {!(_target getVariable ['ACE_isUnconscious', false])} && {!(_target getVariable ['ace_evacuation_casualtyTicketClaimed', false])} && {!(_target getVariable ['ACME_obtunded', false])}}";
                    statement = "[_target, true] call ACM_core_fnc_getUp";
                };
                // get up on the body, for player patients in the lying state. ACM's own entry above carries !(isplayer
                // _target), so a player forced into the lying state, by treatment repositioning, a stale hold or any forced
                // supine state, had no get up in their interact menu. this twin covers exactly the player case, so ai keeps
                // ACM's entry and there is never a duplicate row.
                // Awake obtunded casualties are intentionally included; the ACM override slows their actual Get Up movement.
                class ACME_LyingState_GetUp_Player {
                    displayName = "Get Up";
                    icon = "";
                    condition = "(isPlayer _target) && {_target getVariable ['ACM_core_Lying_State', false]} && {alive _target} && {!(_target getVariable ['ACE_isUnconscious', false])} && {!(_target getVariable ['ace_evacuation_casualtyTicketClaimed', false])}";
                    statement = "[_target, true] call ACM_core_fnc_getUp";
                    exceptions[] = {"isNotInside"};
                    showDisabled = 0;
                };
            };
        };
    };

    // looping positional sound-source objects. createSoundSource starts them and deletevehicle stops them. they
    // inherit the engine "Sound" emitter base, and each references a CfgSFX class above.
    class Sound;
    class ACM_NRB_SoundSource: Sound {
        scope = 1;
        sound = "ACM_NRB_SFX";
    };
    class ACME_SyringeDraw_SoundSource: Sound {
        scope = 1;
        sound = "ACME_SyringeDraw_SFX";
    };
    class ACME_JunctionalPackLoop_SoundSource: Sound {
        scope = 1;
        sound = "ACME_JunctionalPackLoop_SFX";
    };
    class ACME_JunctionalPack_SoundSource: Sound {
        scope = 1;
        sound = "ACME_JunctionalPack_SFX";
    };
    class ACME_JunctionalLeak_SoundSource: Sound {
        scope = 1;
        sound = "ACME_JunctionalLeak_SFX";
    };
    class ACM_Suction_SoundSource: Sound {
        scope = 1;
        sound = "ACM_Suction_SFX";
    };
    class ACME_VentRun_SoundSource: Sound {
        scope = 1;
        sound = "ACME_VentRun_SFX";
    };

    // zeus and eden module: "Spawn Megacode Kelly".
    // placing this logic, from the zeus modules tab or from eden, spawns a bare, gearless training manikin at the
    // position of the module through ACME_fnc_megacodeModuleInit, then deletes the logic.
    class Module_F;
    class ACME_ModuleMegacodeKelly: Module_F {
        scope = 2;
        scopeCurator = 2;
        displayName = "Spawn Megacode Kelly";
        category = "ACME_Curator_Category";
        function = "ACME_fnc_megacodeModuleInit";
        functionPriority = 1;
        isGlobal = 0;
        isTriggerActivated = 0;
        is3DEN = 0;
        curatorCanAttach = 0;
        icon = "\a3\ui_f\data\IGUI\Cfg\Actions\heal_ca.paa";
        portrait = "\a3\ui_f\data\IGUI\Cfg\Actions\heal_ca.paa";
        class Arguments {};
        class ModuleDescription {
            description = "Spawns a controllable Megacode Kelly training manikin: a bare, gearless casualty locked in ACM_LyingState. Interact with it to open the instructor control panel (vitals, rhythms, airway, wounds, neuro/ICP).";
        };
    };

    // drop-on-unit inflict modules. curatorCanAttach is 1, so the module attaches to the casualty it is placed on,
    // and the function resolves that unit through attachedto. isglobal is 0, so the function runs on the placing
    // machine and routes the state to the owner of the unit itself.
    class ACME_ModuleInflictEdema: Module_F {
        scope = 2;
        scopeCurator = 2;
        displayName = "Inflict Pulmonary Edema";
        category = "ACME_Curator_Category";
        function = "ACME_fnc_zeusInflictEdema";
        functionPriority = 1;
        isGlobal = 0;
        isTriggerActivated = 0;
        isDisposable = 1;
        curatorCanAttach = 1;
        class Arguments {};
        class ModuleDescription {
            description = "Floods the lungs with fluid overload. Recruitable shunt: PEEP treats it, oxygen alone does not.";
        };
    };
    class ACME_ModuleClearEdema: Module_F {
        scope = 2;
        scopeCurator = 2;
        displayName = "Clear Pulmonary Edema";
        category = "ACME_Curator_Category";
        function = "ACME_fnc_zeusClearEdema";
        functionPriority = 1;
        isGlobal = 0;
        isTriggerActivated = 0;
        isDisposable = 1;
        curatorCanAttach = 1;
        class Arguments {};
        class ModuleDescription {
            description = "Drains the fluid overload. The counterpart to Inflict Pulmonary Edema, so the same casualty can be run twice.";
        };
    };
    class ACME_ModuleInflictBlastLung: Module_F {
        scope = 2;
        scopeCurator = 2;
        displayName = "Inflict Blast Lung";
        category = "ACME_Curator_Category";
        function = "ACME_fnc_zeusInflictBlastLung";
        functionPriority = 1;
        isGlobal = 0;
        isTriggerActivated = 0;
        is3DEN = 0;
        curatorCanAttach = 1;
        icon = "\x\acm\addons\breathing\ui\chestseal_ca.paa";
        portrait = "\x\acm\addons\breathing\ui\chestseal_ca.paa";
        class Arguments {};
        class ModuleDescription {
            description = "Inflicts primary blast injury (blast lung) on the targeted casualty. The lung floods and stiffens: gas exchange collapses and they cannot be saved with a bag. They need intubation, high FiO2 and MECHANICAL VENTILATION. Because the lung is stiff, volume control (SIMV VC PS) drives the airway pressure into barotrauma and makes it worse. pressure control (SIMV PC) is the correct mode. Often accompanied by a pneumothorax.";
        };
    };

    class ACME_ModuleInflictJunctional: Module_F {
        scope = 2;
        scopeCurator = 2;
        displayName = "Inflict Junctional Bleed";
        category = "ACME_Curator_Category";
        function = "ACME_fnc_zeusInflictJunctional";
        functionPriority = 1;
        isGlobal = 0;
        isTriggerActivated = 0;
        is3DEN = 0;
        curatorCanAttach = 1;
        icon = "\z\ace\addons\medical_treatment\ui\tourniquet_ca.paa";
        portrait = "\z\ace\addons\medical_treatment\ui\tourniquet_ca.paa";
        class Arguments {};
        class ModuleDescription {
            description = "Places a junctional (axillary/inguinal) arterial hemorrhage on a random uninjured limb of the targeted casualty. Drop again for another limb. Controlled by direct pressure, packing, wraps, or an AAJT-S.";
        };
    };

    class ACME_ModuleInduceObtundation: Module_F {
        scope = 2;
        scopeCurator = 2;
        displayName = "Induce / Clear Obtundation";
        category = "ACME_Curator_Category";
        function = "ACME_fnc_zeusInduceObtundation";
        functionPriority = 1;
        isGlobal = 0;
        isTriggerActivated = 0;
        is3DEN = 0;
        curatorCanAttach = 1;
        icon = "\a3\ui_f\data\IGUI\Cfg\Actions\heal_ca.paa";
        portrait = "\a3\ui_f\data\IGUI\Cfg\Actions\heal_ca.paa";
        class Arguments {};
        class ModuleDescription {
            description = "Toggles the awake-but-down obtunded (back) state on the targeted casualty. Players get the full input-lock and blur experience; AI are placed in the locked back pose. Drop again to clear it.";
        };
    };

    class ACME_ModuleInflictTBI: Module_F {
        scope = 2;
        scopeCurator = 2;
        displayName = "Inflict TBI";
        category = "ACME_Curator_Category";
        function = "ACME_fnc_zeusInflictTBI";
        functionPriority = 1;
        isGlobal = 0;
        isTriggerActivated = 0;
        is3DEN = 0;
        curatorCanAttach = 1;
        icon = "\a3\ui_f\data\IGUI\Cfg\Actions\heal_ca.paa";
        portrait = "\a3\ui_f\data\IGUI\Cfg\Actions\heal_ca.paa";
        class Arguments {};
        class ModuleDescription {
            description = "Opens a dialog to set a traumatic brain injury on the targeted casualty: choose severity and an initial state (Mild / Moderate / Severe / Herniating). Drives the CPP/ICP model.";
        };
    };

    // zeus: place an IV of any gauge on the targeted casualty, at any limb and any access site.
    // it opens a dialog rather than acting straight away, because a placement needs three choices and a module
    // cannot ask for them.
    // it also writes the catheter hub into the mark array, so the line can be pulled in the IV screen the same way
    // a hand-placed one can. without that a curator-placed IV would have no removal path at all, because the
    // gauge removal buttons were hidden in v0.9.999r-42.
    class ACME_ModuleInsertIV: Module_F {
        scope = 2;
        scopeCurator = 2;
        displayName = "Place IV";
        category = "ACME_Curator_Category";
        function = "ACME_fnc_zeusInsertIV";
        functionPriority = 1;
        isGlobal = 0;
        isTriggerActivated = 0;
        is3DEN = 0;
        curatorCanAttach = 1;
        icon = "\a3\ui_f\data\IGUI\Cfg\Actions\heal_ca.paa";
        portrait = "\a3\ui_f\data\IGUI\Cfg\Actions\heal_ca.paa";
        class Arguments {};
        class ModuleDescription {
            description = "Opens a dialog to place an IV on the targeted casualty: choose the limb, the access site and the gauge, 14g, 16g, 18g or 20g. The catheter hub is written to the limb so it can be pulled in the IV screen.";
        };
    };

    class ACME_ModuleClearTBI: Module_F {
        scope = 2;
        scopeCurator = 2;
        displayName = "Clear TBI";
        category = "ACME_Curator_Category";
        function = "ACME_fnc_zeusClearTBI";
        functionPriority = 1;
        isGlobal = 0;
        isTriggerActivated = 0;
        is3DEN = 0;
        curatorCanAttach = 1;
        icon = "\a3\ui_f\data\IGUI\Cfg\Actions\heal_ca.paa";
        portrait = "\a3\ui_f\data\IGUI\Cfg\Actions\heal_ca.paa";
        class Arguments {};
        class ModuleDescription {
            description = "Clears a traumatic brain injury and all ICP state from the targeted casualty (resolves ICP drive, herniation, evac flag and vitals offsets). Reverses Inflict TBI.";
        };
    };

    // blood fridge.
    // this is a stocked blood refrigerator. the module spawns a closed-model fridge plus a co-located open-model
    // twin, and the server hides and shows whichever matches the live state. the fridge auto-opens, with the model
    // and the door sfx, while any player has the ACE interaction menu pointed at it, and shuts when the last one
    // looks away. ACE "Take" hands out 500 ml units by type, and if the player carries a cooler the cold-chain
    // ledger covers the unit by volume automatically. stock is preserved indefinitely while inside, and it can
    // restock to its configured load each in-game day.
    // two object classes share one ACE_Actions body through the FRIDGE_ACTIONS macro, so take works on whichever
    // model is currently shown. the closed object is always the state anchor, and the open object stores
    // ACME_bf_anchor pointing at it.
    #define FRIDGE_ACTIONS \
        class ACE_Actions { \
            class ACE_MainActions { \
                displayName = "Blood Fridge"; \
                selection = ""; \
                distance = 4; \
                condition = "true"; \
                class ACME_bf_take { \
                    displayName = "Take Blood Unit"; \
                    icon = "\z\ace\addons\medical_treatment\ui\bloodIV_ca.paa"; \
                    distance = 4; \
                    condition = "true"; \
                    statement = ""; \
                    insertChildren = "_this call ACME_fnc_bloodFridgeTakeMenu"; \
                }; \
                class ACME_BF_Contents { \
                    displayName = "Check Contents"; \
                    condition = "true"; \
                    statement = "[_target] call ACME_fnc_bloodFridgeContents"; \
                    icon = "\z\ace\addons\medical_treatment\ui\bloodIV_ca.paa"; \
                }; \
            }; \
        }

    class Fridge_01_closed_F;
    class Fridge_01_open_F;

    class ACME_BloodFridge_Closed: Fridge_01_closed_F {
        scope = 1;  // spawned by the module only. the module is the placement surface.
        scopeCurator = 0;
        displayName = "Blood Fridge (Stocked)";
        author = "PILLAR";
        FRIDGE_ACTIONS;
    };
    class ACME_BloodFridge_Open: Fridge_01_open_F {
        scope = 1;
        scopeCurator = 0;
        displayName = "Blood Fridge (Open)";
        author = "PILLAR";
        FRIDGE_ACTIONS;
    };

    // zeus and eden module. the arguments render in both the eden module attribute panel and the zeus placement
    // dialog.
    class ACME_ModuleBloodFridge: Module_F {
        scope = 2;
        scopeCurator = 2;
        displayName = "Place Blood Fridge";
        category = "ACME_Curator_Category";
        function = "ACME_fnc_bloodFridgeModuleInit";
        functionPriority = 1;
        isGlobal = 0;
        isTriggerActivated = 0;
        is3DEN = 0;
        curatorCanAttach = 1;
        icon = "\z\ace\addons\medical_treatment\ui\bloodIV_ca.paa";
        portrait = "\z\ace\addons\medical_treatment\ui\bloodIV_ca.paa";
        class Arguments {
            class ONeg  { displayName = "O- units";  description = "500 mL units of O-negative (universal donor)."; typeName = "NUMBER"; defaultValue = 2; };
            class OPos  { displayName = "O+ units";  description = "500 mL units of O-positive.";  typeName = "NUMBER"; defaultValue = 6; };
            class ANeg  { displayName = "A- units";  description = "500 mL units of A-negative.";  typeName = "NUMBER"; defaultValue = 0; };
            class APos  { displayName = "A+ units";  description = "500 mL units of A-positive.";  typeName = "NUMBER"; defaultValue = 0; };
            class BNeg  { displayName = "B- units";  description = "500 mL units of B-negative.";  typeName = "NUMBER"; defaultValue = 0; };
            class BPos  { displayName = "B+ units";  description = "500 mL units of B-positive.";  typeName = "NUMBER"; defaultValue = 0; };
            class ABNeg { displayName = "AB- units"; description = "500 mL units of AB-negative."; typeName = "NUMBER"; defaultValue = 0; };
            class ABPos { displayName = "AB+ units"; description = "500 mL units of AB-positive."; typeName = "NUMBER"; defaultValue = 0; };
            class Restock { displayName = "Restock periodically"; description = "If yes, the fridge refills to its configured load every regen interval below."; typeName = "BOOL"; defaultValue = 1; };
            class RegenMins { displayName = "Regen interval (in-game minutes)"; description = "In-game minutes between regenerations. 1440 = 24 in-game hours (default). 0 = never regenerate. -1 = use the addon-option interval."; typeName = "NUMBER"; defaultValue = 1440; };
        };
        class ModuleDescription {
            description = "Places a stocked blood fridge. Set per-type unit counts (defaults 2x O-, 6x O+) and daily restock. ACE-interact to take units; blood keeps indefinitely while inside and the model opens while anyone is using it.";
        };
    };
};

// ACM's custom medical menu renders each collected treatment action as a button of class
// ACM_MedicalMenu_ActionButton_<ACM_menuIcon>, in gui/overrides/fnc_updateactions.sqf. when the show action
// item icons option is on, which is ACM's default, an action whose ACM_menuIcon has no matching button class
// makes ctrlcreate fail. the button is then never created and the action silently never appears in its
// category. our NRB and HPMK actions set ACM_menuIcon, so we must supply the matching button classes, with the
// icon through textureNoShortcut, exactly as ACM does for its own items in gui/actionbuttons.hpp. ACM_AED
// already has a button class in ACM.
// on left-aligning all medical-menu button text, which was centerd: ACM's stock medical-menu button is
// ACE-centerd and is used as-is by default, and our per-action icon buttons below inherit it. left alignment
// is optional now. when the left-align medical menu accessibility option is on, a thin wrapper around
// updateactions, see fn_postInit, swaps each button for its ACM_MedicalMenu_ActionButton_L_* variant, defined
// after the icon classes. so we no longer reopen _none at all. that reopen, with a partial TextPos, is what
// caused the .../TextPos.top crash, because a redefined nested class drops the inherited members.
// B90: CPR and manual BVM action ownership is intentionally left to ACM. ACME does not restate CPR's action
// condition/callback or replace ACM's continuous-action functions; addon-specific systems only observe their
// published patient state where needed.

class ACM_MedicalMenu_ActionButton_None;
class ACM_MedicalMenu_ActionButton_ACM_NRBMask: ACM_MedicalMenu_ActionButton_None {
    textureNoShortcut = "\acm_extended\ui\items\nrbmask_ca.paa";
};
class ACM_MedicalMenu_ActionButton_ACM_HPMK: ACM_MedicalMenu_ActionButton_None {
    textureNoShortcut = "\acm_extended\ui\items\HPMK_ca.paa";
};
// AAJT-s treatment-action icon. ACM's medical menu renders the icon of an action from the textureNoShortcut of
// a button class named ACM_MedicalMenu_ActionButton_<ACM_menuIcon>. it ignores the ACE icon property there,
// which is why the AAJT entry showed blank. the four AAJT actions set ACM_menuIcon to "ACME_AAJT".
class ACM_MedicalMenu_ActionButton_ACME_AAJT: ACM_MedicalMenu_ActionButton_None {
    textureNoShortcut = "\acm_extended\ui\items\aajt-s_ca.paa";
};
class ACM_MedicalMenu_ActionButton_ACME_Ventilator: ACM_MedicalMenu_ActionButton_None {
    textureNoShortcut = "\acm_extended\ui\vent\ventway_sparrow_robust_icon_ca.paa";
};
class ACM_MedicalMenu_ActionButton_ACM_EMMA: ACM_MedicalMenu_ActionButton_None {
    textureNoShortcut = "\acm_extended\ui\emma\emma_etco2_ca.paa";
};
class ACM_MedicalMenu_ActionButton_ACME_iGel_Remove: ACM_MedicalMenu_ActionButton_None {
    textureNoShortcut = "\acm_extended\ui\items\igel_remove_ca.paa";
};
class ACM_MedicalMenu_ActionButton_ACME_IV_18g: ACM_MedicalMenu_ActionButton_None {
    textureNoShortcut = "\acm_extended\ui\items\iv_18g_ca.paa";
};
// the 20g row icon. nothing sets ACM_menuIcon to this yet, which is harmless: an action naming a button class
// that does not exist fails ctrlCreate and vanishes, and a button class that nothing names simply sits there.
class ACM_MedicalMenu_ActionButton_ACME_IV_20g: ACM_MedicalMenu_ActionButton_None {
    textureNoShortcut = "\acm_extended\ui\items\iv_20g_ca.paa";
};
class ACM_MedicalMenu_ActionButton_ACME_NARSPEAR: ACM_MedicalMenu_ActionButton_None {
    textureNoShortcut = "\acm_extended\ui\items\nar_spear_ca.paa";
};
// in esketamine spray. without this button class ACM's menu cannot build the button, because ctrlcreate fails,
// and the head action silently never appears even though the treatment action and the item are defined. it
// mirrors naloxone.
class ACM_MedicalMenu_ActionButton_ACME_Spray_Esketamine: ACM_MedicalMenu_ActionButton_None {
    textureNoShortcut = "\acm_extended\ui\items\esketamine_in_ca.paa";
};
// combat gauze icon for "Pack Wound (Combat Gauze)". ACME_PackJunctional sets ACM_menuIcon to
// "ACME_CombatGauze".
class ACM_MedicalMenu_ActionButton_ACME_CombatGauze: ACM_MedicalMenu_ActionButton_None {
    textureNoShortcut = "\acm_extended\ui\items\combat_gauze_ca.paa";
};
// XStat 30 icon for "Insert XStat 30". ACM ignores the ACE icon field in its custom menu and instead
// ctrlcreates ACM_MedicalMenu_ActionButton_<ACM_menuIcon>. without this class the action can vanish silently
// when action-item icons are enabled.
class ACM_MedicalMenu_ActionButton_ACME_XStat: ACM_MedicalMenu_ActionButton_None {
    textureNoShortcut = "\acm_extended\ui\items\xstat_ca.paa";
};
// narc box icon for the "Narc Box: Draw + Administer" treatment action, where ACM_menuIcon is
// "ACME_NarcBox".
class ACM_MedicalMenu_ActionButton_ACME_NarcBox: ACM_MedicalMenu_ActionButton_None {
    textureNoShortcut = "\acm_extended\ui\items\narc_box_ca.paa";
};
// establish iv, the iv mini-game start action. the user supplied the icon.
class ACM_MedicalMenu_ActionButton_ACME_EstablishIV: ACM_MedicalMenu_ActionButton_None {
    textureNoShortcut = "\acm_extended\ui\items\establish_iv_ca.paa";
};


// optional left-align menu family.
// when the left-align medical menu accessibility option is on, the wrapper around updateactions, in
// fn_postInit, rewrites the menuicon of each action to "L_<icon>". ACM then builds the button from
// ACM_MedicalMenu_ActionButton_L_<icon> below instead of the stock centerd class. each l_ variant inherits the
// stock icon class, for its texture and shortcutpos, and restates a full attributes with align=left and a full
// TextPos. full is required, because a partial nested class drops the inherited members. that was the
// TextPos.top crash. it is off by default and untouched unless enabled.

// forward-declare ACM's stock icon classes so the l_ variants can inherit their textures. our own icon classes
// above are already in scope, so they are not re-declared here.
class ACM_MedicalMenu_ActionButton_ACE_tourniquet;
class ACM_MedicalMenu_ActionButton_ACE_surgicalKit;
class ACM_MedicalMenu_ActionButton_ACE_personalAidKit;
class ACM_MedicalMenu_ActionButton_ACE_bodyBag;
class ACM_MedicalMenu_ActionButton_ACE_bodyBag_blue;
class ACM_MedicalMenu_ActionButton_ACE_bodyBag_white;
class ACM_MedicalMenu_ActionButton_ACE_adenosine;
class ACM_MedicalMenu_ActionButton_ACE_epinephrine;
class ACM_MedicalMenu_ActionButton_CPR;
class ACM_MedicalMenu_ActionButton_ACE_morphine;
class ACM_MedicalMenu_ActionButton_ACM_OPA;
class ACM_MedicalMenu_ActionButton_ACM_IGel;
class ACM_MedicalMenu_ActionButton_ACM_NPA;
class ACM_MedicalMenu_ActionButton_ACM_SuctionBag;
class ACM_MedicalMenu_ActionButton_ACM_ACCUVAC;
class ACM_MedicalMenu_ActionButton_ACM_CricKit;
class ACM_MedicalMenu_ActionButton_ACM_ChestSeal;
class ACM_MedicalMenu_ActionButton_ACM_PulseOximeter;
class ACM_MedicalMenu_ActionButton_ACM_Stethoscope;
class ACM_MedicalMenu_ActionButton_ACM_NCDKit;
class ACM_MedicalMenu_ActionButton_ACM_ChestTubeKit;
class ACM_MedicalMenu_ActionButton_ACM_ThoracostomyKit;
class ACM_MedicalMenu_ActionButton_ACM_PocketBVM;
class ACM_MedicalMenu_ActionButton_ACM_BVM;
class ACM_MedicalMenu_ActionButton_ACM_AED;
class ACM_MedicalMenu_ActionButton_ACM_PressureCuff;
// the two IV rows are NOT forward-declared here. they are modified further down instead, and a name may appear
// only ONCE in a scope: declaring it and then reopening it is two mentions and the engine rejects the file.
// see the block below ACM_MedicalMenu_ActionButton_ACM_Midazolam_Autoinjector.
class ACM_MedicalMenu_ActionButton_ACM_IO_FAST;
class ACM_MedicalMenu_ActionButton_ACM_IO_EZ;
class ACM_MedicalMenu_ActionButton_ACM_Syringe_10;
class ACM_MedicalMenu_ActionButton_ACM_Syringe_5;
class ACM_MedicalMenu_ActionButton_ACM_Syringe_3;
class ACM_MedicalMenu_ActionButton_ACM_Syringe_1;
class ACM_MedicalMenu_ActionButton_ACM_Spray_Naloxone;
class ACM_MedicalMenu_ActionButton_ACM_Paracetamol;
class ACM_MedicalMenu_ActionButton_ACM_AmmoniaInhalant;
class ACM_MedicalMenu_ActionButton_ACM_Inhaler_Penthrox;
class ACM_MedicalMenu_ActionButton_ACM_Lozenge_Fentanyl;
class ACM_MedicalMenu_ActionButton_ACM_PressureBandage;
class ACM_MedicalMenu_ActionButton_ACM_EmergencyTraumaDressing;
class ACM_MedicalMenu_ActionButton_ACM_ElasticWrap;
class ACM_MedicalMenu_ActionButton_ACM_SAMSplint;
class ACM_MedicalMenu_ActionButton_ACM_ATNA_Autoinjector;
class ACM_MedicalMenu_ActionButton_ACM_Midazolam_Autoinjector;

// ACM'S OWN TWO CATHETER ROW ICONS, REPOINTED AT THE MATCHING SET.
//
// TWO RULES, AND THREE REJECTED BUILDS BETWEEN THEM.
//
// 1. A NAME MAY APPEAR ONCE PER SCOPE. either you forward-declare it, so something can inherit from it, or you
//    reopen it to modify it. doing both is two mentions of one member and the engine rejects the whole config
//    file with "Member already defined". the forward declarations for these two were removed from the block
//    above for exactly this reason.
// 2. NO PARENT ON A REOPEN. a class that already exists, here in ACM, is modified by reopening it with a body
//    and no parent. writing "class X: P { ... }" declares a NEW class of that name, which collides with the one
//    that is already there.
//
// r-50 shipped with the parent restated. r-51 moved the block, which changed nothing because placement was
// never the fault. r-52 removed the parent and still had the declaration above it. this is the third fix and it
// is verified by a check that flags any name mentioned twice in a scope, which reports the whole file clean.
//
// the proven form is elsewhere in this file already: InsertIV_16_Upper at line 6769 and ApplyChestSeal at 6881
// are ACM classes modified with exactly this shape, no parent and no declaration, and they have shipped for
// many builds. restating a parent is correct only for a class this addon is CREATING, which is what every other
// button class in this section is.
//
// ACM generates these two from a macro whose entire body is textureNoShortcut, at gui/ActionButtons.hpp:36
// and :37, so a modify carrying textureNoShortcut alone replaces the only property either one has.
//
// NOTE THE CASE. the button class is ACM_IV_16G with a capital G and the inventory item is ACM_IV_16g with a
// small one. overrides/fn_updateActions.sqf:221 to 225 carries the map between the two spellings.
class ACM_MedicalMenu_ActionButton_ACM_IV_16G {
    textureNoShortcut = "\acm_extended\ui\items\iv_16g_ca.paa";
};
class ACM_MedicalMenu_ActionButton_ACM_IV_14G {
    textureNoShortcut = "\acm_extended\ui\items\iv_14g_ca.paa";
};

#define ACME_LBTN(name) \
    class ACM_MedicalMenu_ActionButton_L_##name: ACM_MedicalMenu_ActionButton_##name { \
        style = 0; \
        class Attributes { align = "left"; color = "#E5E5E5"; font = "RobotoCondensed"; shadow = "false"; }; \
        class TextPos { \
            left = "0.013 + 1.35 * (((safezoneW / safezoneH) min 1.2) / 40)"; \
            top = "(((((safezoneW / safezoneH) min 1.2) / 1.2) / 25) - (((safezoneW / safezoneH) min 1.2) / 40)) / 2"; \
            right = 0.005; \
            bottom = 0; \
        }; \
    }
ACME_LBTN(None);
ACME_LBTN(ACE_tourniquet);
ACME_LBTN(ACE_surgicalKit);
ACME_LBTN(ACE_personalAidKit);
ACME_LBTN(ACE_bodyBag);
ACME_LBTN(ACE_bodyBag_blue);
ACME_LBTN(ACE_bodyBag_white);
ACME_LBTN(ACE_adenosine);
ACME_LBTN(ACE_epinephrine);
ACME_LBTN(CPR);
ACME_LBTN(ACE_morphine);
ACME_LBTN(ACM_OPA);
ACME_LBTN(ACM_IGel);
ACME_LBTN(ACM_NPA);
ACME_LBTN(ACM_SuctionBag);
ACME_LBTN(ACM_ACCUVAC);
ACME_LBTN(ACM_CricKit);
ACME_LBTN(ACM_ChestSeal);
ACME_LBTN(ACM_PulseOximeter);
ACME_LBTN(ACM_Stethoscope);
ACME_LBTN(ACM_NCDKit);
ACME_LBTN(ACM_ChestTubeKit);
ACME_LBTN(ACM_ThoracostomyKit);
ACME_LBTN(ACM_PocketBVM);
ACME_LBTN(ACM_BVM);
ACME_LBTN(ACM_AED);
ACME_LBTN(ACM_PressureCuff);
ACME_LBTN(ACM_IV_16G);
ACME_LBTN(ACM_IV_14G);
ACME_LBTN(ACM_IO_FAST);
ACME_LBTN(ACM_IO_EZ);
ACME_LBTN(ACM_Syringe_10);
ACME_LBTN(ACM_Syringe_5);
ACME_LBTN(ACM_Syringe_3);
ACME_LBTN(ACM_Syringe_1);
ACME_LBTN(ACM_Spray_Naloxone);
ACME_LBTN(ACM_Paracetamol);
ACME_LBTN(ACM_AmmoniaInhalant);
ACME_LBTN(ACM_Inhaler_Penthrox);
ACME_LBTN(ACM_Lozenge_Fentanyl);
ACME_LBTN(ACM_PressureBandage);
ACME_LBTN(ACM_EmergencyTraumaDressing);
ACME_LBTN(ACM_ElasticWrap);
ACME_LBTN(ACM_SAMSplint);
ACME_LBTN(ACM_ATNA_Autoinjector);
ACME_LBTN(ACM_Midazolam_Autoinjector);
ACME_LBTN(ACM_NRBMask);
ACME_LBTN(ACM_HPMK);
ACME_LBTN(ACME_AAJT);
ACME_LBTN(ACM_EMMA);
ACME_LBTN(ACME_iGel_Remove);
ACME_LBTN(ACME_IV_18g);
ACME_LBTN(ACME_IV_20g);
ACME_LBTN(ACME_NARSPEAR);
ACME_LBTN(ACME_Spray_Esketamine);
ACME_LBTN(ACME_CombatGauze);
ACME_LBTN(ACME_XStat);
ACME_LBTN(ACME_NarcBox);
ACME_LBTN(ACME_EstablishIV);
// connect airway > ventilator, disconnect ventilator and open ventilator all carry ACM_menuIcon set to
// "ACME_Ventilator". the renderer swaps each button for its ACM_MedicalMenu_ActionButton_L_<icon> class when
// left alignment is on, so without this the ventilator actions had no left variant to swap to and stayed
// centerd while every other entry moved.
ACME_LBTN(ACME_Ventilator);
#undef ACME_LBTN

class ace_medical_treatment_actions {
    // PARALLEL PROVIDER RULE:
    // Active BVM, CPR and other continuous roles reserve only that same role. They do not globally
    // disable unrelated treatment actions for another provider. The provider actually performing a
    // continuous action remains occupied locally, while BVM canUseBVM, CPR canCPR and procedure-specific
    // in-progress state preserve one-provider-per-role / one-procedure-at-a-time behavior.
    // only CheckPulse is forward declared, because it is the only one of these we do not go on to define.
    // declaring a class and then defining it in the same scope gives "Member already defined". the definition
    // below is the reference, and other classes inherit from it perfectly well with no separate declaration.
    class CheckPulse;

    // NA8: preserve ACM's action and replace only its completed assessment callback.
    // ACM core/ACE_Medical_Treatment_Actions.hpp:217-228 defines its parent and conditions.
    class InspectForFracture: CheckPulse {
        callbackSuccess = "ACME_fnc_inspectForFracture";
    };

    // User-supplied removal icon. Behaviour remains ACE/ACM-native; only the action presentation changes.
    class RemoveOPA;
    class RemoveIGel: RemoveOPA {
        icon = "\acm_extended\ui\items\igel_remove_ca.paa";
        ACM_menuIcon = "ACME_iGel_Remove";
    };

    // assessment animations.
    // these actions have never had a medic animation. ACE's diagnose sets animationmedic to "" with a literal todo
    // beside it, CheckPulse then blanks the prone variants too, and everything in the assessment family inherits
    // that emptiness. a medic checking an airway or feeling for a pulse simply stood there.
    // there are two motions, split by what the hands actually do.
    // medic4 is a deliberate two-handed maneuver at the head. opening an airway and shaking someone for a
    // response are both things you do to a casualty with some force.
    // gear is a light, close, one-handed reach. feeling a pulse, a forehead or skin turgor, and pressing a nail
    // bed, are the same gesture: touch, wait, read.
    // they are set on the actions themselves rather than on the shared parent, because CheckPulse is the base for
    // a lot more than these. quietly giving every descendant an animation is how you end up with a medic doing a
    // gear check while they cannulate.
    class CheckAirway {
        // B47: one pose owner cleanly enters the requested medic4_old examination from empty-handed crouch,
        // keeps it inside the treatment window, then blends back to the same crouch.  The exact-class guard in
        // ACME_fnc_airwayMedicPose prevents CheckAirway descendants from inheriting this theatre accidentally.
        animationMedic = "";
        animationMedicProne = "";
        animationMedicSelf = "";
        animationMedicSelfProne = "";
        // Dead engine corpses retain intervention/inspection access where explicitly supported, but a live airway
        // assessment is not one of those actions. Keep this gate local to Check Airway rather than globally hiding
        // dead-patient medical actions.
        condition = "alive _patient && {ACM_airway_enable} && {!(_patient call ace_common_fnc_isAwake)}";
        callbackStart = "_this call ACME_fnc_airwayMedicPose";
        callbackSuccess = "_this call ACM_airway_fnc_checkAirway; [_medic, 'airway'] call ACME_fnc_treatmentPoseStop";
        callbackFailure = "[_medic, 'airway'] call ACME_fnc_treatmentPoseStop";
    };
    class RecoveryPosition: CheckAirway {
        displayName = "$STR_ACM_Airway_EstablishRecoveryPosition";
        displayNameProgress = "$STR_ACM_Airway_EstablishRecoveryPosition_Progress";
        icon = "";
        medicRequired = 0;
        treatmentTime = 3;
        allowedSelections[] = {"Body"};
        condition = "alive _patient && {ACM_airway_enable} && {!(_patient call ace_common_fnc_isAwake)} && {(_patient getVariable ['ACM_airway_AirwayItem_Oral','']) != 'SGA'} && {!(_patient getVariable ['ACME_ETT_Inserted',false])} && {!(_patient getVariable ['ACME_vent_driving',false])} && {!(_patient getVariable ['ACM_airway_RecoveryPosition_State',false])} && {isNull objectParent _patient}";
        callbackSuccess = "[_medic,_patient,true] call ACM_airway_fnc_setRecoveryPosition";
        ACM_rollToBack = 0;
    };

    class CheckResponse: CheckPulse {
        // Five seconds is intentional: the complete medic3_old assessment motion lives inside the progress window
        // instead of being clipped by a three-second action.  ACME owns entry/exit so ACM never raises a rifle first.
        displayName = "$STR_ACE_Medical_Treatment_Check_Response";
        displayNameProgress = "$STR_ACE_Medical_Treatment_Check_Response_Content";
        category = "examine";
        allowedSelections[] = {"Head"};
        allowSelfTreatment = 0;
        treatmentTime = 5;
        condition = "true";
        callbackStart = "if (toLower (_this param [3, '']) == 'checkresponse') then {[(_this param [0, objNull]), 'response', 5] call ACME_fnc_treatmentPoseStart}";
        callbackSuccess = "_this call ace_medical_treatment_fnc_checkResponse; [_medic, 'response'] call ACME_fnc_treatmentPoseStop";
        callbackFailure = "[_medic, 'response'] call ACME_fnc_treatmentPoseStop";
        animationMedic = "";
        animationMedicProne = "";
        animationMedicSelf = "";
        animationMedicSelfProne = "";
    };
    // Spawned Megacode patients use a civilian model. Keep the exception local to this action.
    class CheckDogTags: CheckResponse {
        condition = "ACME_fnc_canCheckPatientDogtags";
    };
    // Two-second physical stimulus. Keep ACM's native eligibility/callback/animation contract; only the duration changes.
    class ShakeAwake;
    class SlapAwake: ShakeAwake {
        displayName = "$STR_ACM_Disability_SlapAwake";
        displayNameProgress = "$STR_ACM_Disability_SlapAwake_Progress";
        allowedSelections[] = {"Head"};
        treatmentTime = 2;
        condition = "!([_patient] call ace_common_fnc_isAwake)";
        callbackSuccess = "ACM_disability_fnc_slapAwake";
        animationMedic = "AinvPknlMstpSnonWnonDr_medic3";
        ACM_rollToBack = 1;
        ACM_ignoreAnimCoef = 1;
    };
    class CheckBreathing {
        animationMedic = "AmovPknlMstpSrasWpstDnon_AmovPknlMstpSrasWpstDnon_gear";
        animationMedicProne = "AmovPknlMstpSrasWpstDnon_AmovPknlMstpSrasWpstDnon_gear";
        condition = "alive _patient";
    };
    class UseStethoscope {
        // Auscultation owns a clean supine chest-access pose. Do not inherit CheckBreathing's generic roll-to-back:
        // elevated casualties use the authored head-lowering sequence first, then the stethoscope controller holds
        // the normal face-up rest directly for the lifetime of the scope.
        ACM_rollToBack = 0;
        ACME_neverRollToBack = 1;
        animationMedic = "";
        animationMedicProne = "";
        animationMedicSelf = "";
        animationMedicSelfProne = "";
        // Generic treatment preflight already owns the single empty-hands transition. A second stethoscope-specific
        // put-away request could queue another sidearm/primary/launcher holster chain.
        callbackStart = "";
        callbackSuccess = "private _a = +_this; private _p = _a param [1,objNull]; private _ready = if (isNull _p) then {-1} else {_p getVariable ['ACME_headElev_suspendReadyAt',-1]}; if (!isNull _p && {_p getVariable ['ACME_headElev_Suspended',false]} && {_ready > CBA_missionTime}) then {[{_this call ACM_breathing_fnc_useStethoscope},_a,((_ready - CBA_missionTime) max 0.05) + 0.05] call CBA_fnc_waitAndExecute} else {_a call ACM_breathing_fnc_useStethoscope}";
    };
    // CheckPulse is deliberately not touched. it is the base class for more than fifty actions in this addon
    // alone: the thoracostomy, chest seals, junctional packing, the ej line, the EMMA, the ventilator battery and
    // every debug rhythm toggle. giving it an animation gives all of them a light one-handed gear check, so a
    // medic would reach out and touch someone while cutting a hole in their chest.
    // feel pulse therefore still has none. fixing that properly means either blanking the animation on about
    // thirty descendants or giving feel pulse its own class, and that is a decision rather than a detail.
    class CheckCapillaryRefill {
        animationMedic = "AmovPknlMstpSrasWpstDnon_AmovPknlMstpSrasWpstDnon_gear";
        animationMedicProne = "AmovPknlMstpSrasWpstDnon_AmovPknlMstpSrasWpstDnon_gear";
    };

// one advanced airway at a time.
// ACM already makes the oral adjuncts mutually exclusive with each other. InsertOPA and InsertIGel both require
// airwayitem_oral to be empty, so an i-gel cannot go in on top of an OPA or the reverse. the NPA sits in the
// separate nasal slot, which is why ACM lets an NPA and an OPA coexist, and that pairing is left exactly as it
// is.
// none of them checked for a definitive airway already in place. with a tube down the trachea or a surgical
// airway established, dropping an oral or nasal adjunct in alongside it is not a thing anyone does, so each
// now also requires no ETT and no cric. ACM's own clauses are preserved verbatim and only these two are added,
// so nothing that was previously refused becomes possible.
// the parents are restated, as : CheckAirway and : InsertOPA, and they must be. these three carry almost
// nothing of their own. the displayname, icon, treatmenttime, items, consumeitem, callbacksuccess and menu
// icon all arrive through CheckAirway. declaring them here without the parent does not merge with ACM's
// version, it severs that inheritance, and the action loses everything that made it an action. it then
// vanishes from the medical menu entirely, which is exactly what happened once. the AED overrides below follow
// the same rule.
    class InsertOPA: CheckAirway {
        // CheckAirway forces a crouch through its callbackStart now. this restates an empty one so this action
        // keeps the behavior it had. delete this line to give it the crouch as well.
        callbackStart = "";
        // and it keeps the animation it inherited before CheckAirway moved to the rifle carrying variant.
        animationMedic = "AinvPknlMstpSnonWnonDr_medic4";
        animationMedicProne = "AinvPknlMstpSnonWnonDr_medic4";
        displayName = "$STR_ACM_Airway_InsertOPA";
        displayNameProgress = "$STR_ACM_Airway_InsertOPA_Progress";
        icon = "";
        medicRequired = "ACM_airway_allowOPA";
        treatmentTime = "ACM_airway_treatmentTimeOPA";
        items[] = {"ACM_OPA"};
        consumeItem = 1;
        condition = "ACM_airway_enable && !(_patient call ace_common_fnc_isAwake) && (_patient getVariable ['ACM_airway_AirwayItem_Oral','']) == '' && !(_patient getVariable ['ACME_ETT_Inserted', false]) && !(_patient getVariable ['ACM_airway_SurgicalAirway_TubeInserted', false])";
        callbackSuccess = "[_medic, _patient, 'OPA'] call ACM_airway_fnc_insertAirwayItem";
        ACM_cancelRecovery = 1;
        ACM_menuIcon = "ACM_OPA";
    };
    class InsertNPA: InsertOPA {
        displayName = "$STR_ACM_Airway_InsertNPA";
        displayNameProgress = "$STR_ACM_Airway_InsertNPA_Progress";
        icon = "";
        medicRequired = "ACM_airway_allowNPA";
        treatmentTime = "ACM_airway_treatmentTimeNPA";
        items[] = {"ACM_NPA"};
        condition = "ACM_airway_enable && !(_patient call ace_common_fnc_isAwake) && (_patient getVariable ['ACM_airway_AirwayItem_Nasal','']) == '' && !(_patient getVariable ['ACME_ETT_Inserted', false]) && !(_patient getVariable ['ACM_airway_SurgicalAirway_TubeInserted', false])";
        callbackSuccess = "[_medic, _patient, 'NPA'] call ACM_airway_fnc_insertAirwayItem";
        ACM_menuIcon = "ACM_NPA";
    };
    class InsertIGel: InsertOPA {
        displayName = "$STR_ACM_Airway_InsertIGel";
        displayNameProgress = "$STR_ACM_Airway_InsertIGel_Progress";
        icon = "";
        medicRequired = "ACM_airway_allowSGA";
        treatmentTime = "ACM_airway_treatmentTimeSGA";
        items[] = {"ACM_IGel"};
        condition = "ACM_airway_enable && !(_patient call ace_common_fnc_isAwake) && (_patient getVariable ['ACM_airway_AirwayItem_Oral','']) == '' && !(_patient getVariable ['ACME_ETT_Inserted', false]) && !(_patient getVariable ['ACM_airway_SurgicalAirway_TubeInserted', false]) && !(_patient getVariable ['ACME_nrb_on', false])";
        callbackSuccess = "[_medic, _patient, 'SGA'] call ACM_airway_fnc_insertAirwayItem";
        ACM_menuIcon = "ACM_IGel";
    };
    // CPR remains entirely native ACM. ACME does not restate its condition, callback or continuous-action behavior.

    // move all AED options to the advanced treatments tab. ACM splits them. apply and remove pads, manual charge,
    // shock and cancel charge are already advanced, while view monitor, analyze rhythm, measure bp and the sensor
    // connect and disconnect actions sit in examine. we override the category only on the examine ones, so
    // everything AED lives under advanced. the parents are restated, as : CheckPulse and : aed_*, so each override
    // merges with ACM's class. the displayname, condition and callbacks are untouched and only the tab changes.
    // AED_ApplyPads and AED_RemovePads are already advanced, and are forward-declared here purely as parents.
    class AED_ApplyPads;
    class AED_RemovePads;
    class AED_ViewMonitor: CheckPulse { category = "advanced"; };
    class AED_AnalyzeRhythm: AED_ViewMonitor { category = "advanced"; };
    class AED_MeasureBP: AED_AnalyzeRhythm { category = "advanced"; };
    class AED_ConnectPulseOximeter: AED_ApplyPads { category = "advanced"; };
    class AED_DisconnectPulseOximeter: AED_RemovePads { category = "advanced"; };
    class AED_ConnectPressureCuff: AED_ApplyPads { category = "advanced"; };
    class AED_DisconnectPressureCuff: AED_RemovePads { category = "advanced"; };
    class AED_ConnectCapnograph: AED_ApplyPads { category = "advanced"; };
    class AED_DisconnectCapnograph: AED_RemovePads { category = "advanced"; };

    // manual measure blood pressure. this routes its callback through our wrapper so it can run while the medic
    // holds direct pressure. ACM's measurebp into begincontinuousaction exits immediately when a continuous action
    // is already active, and torso dp holds ACM_core_ContinuousAction_Active true, so the bp window never opened
    // and the menu just reopened. the wrapper releases any held dp first, which clears that flag, then measures.
    // this is an in-place reopen. forward-declare the parent, CheckBloodPressure, then restate it on each reopen so
    // the parent link is preserved. a bare reopen, class x { ... }, strips the parent to '', and the action loses
    // everything it inherits from CheckBloodPressure and CheckPulse that it does not redefine itself: the
    // category, treatmentlocations and action-framework fields. the manual "Measure Blood Pressure" action then
    // stopped working, because the success callback never fired and there were no [ACME-BPCUFF] logs. restating
    // the same parent keeps ACM's condition, displayname, items and allowedselections and the inherited fields,
    // and changes callbacksuccess only. the 4th argument is the stethoscope flag, matching ACM's two callbacks.
    class CheckBloodPressure;
    class MeasureBloodPressure: CheckBloodPressure { callbackSuccess = "[_medic, _patient, _bodyPart, false] call ACME_fnc_measureBPWrap"; };
    class MeasureBloodPressureStethoscope: MeasureBloodPressure { callbackSuccess = "[_medic, _patient, _bodyPart, true] call ACME_fnc_measureBPWrap"; };

    // an io with no local anesthesia gives a pain-driven loss of consciousness and persistent severe pain.
    // we keep ACM's exact setiv call and append our pain response, so the original behavior is unchanged and the
    // pain fires on a dry insertion only. the response itself does nothing when lidocaine or ketamine is on board.
    // the markers are ACM_IO_EZ_M at 3 and ACM_IO_FAST1_M at 4, with insert true and iv false.
    // to modify an existing ACM action in place, the parent chain of the class must be forward-declared so config
    // inheritance can find the existing class. CheckBreathing is declared above for the same reason, so the modify
    // of ApplyChestSeal resolves with no restated parent. InsertIO_FAST1 derives from InsertIV_16_Upper, and
    // InsertIO_EZ from InsertIO_FAST1. declare the chain, then reopen each io class with no parent and
    // callbacksuccess only. every other ACM property, the displayname, condition, items and allowedselections, is
    // preserved.
    // ACM's nine native "Insert <gauge> IV (<site>)" placement actions are hidden, at condition "false", so the
    // only way to start a peripheral iv is our "Establish IV" mini-game. each is reopened in place with no
    // restated parent, so ACM's displayname and items are preserved and we force the condition false only. the io
    // actions, InsertIO_FAST1 and ez, keep their own ACM condition, so hiding their iv parent here does not hide
    // them. if a name below does not match an ACM class it is an inert, never-shown orphan and is harmless.
    // InsertIV_16_Upper is also the parent ACM uses for the io chain, so it is hidden here and still serves that
    // role.
    class InsertIV_16_Upper { condition = "false"; };
    class InsertIV_16_Middle { condition = "false"; };
    class InsertIV_16_Lower { condition = "false"; };
    class InsertIV_14_Upper { condition = "false"; };
    class InsertIV_14_Middle { condition = "false"; };
    class InsertIV_14_Lower { condition = "false"; };
    class InsertIV_18_Upper { condition = "false"; };
    class InsertIV_18_Middle { condition = "false"; };
    class InsertIV_18_Lower { condition = "false"; };
    // ACM's six IV removal buttons, hidden at v0.9.999r-42.
    // an IV comes out in the IV screen now: take hold of the hub and pull it. the buttons did the same job from
    // a menu, and having both meant the same act had two entry points that behaved differently.
    // THE IO REMOVALS STAY. RemoveIO_FAST1 inherits RemoveIV_16_Upper and RemoveIO_EZ inherits that, and both
    // restate their own condition, so hiding the parent does not reach them. an IO has no hub in the IV screen
    // and its button is the only way to take it out.
    // to restore any row, delete its line here and ACM's own condition comes back.
    class RemoveIV_16_Upper { condition = "false"; };
    class RemoveIV_16_Middle { condition = "false"; };
    class RemoveIV_16_Lower { condition = "false"; };
    class RemoveIV_14_Upper { condition = "false"; };
    class RemoveIV_14_Middle { condition = "false"; };
    class RemoveIV_14_Lower { condition = "false"; };

    // IO removal is kept independent from the native peripheral-IV removal hierarchy.  The IV rows above are
    // intentionally hidden because peripheral catheters come out through the IV minigame.  IOs have no draggable
    // hub, so they need their own medical-menu removal actions.  Using ACME-owned classes here prevents a later
    // change to RemoveIV_16_Upper from suppressing IO removal through config inheritance/load-order merging.
    class RemoveIO_FAST1 { condition = "false"; };
    class RemoveIO_EZ { condition = "false"; };
    class ACME_RemoveIO_FAST1 {
        displayName = "$STR_ACM_Circulation_RemoveIO_FAST1";
        displayNameProgress = "$STR_ACM_Circulation_RemoveIO_FAST1_Progress";
        icon = "";
        category = "advanced";
        treatmentLocations = 0;
        medicRequired = 0;
        treatmentTime = 3.5;
        allowedSelections[] = {"Body"};
        allowSelfTreatment = 0;
        items[] = {};
        consumeItem = 0;
        condition = "[_patient, _bodyPart, 4] call ACM_circulation_fnc_hasIO";
        callbackSuccess = "[_medic, _patient, _bodyPart, 4, false, false] call ACM_circulation_fnc_setIV";
        ACM_menuIcon = "ACM_IO_FAST";
    };
    class ACME_RemoveIO_EZ: ACME_RemoveIO_FAST1 {
        displayName = "$STR_ACM_Circulation_RemoveIO_EZ";
        displayNameProgress = "$STR_ACM_Circulation_RemoveIO_EZ_Progress";
        allowedSelections[] = {"LeftArm", "RightArm", "LeftLeg", "RightLeg"};
        condition = "[_patient, _bodyPart, 3] call ACM_circulation_fnc_hasIO";
        callbackSuccess = "[_medic, _patient, _bodyPart, 3, false, false] call ACM_circulation_fnc_setIV";
        ACM_menuIcon = "ACM_IO_EZ";
    };

    class InsertIO_FAST1: InsertIV_16_Upper {
        // B45 keeps ACM's insertion mechanics, then an owner-local setIVLocal handler guarantees a moderate-pain
        // floor. Fluid through the IO invokes ACME_fnc_ioPainResponse for max pain and delayed syncope.
        callbackSuccess = "[_medic, _patient, _bodyPart, 4, true, false] call ACM_circulation_fnc_setIV;";
    };
    class InsertIO_EZ: InsertIO_FAST1 {
        callbackSuccess = "[_medic, _patient, _bodyPart, 3, true, false] call ACM_circulation_fnc_setIV;";
    };
    class Naloxone;  // ACM in naloxone spray. it is the base for our in esketamine, with the same head-targeted spray mechanics.

    // intranasal esketamine. it gives battlefield analgesia with no iv access, and a medic administers it exactly
    // like the ACM naloxone spray. it inherits the head-targeted spray flow of naloxone. we point it at the
    // esketamine atomizer and raise ACM's medicationlocal with the classname 'esketamine', so it applies the
    // esketamine effect config: analgesia, shock-tolerant and gag-preserving. it is indicated for a
    // non-mission-capable casualty in moderate to severe pain, at an ace pain of 0.35 or more, when no BVM is
    // running and they are not in arrest.
    class ACME_Esketamine_IN: Naloxone {
        displayName = "Use Esketamine (IN)";
        displayNameProgress = "Administering intranasal esketamine...";
        items[] = {"ACME_Spray_Esketamine"};
        treatmentTime = 4;
        medicRequired = 0;
        condition = "true";
        callbackSuccess = "['ace_medical_treatment_medicationLocal', [_patient, _bodyPart, 'Esketamine', 1, false], _patient] call CBA_fnc_targetEvent";
        ACM_rollToBack = "false";  // a conscious pain patient. do not force them supine.
        sounds[] = {};
        ACM_menuIcon = "ACME_Spray_Esketamine";
    };

    // Keep the existing assessment action; B31 gives its medic one pose owner.
    class InspectChest {
        condition = "false";
    };
    class ACME_InspectChest: CheckBreathing {
        displayName = "Inspect Chest";
        displayNameProgress = "Inspecting chest...";
        icon = "";
        category = "airway";
        treatmentLocations[] = {"All"};
        medicRequired = "ACM_breathing_allowInspectChest";
        treatmentTime = 6;
        allowedSelections[] = {"Body"};
        allowSelfTreatment = 1;
        // inspect a chest whenever you like. there is no injury gate and there never should have been one.
        // it used to require the pneumothorax system to be on, the patient to be unconscious, no CPR running and
        // the patient out of a vehicle. every one of those is the game deciding in advance whether looking is
        // worth the medic's time, and the answer to that is always yes. an assessment that only appears once
        // something is already wrong tells the medic the answer before they look, and a chest that turns out to be
        // normal is a finding: it is how you rule a tension out rather than needle on suspicion.
        // it is the same rule the chest seal and the NCD already follow, and for the same reason. the decision, and
        // being wrong about it, is the thing being taught.
        // the findings themselves are unchanged. a chest with nothing wrong reports nothing wrong.
        condition = "!isNull _patient && {_patient isKindOf 'CAManBase'}";
        callbackStart = "_this call ACME_fnc_inspectChestPoseStart";
        callbackSuccess = "[_medic,_patient] call ACM_breathing_fnc_inspectChest; [_medic] call ACME_fnc_inspectChestPoseStop";
        callbackFailure = "[_medic, true] call ACME_fnc_inspectChestPoseStop";
        callbackProgress = "";
        // The episode controller owns crouch, work and exit, including self/prone starts.
        animationMedic = "";
        animationMedicProne = "";
        animationMedicSelf = "";
        animationMedicSelfProne = "";
        // do not force the patient onto their back. that was safe while this was unconscious-only and it is not
        // now: rolling a conscious casualty supine to look at their chest, or rolling the medic on a self
        // inspection, is the same trap ACME_ApplyChestSeal documents just below.
        // fn_inspectchestlocal already rolls an obtunded prone casualty itself, through the shared posture
        // controller, so the case that genuinely needs a roll still gets one.
        ACM_rollToBack = "false";
        ACM_cancelRecovery = 1;
    };
    // custom chest-seal. it opens our search mini-game on any patient and lives in airway management on the chest.
    // the visibility-determining properties, the category, allowedselections, ACM_menuIcon and items, are restated
    // explicitly here instead of leaning on inheritance from CheckBreathing. in this build a silently dropped
    // inherited property would make the action vanish from the menu entirely, which is the most likely reason it
    // was not showing under airway on the chest. there is no colon, so it is an in-place modify, and performncd
    // and PerformThoracostomy, which inherit from ApplyChestSeal, are left untouched.
    // ACM's stock ApplyChestSeal is hidden, at condition "false", so only our mini-game ACME_ApplyChestSeal shows.
    // on the thoracostomy, rebuilt fresh: ACM's PerformThoracostomy inherits from ApplyChestSeal and so inherits
    // items[] = {"ACE_surgicalKit"}. that is the real reason it kept not showing, because ACE's item gate hides
    // the action unless the medic carries a surgical kit. the previous fix restated the condition only and left
    // that item gate intact.
    // we now do two things. first, hide ACM's PerformThoracostomy outright, with a restated parent so the modify
    // merges, then force it false. that also hides performthoracostomy_kit, which inherits it without restating a
    // condition. second, build a fresh thoracostomy from CheckPulse, in the proven ACME_PerformNARSPEAR and
    // ACME_ApplyChestSeal pattern with every property explicit, with no item gate, delegating a successful
    // placement to ACM's native thoracostomy_start. ACM's InsertChestTube, DrainFluid_ACCUVAC and CloseIncision all
    // restate their own conditions, so they are not hidden and the downstream chest-tube chain still works once
    // our action seeds thoracostomy_state. native performncd stays hidden, because the NAR SPEAR replaces it.
    class ApplyChestSeal {
        condition = "false";
    };
    class PerformThoracostomy: ApplyChestSeal {
        condition = "false";
    };

    // thoracostomy, built fresh from CheckPulse so it is immune to the item-gate and inheritance trap. it is
    // persistent and shows on any living person with no clinical-indication gate, no medic-skill gate, no CPR gate
    // and no item requirement. the condition is a bare inline alive-check, with no dependency on a helper fn that
    // might not be loaded, so nothing can hide it. it hands a successful placement to ACM's native finger
    // thoracostomy, so the chest-tube follow-on chain, InsertChestTube, drain and close, is unchanged.
    // to make it medic-only or gate it on a real pneumo again, set medicrequired = 1 or restore the
    // chestSealCanApply condition.
    class ACME_PerformThoracostomy: CheckPulse {
        displayName = "Perform Thoracostomy";
        displayNameProgress = "Performing thoracostomy...";
        category = "airway";
        treatmentLocations[] = {"All"};
        // a finger thoracostomy is a Medic skill and above.
        // cutting into a chest and putting a finger through the pleura is not something an untrained rifleman does
        // off the back of carrying the kit. carrying it is not the qualification, so this is a trait gate rather
        // than an item gate: no amount of equipment makes the option appear for someone without the training.
        // 1 is Medic and 2 is Doctor, per ace_medical_treatment_fnc_isMedic.
        medicRequired = "ACM_breathing_allowThoracostomy";
        allowSelfTreatment = 0;
        treatmentTime = 1;
        allowedSelections[] = {"Body"};
        // the provider must carry a thoracostomy kit. this is a treatment action, evaluated by ACE's cantreat, whose
        // scope binds the medic as _medic and not _player. _player is undefined here, and a reference to it made the
        // whole condition throw and the action vanish. the kit check uses ACE's own hasitem, so it also finds the kit
        // in a vehicle or facility supply, which matches every sibling below. consumeitem stays 0, so the kit is not
        // eaten, because it is reusable equipment here.
        condition = "([_medic, 'ACME_PerformThoracostomy'] call ACME_fnc_procedureActionAllowed) && {!isNull _patient && {_patient isKindOf 'CAManBase'} && {(_patient getVariable ['ACM_breathing_Thoracostomy_State', 0]) < 1} && {([_medic, _patient] call ACME_fnc_thoraKitItem) != ''}}";
        callbackStart = "";
        // opens the thoracostomy mini-game, idd 86600. the mini-game itself calls
        // ACM_breathing_fnc_Thoracostomy_start at the finger sweep, and the tube follow-ons at tube placement. the
        // legacy direct-start path is kept in a comment for a revert: [_this select 0, _this select 1, false] call
        // ACM_breathing_fnc_Thoracostomy_start.
        callbackSuccess = "[_this select 0, _this select 1, _this select 2] call ACME_fnc_thoraOpen";
        callbackFailure = "";
        callbackProgress = "";
        consumeItem = 0;
        // the condition above enforces the kit requirement, as an item in the inventory of the medic. we do not also
        // list it in items[]. that array is ACE's consumable-requirement gate, and combining it with a reusable-item
        // condition double-gates the action in a way that can make it unusable even with the kit present. one gate, in
        // the condition, is correct here.
        items[] = {};
        ACM_menuIcon = "ACM_ThoracostomyKit";
        ACM_cancelRecovery = 1;
    };
    // the same action, shown once a thoracostomy is already present. it is relabeled "Adjust Thoracostomy" and
    // re-opens the mini-game with the saved state. perform and adjust are mutually exclusive on
    // thoracostomy_state.
    class ACME_AdjustThoracostomy: ACME_PerformThoracostomy {
        displayName = "Adjust Thoracostomy";
        displayNameProgress = "Opening thoracostomy...";
        condition = "([_medic, 'ACME_AdjustThoracostomy'] call ACME_fnc_procedureActionAllowed) && {!isNull _patient && {(_patient getVariable ['ACM_breathing_Thoracostomy_State', 0]) > 0} && {[_medic, _patient, true] call ACME_fnc_thoraCanOpen}}";
            medicRequired = 0;
    };

    // thoracostomy follow-ons, rebuilt fresh under airway so they sit next to perform thoracostomy. ACM's own
    // InsertChestTube, drainfluid and CloseIncision inherit ApplyChestSeal and so land in category examine. after
    // our airway thoracostomy they were hiding in the examine tab, which is why they appeared to vanish. these
    // inherit ACME_PerformThoracostomy, so airway and body, and delegate to ACM's native functions. ACM's examine
    // versions are hidden below to avoid duplicates. they gate on ACM_breathing_Thoracostomy_State, where 1 is
    // incision and finger done, 2 is tube draining and 3 is tube sealed, exactly like ACM.
    class ACME_InsertChestTube: ACME_PerformThoracostomy {
        displayName = "Insert Chest Tube";
        displayNameProgress = "Opening thoracostomy...";
        items[] = {"ACM_ChestTubeKit"};
        consumeItem = 0;
        condition = "([_medic, 'ACME_InsertChestTube'] call ACME_fnc_procedureActionAllowed) && {!isNull _patient && {(_patient getVariable ['ACM_breathing_Thoracostomy_State', 0]) == 1} && {(((_patient getVariable ['ACME_thora_open_left', '']) == 'finger') && {!(_patient getVariable ['ACME_thora_closed_left', false])} && {!(_patient getVariable ['ACME_thora_sealed_left', false])}) || (((_patient getVariable ['ACME_thora_open_right', '']) == 'finger') && {!(_patient getVariable ['ACME_thora_closed_right', false])} && {!(_patient getVariable ['ACME_thora_sealed_right', false])})}}";
        // re-opens the thoracostomy mini-game so the medic can place the tube, or continue, with the saved state.
        callbackSuccess = "[_this select 0, _this select 1, _this select 2] call ACME_fnc_thoraOpen";
        ACM_menuIcon = "ACM_ChestTubeKit";
            medicRequired = "ACME_skillChestTube";
    };
    class ACME_DrainFluid_ACCUVAC: ACME_PerformThoracostomy {
        displayName = "Drain Fluid (ACCUVAC)";
        displayNameProgress = "Draining fluid...";
        items[] = {"ACM_ACCUVAC"};
        condition = "([_medic, 'ACME_DrainFluid_ACCUVAC'] call ACME_fnc_procedureActionAllowed) && {!isNull _patient && {(_patient getVariable ['ACM_breathing_Thoracostomy_State', 0]) in [2,3]}}";
        callbackSuccess = "[_this select 0, _this select 1, 'drain', 1] call ACME_fnc_thoraAftercare";
        ACM_menuIcon = "ACM_ACCUVAC";
            medicRequired = "ACM_breathing_allowThoracostomy";
    };
    class ACME_DrainFluid_SuctionBag: ACME_DrainFluid_ACCUVAC {
        displayName = "Drain Fluid (Suction Bag)";
        treatmentTime = 8;
        items[] = {"ACM_SuctionBag"};
        consumeItem = 0;
        callbackSuccess = "[_this select 0, _this select 1, 'drain', 0] call ACME_fnc_thoraAftercare";
        ACM_menuIcon = "ACM_SuctionBag";
            condition = "([_medic, 'ACME_DrainFluid_SuctionBag'] call ACME_fnc_procedureActionAllowed) && {!isNull _patient && {(_patient getVariable ['ACM_breathing_Thoracostomy_State', 0]) in [2,3]}}";
    };
    class ACME_ResealChestTube: ACME_PerformThoracostomy {
        displayName = "Reseal Chest Tube";
        displayNameProgress = "Resealing chest tube...";
        condition = "([_medic, 'ACME_ResealChestTube'] call ACME_fnc_procedureActionAllowed) && {!isNull _patient && {(_patient getVariable ['ACM_breathing_Thoracostomy_State', 0]) == 3}}";
        callbackSuccess = "[_this select 0, _this select 1, 'reseal'] call ACME_fnc_thoraAftercare";
        ACM_menuIcon = "ACM_ChestTubeKit";
            medicRequired = "ACM_breathing_allowThoracostomy";
    };
    class ACME_CloseIncision: ACME_PerformThoracostomy {
        displayName = "Close Incision (Suture)";
        displayNameProgress = "Suturing incision closed...";
        condition = "([_medic, 'ACME_CloseIncision'] call ACME_fnc_procedureActionAllowed) && {!isNull _patient && {(([_medic, _patient, ['ACE_surgicalKit']] call ace_medical_treatment_fnc_hasItem) || {_patient getVariable ['ACM_breathing_Thoracostomy_UsedKit', false]})} && {(_patient getVariable ['ACM_breathing_Thoracostomy_State', 0]) > 0} && {!(_patient getVariable ['ACME_thora_tube_left', false])} && {!(_patient getVariable ['ACME_thora_tube_right', false])} && {!(_patient getVariable ['ACME_thora_closed_left', false])} && {!(_patient getVariable ['ACME_thora_closed_right', false])}}";
        callbackSuccess = "[_this select 0, _this select 1, 'close'] call ACME_fnc_thoraAftercare";
        ACM_menuIcon = "ACE_surgicalKit";
            medicRequired = "ACM_breathing_allowThoracostomy";
    };
    // suture the chest tube in place, which is distinct from closing the incision. it permanently affixes the tube
    // on any side that has one, so it can no longer be pulled in the mini-game, and it marks the casualty
    // surgical. it shows only while an un-sutured tube is present.
    class ACME_SutureChestTube: ACME_PerformThoracostomy {
        displayName = "Suture Chest Tube";
        displayNameProgress = "Suturing chest tube in place...";
        condition = "([_medic, 'ACME_SutureChestTube'] call ACME_fnc_procedureActionAllowed) && {!isNull _patient && {(([_medic, _patient, ['ACE_surgicalKit']] call ace_medical_treatment_fnc_hasItem) || {_patient getVariable ['ACM_breathing_Thoracostomy_UsedKit', false]})} && {((_patient getVariable ['ACME_thora_tube_left', false]) && {!(_patient getVariable ['ACME_thora_sealed_left', false])}) || ((_patient getVariable ['ACME_thora_tube_right', false]) && {!(_patient getVariable ['ACME_thora_sealed_right', false])})}}";
        callbackSuccess = "_this call ACME_fnc_thoraSutureTube";
        ACM_menuIcon = "ACE_surgicalKit";
            medicRequired = "ACM_breathing_allowThoracostomy";
    };
    // hide ACM's examine-category versions. each is restated false so the inheritance trap cannot leak through.
    class InsertChestTube { condition = "false"; };
    class ResealChestTube { condition = "false"; };
    class DrainFluid_ACCUVAC { condition = "false"; };
    class DrainFluid_SuctionBag { condition = "false"; };
    class CloseIncision { condition = "false"; };

    // the working chest-seal action, built fresh from CheckPulse. it uses the exact proven pattern of
    // ACME_DirectPressure and ACME_AssessPupils, with every property explicit, so it is immune to the in-place
    // property drop that broke the stock override. it shows under airway on the chest of any patient with no
    // injury gate, needs a chest seal in hand, and opens the placement mini-game, ACME_fnc_chestSealOpen.
    class ACME_ApplyChestSeal: CheckPulse {
        displayName = "Apply Chest Seal";
        displayNameProgress = "Applying chest seal...";
        category = "airway";
        treatmentLocations[] = {"All"};
        medicRequired = 0;
        allowSelfTreatment = 1;
        treatmentTime = 0.4;
        allowedSelections[] = {"Body"};
        // do not force the patient onto their back. ACM defaults treatments to ACM_rollToBack = 1, which is inherited.
        // on a self chest seal that rolls the medic supine and locks the pose until another treatment, such as a check
        // pulse, clears it. the placement is a body-image mini-game, so no pose is needed either way.
        ACM_rollToBack = "false";
        condition = "[_patient] call ACME_fnc_chestSealCanApply";
        callbackStart = "";
        callbackSuccess = "_this call ACME_fnc_chestSealOpen";
        callbackFailure = "";
        callbackProgress = "";
        // The 0.4 s launcher has no provider theatre. Explicitly blank every inherited ACE animation so the
        // minigame cannot start with a generic medic motion before B48's exact Flip animation is requested.
        animationMedic = "";
        animationMedicProne = "";
        animationMedicSelf = "";
        animationMedicSelfProne = "";
        consumeItem = 0;
        ACM_menuIcon = "ACM_ChestSeal";
        items[] = {"ACM_ChestSeal"};
    };

    // burp the seal. it sits directly under apply chest seal, which is where a medic would look for it, and
    // appears only when there is a seal on and hardcore chest seals are on. it takes two seconds and no kit,
    // because lifting a corner is not a procedure. it is a thing you do with one finger while you are already
    // there.
    class ACME_BurpChestSeal: ACME_ApplyChestSeal {
        displayName = "Burp Chest Seal";
        displayNameProgress = "Burping seal...";
        treatmentTime = 2;
        items[] = {};
        // every seal can be burped, in every mode. the valve clogs whatever the settings say and hardcore only
        // decides how fast, so gating the fix behind hardcore left a clogged seal with nothing to do about it.
        condition = "false";  // Burping is performed only inside the chest-seal minigame.
        callbackSuccess = "_this call ACME_fnc_chestSealBurp";
        callbackFailure = "";
        callbackProgress = "";
        animationMedic = "AmovPknlMstpSrasWpstDnon_AmovPknlMstpSrasWpstDnon_gear";
    };

    // the NAR SPEAR enters the same interactive chest procedure, then delegates a successful placement to ACM's
    // native performncd function. the item is consumed only when the needle is actually placed.
    class ACME_PerformNARSPEAR: CheckPulse {
        displayName = "Perform NCD (NAR SPEAR)";
        displayNameProgress = "Preparing NAR SPEAR...";
        category = "airway";
        treatmentLocations[] = {"All"};
        medicRequired = "ACM_breathing_allowNCD";
        allowSelfTreatment = 0;
        treatmentTime = 0.4;
        allowedSelections[] = {"Body"};
        condition = "([_medic, 'ACME_PerformNARSPEAR'] call ACME_fnc_procedureActionAllowed) && {[_patient] call ACME_fnc_chestSealCanApply}";
        callbackStart = "";
        callbackSuccess = "[_this select 0, _this select 1, _this select 2, 'spear'] call ACME_fnc_chestSealOpen";
        callbackFailure = "";
        callbackProgress = "";
        consumeItem = 0;
        ACM_menuIcon = "ACME_NARSPEAR";
        items[] = {"ACME_NARSPEAR"};
        ACM_cancelRecovery = 1;
    };
    // apply direct pressure. it is manual hemorrhage control and a last resort. torso pressure uses the stronger
    // two-handed hold pose; head/limb pressure uses the freer one-handed hold. Neither owns ACM's exclusive
    // continuous-action lock, so the medical menu and other interventions remain available. both clot the held part, at a very high
    // chance past 15 s. the callback branches by body part.
    class ACME_DirectPressure: CheckPulse {
        displayName = "Apply Direct Pressure";
        displayNameProgress = "Getting into position...";
        category = "bandage";
        treatmentLocations[] = {"All"};
        medicRequired = 0;
        treatmentTime = 0.1;
        allowedSelections[] = {"Head","Body","LeftArm","RightArm","LeftLeg","RightLeg"};
        condition = "(missionNamespace getVariable ['ACME_sys_dp', true]) && {!(_medic getVariable ['ACME_DP_Active', false])} && {!(_medic getVariable ['ACME_hang_Active', false])} && {(toLower _bodyPart != 'body') || {!(missionNamespace getVariable ['ACM_core_ContinuousAction_Active', false])}}";
        // one-shot sfx the moment the button is pressed, for hands on the wound.
        callbackStart = "params ['_medic','_patient']; if (!isNull _patient) then {[_patient, 0.85] call ACME_fnc_markImportantSfx}; if (!isNull _medic) then {[_medic, 'ACME_DirectPressure'] remoteExec ['say3D', 0]}";
        callbackSuccess = "_this call ACME_fnc_directPressureStart";
        callbackFailure = "";
        callbackProgress = "";
        ACM_menuIcon = "CPR";
        items[] = {};
    };
    class ACME_StopDirectPressure: CheckPulse {
        displayName = "Stop Direct Pressure";
        displayNameProgress = "Releasing pressure...";
        category = "bandage";
        treatmentLocations[] = {"All"};
        medicRequired = 0;
        treatmentTime = 0.1;
        allowedSelections[] = {"Head","Body","LeftArm","RightArm","LeftLeg","RightLeg"};
        condition = "(_medic getVariable ['ACME_DP_Active', false]) && {(_medic getVariable ['ACME_DP_Patient', objNull]) isEqualTo _patient}";
        callbackStart = "";
        callbackSuccess = "[false, _medic] call ACME_fnc_directPressureStop";
        callbackFailure = "";
        callbackProgress = "";
        ACM_menuIcon = "CPR";
        items[] = {};
    };
    class ACME_AssessPupils: CheckPulse {
        displayName = "Assess Pupils";
        displayNameProgress = "Assessing pupils...";
        category = "examine";
        treatmentLocations[] = {"All"};
        medicRequired = 0;
        treatmentTime = 4;
        allowedSelections[] = {"Head"};
        condition = "true";
        callbackSuccess = "_this call ACME_fnc_tbiAssessPupils";
        callbackFailure = "";
        callbackProgress = "";
        // the same medic animation ACM's inspect chest plays.
        animationMedic = "AinvPknlMstpSnonWnonDr_medic4";
        items[] = {};
    };
    // check temperature. it reads the core temp and freezes it as a persistent readout in the medical-menu
    // vitals, in fn_tempinjuryentry. it updates manually, like a bp cuff: take a fresh reading whenever you want a
    // new value.
    class ACME_CheckTemperature: CheckPulse {
        // its own, because CheckPulse is deliberately left blank. inheriting from it would hand the same animation to
        // every procedure in the addon.
        animationMedic = "AmovPknlMstpSrasWpstDnon_AmovPknlMstpSrasWpstDnon_gear";
        animationMedicProne = "AmovPknlMstpSrasWpstDnon_AmovPknlMstpSrasWpstDnon_gear";
        displayName = "Check Temperature";
        displayNameProgress = "Checking temperature...";
        category = "examine";
        treatmentLocations[] = {"All"};
        medicRequired = 0;
        treatmentTime = 3;
        allowedSelections[] = {"Head","Body"};
        condition = "([_medic, 'ACM_Thermometer'] call ACME_fnc_itemCount) > 0";
        callbackSuccess = "_this call ACME_fnc_checkTemperature";
        callbackFailure = "";
        callbackProgress = "";
        items[] = {};
    };
    // pressure infuser. wrap and pump the bag to force the unit in fast. it needs the device in hand and not
    // already on. it is reusable and not consumed, and it sets the per-patient flow multiplier the getIVFlowRate
    // override reads.
    // head-of-bed elevation to about 30 deg is a TBI position that eases ICP and CPP down slowly and makes
    // herniation impossible while held. the patient plays a grab pose, and the medic plays a short forced
    // sequence of stand, transition, crouch and release, which esc cancels. see fn_headelevatestart.
    class ACME_ElevateHead: CheckPulse {
        // Disable ACM's generic treatment roll. ACME owns the positioning gate and rolls ONLY a casualty that is
        // actually prone, to the back/supine endpoint, before starting the authored Semi-Fowler sequence.
        ACM_rollToBack = 0;
        // The renderer resolves clinical wording by action class, in both flat
        // and indented lists, without depending on this label's case or glyphs.
        displayName = "Elevate Head to 30°";
        displayNameProgress = "Elevating head...";
        category = "examine";
        treatmentLocations[] = {"All"};
        medicRequired = 0;
        treatmentTime = 0.5;
        allowedSelections[] = {"Head"};
        condition = "[_patient, _medic] call ACME_fnc_headElevateCanStart";
        callbackSuccess = "_this call ACME_fnc_headElevateStart";
        callbackFailure = "";
        callbackProgress = "";
        // B44: the synchronized ACME head-elevation sequence owns the visible movement.
        // Blank every inherited ACE medic animation so the treatment engine cannot run a second pose first.
        animationMedic = "";
        animationMedicProne = "";
        animationMedicSelf = "";
        animationMedicSelfProne = "";
        items[] = {};
    };
    // lower the head again. it plays the release pose and ends the elevation effects.
    class ACME_LowerHead: CheckPulse {
        ACM_rollToBack = 0;  // lowering the head never requires a treatment-engine roll.
        displayName = "Lower Head to Flat";
        displayNameProgress = "Lowering head...";
        category = "examine";
        treatmentLocations[] = {"All"};
        medicRequired = 0;
        treatmentTime = 0.5;
        allowedSelections[] = {"Head"};
        condition = "!(_patient isEqualTo _medic) && {_patient getVariable ['ACME_headElevated', false]}";
        callbackSuccess = "[_this select 0, _this select 1] call ACME_fnc_headElevateStop";
        callbackFailure = "";
        callbackProgress = "";
        // B44: the synchronized ACME head-elevation sequence owns the visible movement.
        // Blank every inherited ACE medic animation so the treatment engine cannot run a second pose first.
        animationMedic = "";
        animationMedicProne = "";
        animationMedicSelf = "";
        animationMedicSelfProne = "";
        items[] = {};
    };
    // open the live tilt tuner, with sliders for the angle, pivot and lift, on an already elevated casualty.
    class ACME_TuneHeadTilt: CheckPulse {
        displayName = "Tune Head / Plate Carrier";
        displayNameProgress = "Opening tuner...";
        category = "examine";
        treatmentLocations[] = {"All"};
        medicRequired = 0;
        treatmentTime = 0.3;
        allowedSelections[] = {"Head"};
        condition = "([] call ACME_fnc_debugEnabled) && {!(_patient isEqualTo _medic)} && {_patient getVariable ['ACME_headElevated', false]}";
        callbackSuccess = "_this call ACME_fnc_headElevTuneOpen";
        callbackFailure = "";
        callbackProgress = "";
        items[] = {};
    };
    // junctional hemorrhage: the two-stage combat gauze treatment.
    // it runs open, then pack with gauze across 15 s to packed, then a pressure bandage across 15 s to wrapped. it
    // is limbs only.
    // _bodyPart arrives lowercase, and tolower keeps it robust either way.
    class ACME_PackJunctional: CheckPulse {
        displayName = "Pack Wound (Combat Gauze)";
        ACM_menuIcon = "ACME_CombatGauze";
        displayNameProgress = "Packing junctional wound...";
        category = "bandage";
        treatmentLocations[] = {"All"};
        medicRequired = 0;
        treatmentTime = 10;
        allowedSelections[] = {"LeftArm","RightArm","LeftLeg","RightLeg"};
        condition = "(_patient getVariable [format ['ACME_Junc_%1', toLower _bodyPart], '']) == 'open'";
        // the start marks the part as actively being packed, so the bleed pfh subsides the flow while the hands
        // and gauze tamponade it, and starts the packing loop. the flag and the sound both clear on success, in
        // junctionalPackDone, and on failure below. the flag is set on the patient and synced, so the
        // patient-owned pfh sees it.
        callbackStart = "_this call ACME_fnc_junctionalPackSfxStart; [_medic, 'junctional'] call ACME_fnc_treatmentPoseStart";
        callbackSuccess = "_this call ACME_fnc_junctionalPackDone; [_medic, 'junctional'] call ACME_fnc_treatmentPoseStop";
        callbackFailure = "params ['_medic','_patient','_bodyPart']; [_medic] call ACME_fnc_junctionalPackSfxStop; if (!isNull _patient) then {_patient setVariable [format ['ACME_Junc_Packing_%1', toLower _bodyPart], false, true]}; [_medic, 'junctional'] call ACME_fnc_treatmentPoseStop";
        callbackProgress = "";
        animationMedic = "";
        animationMedicProne = "";
        animationMedicSelf = "";
        animationMedicSelfProne = "";
        items[] = {"ACM_CombatGauze"};
        consumeItem = 1;
        icon = "\acm_extended\ui\items\combat_gauze_ca.paa";
    };
    class ACME_WrapJunctional: CheckPulse {
        displayName = "Dress Junctional Wound";
        ACM_menuIcon = "ACM_PressureBandage";
        displayNameProgress = "Dressing junctional wound...";
        category = "bandage";
        treatmentLocations[] = {"All"};
        medicRequired = 0;
        treatmentTime = 10;
        allowedSelections[] = {"LeftArm","RightArm","LeftLeg","RightLeg"};
        condition = "(_patient getVariable [format ['ACME_Junc_%1', toLower _bodyPart], '']) == 'packed'";
        callbackStart = "_this call ACME_fnc_junctionalWrapSfxStart; [_medic, 'junctional'] call ACME_fnc_treatmentPoseStart";
        callbackSuccess = "_this call ACME_fnc_junctionalWrapDone; [_medic, 'junctional'] call ACME_fnc_treatmentPoseStop";
        callbackFailure = "(_this select 0) call ACME_fnc_junctionalWrapSfxStop; [_medic, 'junctional'] call ACME_fnc_treatmentPoseStop";
        callbackProgress = "";
        animationMedic = "";
        animationMedicProne = "";
        animationMedicSelf = "";
        animationMedicSelfProne = "";
        items[] = {"ACM_PressureBandage","ACM_ElasticWrap"};
        consumeItem = 1;
        icon = "\x\acm\addons\damage\ui\pressurebandage.paa";
    };
    // test. inflict a junctional wound from the menu, to exercise the system in game.
    // a scenario can instead call: [_unit, "leftarm"] call ACME_fnc_junctionalInflict;
    class ACME_InflictJunctional: CheckPulse {
        displayName = "Inflict Junctional Wound [TEST]";
        displayNameProgress = "...";
        category = "advanced";
        treatmentLocations[] = {"All"};
        medicRequired = 0;
        treatmentTime = 0.5;
        allowedSelections[] = {"LeftArm","RightArm","LeftLeg","RightLeg"};
        condition = "([] call ACME_fnc_debugEnabled) && {!((_patient getVariable [format ['ACME_Junc_%1', toLower _bodyPart], '']) in ['open','packed','wrapped'])}";
        callbackSuccess = "[_patient, _bodyPart] call ACME_fnc_junctionalInflict";
        callbackFailure = "";
        callbackProgress = "";
        items[] = {};
    };

// auto-bp toggle, an AED-driven 5-min cycle. it lives in the advanced treatments tab rather than examine,
// gates on AED presence, and sits on the arm selections.
    class ACME_AutoBP: CheckPulse {
        displayName = "Auto Blood Pressure (AED)";
        displayNameProgress = "";
        category = "advanced";
        treatmentLocations[] = {"All"};
        medicRequired = 0;
        treatmentTime = 0.01;
        allowedSelections[] = {"LeftArm", "RightArm"};
        allowSelfTreatment = 0;
        condition = "_this call ACME_fnc_autoBPCondition";
        callbackSuccess = "_this call ACME_fnc_toggleAutoBP";
        callbackFailure = "";
        callbackProgress = "";
        animationMedic = "";
        items[] = {};
        ACM_menuIcon = "ACM_AED";
    };

    // iv placement mini-game launcher. it lives in the advanced treatments section and opens the feel-for-the-vein
    // placement on the selected limb, starting at the distal or lower site. site progression is handled inside the
    // mini-game. it requires an iv catheter on hand, like ACM's own insertiv, and it is not debug-gated.
    class ACME_IVMinigameStart: CheckPulse {
        // no animation for anything to do with an IV. the work is done in the screen, and a treatment pose
        // played on the body at the same time reads as the medic doing something else entirely.
        // these inherit CheckPulse, which declares one, so it is silenced rather than left to the parent.
        animationMedic = "";
        animationMedicProne = "";
        displayName = "Establish IV";
        displayNameProgress = "...";
        category = "advanced";
        ACM_menuIcon = "ACME_EstablishIV";
        treatmentLocations[] = {"All"};
        medicRequired = 0;
        treatmentTime = 0.1;
        allowedSelections[] = {"LeftArm","RightArm","LeftLeg","RightLeg"};
        // there is no needle-type gate. the action is always available, subject to the clinical caninsertiv check
        // below, and the mini-game itself gates needle grabbing on the per-gauge count. any size therefore works
        // whatever number or kind you carry. previously items[]={"ACM_IV_16g"} hard-required a 16g to even open it.
        items[] = {};
        // ALWAYS AVAILABLE. there is no clinical gate on this action and there must not be one.
        // it used to read canInsertIV on each of the three access sites and show only while one of them was free.
        // that made sense while the screen was a placement tool. it is not one any more. the screen is where the
        // limb is worked: apply and remove the band, prep the site, feel for the vein, stick, connect a line, and
        // pull a catheter back out. a limb carrying three IVs is exactly the limb a provider needs to open, and
        // the old condition hid the button on it.
        // an empty limb is fine too. a provider opening the screen and finding nothing to do is not a fault.
        // the mini-game still owns every rule inside it. per-location occupancy, the band gate on the stick and
        // the per-gauge catheter count are all enforced there, where the provider can see why.
        // to restore the old gate:
        // condition = "([_patient, _bodyPart, 0, 0] call ACM_circulation_fnc_canInsertIV) || {[_patient, _bodyPart, 0, 1] call ACM_circulation_fnc_canInsertIV} || {[_patient, _bodyPart, 0, 2] call ACM_circulation_fnc_canInsertIV}";
        condition = "true";
        callbackStart = "_this call ACME_fnc_ivMinigamePrepare";
        callbackSuccess = "[_medic, _patient, toLower _bodyPart, 'lower'] call ACME_fnc_ivMinigameOpen";
        callbackFailure = "";
        callbackProgress = "";
    };

    // orotracheal intubation, stage 1 of the airway into vent flow. it inherits CheckAirway, a head action base,
    // and shows under advanced treatments. it appears while the medic carries a laryngoscope and an et tube and
    // the patient is not already intubated, so it disappears once the tube is in. treatment-action conditions and
    // callbacks bind the medic as _medic and not _player. _player is undefined in ACE's cantreat and
    // treatmentsuccess scope, which is why this never appeared before.
    // the battery swap sits in the advanced tab rather than airway, because it is machine maintenance and not a
    // treatment.
    class ACME_SwapVentBattery: CheckPulse {
        displayName = "Replace Ventilator Battery";
        displayNameProgress = "Replacing battery...";
        category = "advanced";
        treatmentTime = 6;
        items[] = {"ACME_VentBattery"};
        condition = "[_patient] call ACME_fnc_canSwapVentBattery";
        callbackSuccess = "[_this select 0, _this select 1] call ACME_fnc_swapVentBattery";
        itemConsumed = 1;
        allowedSelections[] = {"Body"};
    };
    class ACME_IntubateStart: CheckAirway {
        // CheckAirway forces a crouch through its callbackStart now. this restates an empty one so this action
        // keeps the behavior it had. delete this line to give it the crouch as well.
        callbackStart = "";
        // and it keeps the animation it inherited before CheckAirway moved to the rifle carrying variant.
        animationMedic = "AinvPknlMstpSnonWnonDr_medic4";
        animationMedicProne = "AinvPknlMstpSnonWnonDr_medic4";
        displayName = "Intubate (Orotracheal)";
        displayNameProgress = "Intubating...";
        category = "airway";  // moved from advanced. intubation is an airway decision and belongs with the other adjuncts.
        treatmentLocations[] = {"All"};
        medicRequired = "ACME_skillIntubation";
        treatmentTime = 0.1;
        allowedSelections[] = {"Head"};
        items[] = {};
        // B120: Orotracheal intubation may be attempted on a perfusing casualty. Airway reflex, sedation and
        // paralysis are handled inside the procedure rather than hiding the action from the menu.
        condition = "([_medic, 'ACME_IntubateStart'] call ACME_fnc_procedureActionAllowed) && {([_medic, 'ACME_Laryngoscope'] call ACME_fnc_itemCount) > 0} && {([_medic, 'ACME_ETTube'] call ACME_fnc_itemCount) > 0} && {!(_patient getVariable ['ACME_ETT_Inserted', false])} && {!(_patient getVariable ['ACM_airway_RecoveryPosition_State', false])} && {(_patient getVariable ['ACM_airway_AirwayItem_Oral', '']) isEqualTo ''} && {!(_patient getVariable ['ACM_airway_SurgicalAirway_TubeInserted', false])} && {!(_patient getVariable ['ACME_nrb_on', false])}";
        callbackSuccess = "[_medic, _patient, toLower _bodyPart] call ACME_fnc_laryngoOpen";
        callbackFailure = "";
        callbackProgress = "";
    };

    // extubate. it sits in airway adjuncts in exactly the place intubate occupies, and appears only when intubate
    // cannot. the two swap over on whether a tube is actually in. once an airway is secured nothing in the
    // laryngoscopy screen can disturb it, so this is the only way it comes back out. that is also how it works in
    // life: a secured tube is not something you fiddle with, it is something you deliberately remove.
    // it is slower than placing it, on purpose. pulling a tube is a decision, and the casualty loses their airway
    // the moment it clears the cords.
    class ACME_Extubate: CheckAirway {
        // CheckAirway forces a crouch through its callbackStart now. this restates an empty one so this action
        // keeps the behavior it had. delete this line to give it the crouch as well.
        callbackStart = "";
        // and it keeps the animation it inherited before CheckAirway moved to the rifle carrying variant.
        animationMedic = "AinvPknlMstpSnonWnonDr_medic4";
        animationMedicProne = "AinvPknlMstpSnonWnonDr_medic4";
        displayName = "Extubate";
        displayNameProgress = "Extubating...";
        category = "airway";
        treatmentLocations[] = {"All"};
        medicRequired = "ACME_skillIntubation";
        treatmentTime = 4;
        allowedSelections[] = {"Head"};
        items[] = {};
        // B120: Extubate is the deliberate removal workflow and remains visible for any inserted ET tube.
        // Its treatment includes releasing securement and cuff state before withdrawing the tube.
        condition = "([_medic, 'ACME_Extubate'] call ACME_fnc_procedureActionAllowed) && {(_patient getVariable ['ACME_ETT_Inserted', false])}";
        callbackSuccess = "[_medic, _patient] call ACME_fnc_laryngoExtubate";
        callbackFailure = "";
        callbackProgress = "";
    };


    // open the airway view again. once the screen was closed there was no way back into it, so a tube that had
    // migrated, an airway full of vomit, or a cuff that was never inflated could all be seen on the body diagram
    // and then not worked on. this reopens the same screen on a casualty who already has a tube.
    // it needs no kit, because looking at an airway you have already secured is not a fresh intubation.
    // a fully seated and secured tube opens read-only, because the screen refuses to disturb a secured airway.
    class ACME_OpenAirwayView: CheckAirway {
        // CheckAirway forces a crouch through its callbackStart now. this restates an empty one so this action
        // keeps the behavior it had. delete this line to give it the crouch as well.
        callbackStart = "";
        // and it keeps the animation it inherited before CheckAirway moved to the rifle carrying variant.
        animationMedic = "AinvPknlMstpSnonWnonDr_medic4";
        animationMedicProne = "AinvPknlMstpSnonWnonDr_medic4";
        displayName = "Open Airway View";
        displayNameProgress = "Looking...";
        category = "airway";
        treatmentLocations[] = {"All"};
        medicRequired = "ACME_skillIntubation";
        treatmentTime = 0.1;
        allowedSelections[] = {"Head"};
        items[] = {};
        condition = "([_medic, 'ACME_OpenAirwayView'] call ACME_fnc_procedureActionAllowed) && {(_patient getVariable ['ACME_ETT_Inserted', false])}";
        callbackSuccess = "[_medic, _patient, toLower _bodyPart] call ACME_fnc_laryngoOpen";
        callbackFailure = "";
        callbackProgress = "";
    };
    // B11: the instant connector uses the acknowledged custody transaction.
    // It does not start a progress dialog or start ventilation automatically.
    class ACME_ConnectETVent: CheckPulse {
        displayName = "Connect Airway > Ventilator";
        displayNameProgress = "";
        category = "advanced";
        treatmentLocations = 0;
        medicRequired = "ACME_skillVentilator";
        treatmentTime = 0;
        ACM_rollToBack = "false";
        consumeItem = 0;
        allowedSelections[] = {"Head"};
        items[] = {};
        condition = "([_medic, 'ACME_ConnectETVent'] call ACME_fnc_procedureActionAllowed) && {!(_patient getVariable ['ACM_airway_RecoveryPosition_State', false])} && {((_patient getVariable ['ACME_ETT_Inserted', false]) || {(_patient getVariable ['ACM_airway_AirwayItem_Oral', '']) isEqualTo 'SGA'} || {_patient getVariable ['ACM_airway_SurgicalAirway_TubeInserted', false]}) && {!(_patient getVariable ['ACME_vent_circuit', false])} && {!(_patient getVariable ['ACME_vent_onPatient', false])} && {(_patient getVariable ['ACME_vent_custodyId', '']) == ''} && {([_medic, 'ACME_Ventilator'] call ACME_fnc_itemCount) > 0}}";
        callbackSuccess = "[_medic, _patient] call ACME_fnc_ventConnectPatient";
        ACM_menuIcon = "ACME_Ventilator";
        callbackFailure = "";
        callbackProgress = "";
    };

    // disconnect ventilator. there was no explicit way to take the machine off a casualty. the only route was to
    // walk away and let the leash break it, which is now deliberately impossible, because the machine travels with
    // the patient. taking a ventilator off someone is a decision a medic makes, so it needs to be an action they
    // can choose. it recovers the ventilator to the medic and clears every piece of vent state on the casualty.
    class ACME_DisconnectETVent: CheckPulse {
        displayName = "Disconnect Ventilator";
        displayNameProgress = "Disconnecting ventilator...";
        category = "advanced";
        medicRequired = "ACME_skillVentilator";
        treatmentTime = 2;
        allowedSelections[] = {"Head"};  // head only. the ventilator connects at the airway, so it belongs on the head and nowhere else.
        items[] = {};
        condition = "([_medic, 'ACME_DisconnectETVent'] call ACME_fnc_procedureActionAllowed) && {(_patient getVariable ['ACME_vent_onPatient', false]) && {!(_patient getVariable ['ACME_vent_recovering', false])}}";
        callbackSuccess = "[_medic, _patient] call ACME_fnc_ventDisconnectPatient";
        callbackFailure = "";
        callbackProgress = "";
        ACM_menuIcon = "ACME_Ventilator";
    };

    // open ventilator on this patient, stage 3. it appears once the patient is connected and configured, and opens
    // the panel bound to the patient in the preset style. because the patient is already configured, the boot
    // sequence is skipped and the panel lands straight on the live screen, exactly like reopening a configured
    // self-preset ventilator. it requires the medic to carry a ventilator.
    // there is also a debug action that cycles the cabin-motion test switch, off to cruise to hard bank, without
    // leaving the ground or opening the console. it exists because "there is no shake" has several causes that
    // look identical from outside fn_motionshake, and four builds went into guessing at them one at a time. you
    // can now stand still, open any minigame, and know in ten seconds whether the motion system is alive and what
    // each level feels like.
    class ACME_DebugForceShake: CheckPulse {
        displayName = "Force Shake (debug)";
        displayNameProgress = "";
        treatmentTime = 0.01;  // ACE requires a non-zero duration to fire callbackSuccess; 0.01 is visually instant.
        allowedSelections[] = {"Head"};
        condition = "missionNamespace getVariable ['ACME_debug_enabled', false]";
        callbackSuccess = "[] call ACME_fnc_debugForceShake";
        items[] = {};
    };

    class ACME_VentOpenPatient: CheckPulse {
        displayName = "Open Ventilator";
        displayNameProgress = "...";
        category = "advanced";
        treatmentLocations[] = {"All"};
        medicRequired = "ACME_skillVentilator";
        treatmentTime = 0.1;
        allowedSelections[] = {"Head"};  // head only. the ventilator connects at the airway, so it belongs on the head and nowhere else.
        items[] = {};
        // the machine is on the patient once connected, so requiring the medic to carry one would make the panel
        // unreachable the moment it was hooked up. carrying a spare still works for a patient who has been configured
        // and not yet connected.
        condition = "([_medic, 'ACME_VentOpenPatient'] call ACME_fnc_procedureActionAllowed) && {((_patient getVariable ['ACME_vent_circuit', false]) || {_patient getVariable ['ACME_vent_configured', false]}) && {(_patient getVariable ['ACME_vent_onPatient', false]) || {([_medic, 'ACME_Ventilator'] call ACME_fnc_itemCount) > 0}}}";
        callbackSuccess = "[_patient, true] call ACME_fnc_ventPanelOpen";
        ACM_menuIcon = "ACME_Ventilator";
        callbackFailure = "";
        callbackProgress = "";
    };
    // the option disappears. it opens the ej mini-game on the body-background view. both jugulars, left and right
    // of the throat, are palpable, and the active side tracks the cursor.
    class ACME_EstablishEJ: CheckPulse {
        // no animation for anything to do with an IV. the work is done in the screen, and a treatment pose
        // played on the body at the same time reads as the medic doing something else entirely.
        // these inherit CheckPulse, which declares one, so it is silenced rather than left to the parent.
        animationMedic = "";
        animationMedicProne = "";
        displayName = "Establish EJ IV";
        displayNameProgress = "...";
        category = "advanced";
        ACM_menuIcon = "ACME_EstablishIV";
        treatmentLocations[] = {"All"};
        medicRequired = 0;
        treatmentTime = 0.1;
        allowedSelections[] = {"Head"};
        items[] = {};
        condition = "!alive _patient || {(_patient getVariable ['ACE_isUnconscious', false]) || {(stance _patient) == 'PRONE'}}";
        callbackStart = "_this call ACME_fnc_ivMinigamePrepare";
        callbackSuccess = "[_medic, _patient, 'ej', 'left'] call ACME_fnc_ivMinigameOpen";
        callbackFailure = "";
        callbackProgress = "";
    };

    // remove an established ej iv. it shows on the head only when a jugular is actually cannulated, on a head iv at
    // access site 0 or 1. it clears the iv through ACME_fnc_removeEJ, an ACM setivlocal type 0, which also returns
    // any hung bag.
    class ACME_RemoveEJ: CheckPulse {
        displayName = "Remove EJ IV";
        displayNameProgress = "Removing EJ IV...";
        category = "advanced";
        ACM_menuIcon = "ACME_EstablishIV";
        treatmentLocations[] = {"All"};
        medicRequired = 0;
        treatmentTime = 3;
        allowedSelections[] = {"Head"};
        items[] = {};
        condition = "false";  // EJ removal is physical: grab the catheter hub in the IV minigame and pull it.
        callbackSuccess = "[_medic, _patient] call ACME_fnc_removeEJ";
        callbackFailure = "";
        callbackProgress = "";
    };
    // AAJT-S placement modes. All applications take 20 seconds.
    // Inguinal placement is unilateral and proximally occludes exactly the selected leg. Axillary placement
    // proximally occludes exactly the selected arm. Zone 3 REBOA is applied on the chest/body selection and
    // occludes both lower extremities. The physical device state is persistent; dead casualties keep the same
    // treatment paths and visual evidence.
    class ACME_ApplyAAJT_Inguinal: CheckPulse {
        displayName = "Apply AAJT-S (Inguinal)";
        displayNameProgress = "Applying AAJT-S...";
        category = "bandage";
        treatmentLocations = 0;
        medicRequired = 0;
        treatmentTime = 20;
        allowedSelections[] = {"LeftLeg","RightLeg"};
        condition = "!(_patient getVariable ['ACME_AAJT_inguinal', false])";
        callbackStart = "[_this select 1, 'aajtApplying', [toLowerANSI (_this select 2), true]] call ACME_fnc_ownerDispatch";
        callbackSuccess = "_this call ACME_fnc_aajtApply";
        callbackFailure = "[_this select 1, 'aajtApplying', ['', false]] call ACME_fnc_ownerDispatch";
        callbackProgress = "";
        animationMedic = "AinvPknlMstpSnonWnonDr_medic4";
        items[] = {"ACME_AAJT_S"};
        consumeItem = 1;
        icon = "\acm_extended\ui\items\aajt-s_ca.paa";
        ACM_menuIcon = "ACME_AAJT";
    };
    class ACME_RemoveAAJT_Inguinal: CheckPulse {
        displayName = "Remove AAJT-S (Inguinal)";
        displayNameProgress = "Removing AAJT-S...";
        category = "bandage";
        treatmentLocations = 0;
        medicRequired = 0;
        treatmentTime = 4;
        allowedSelections[] = {"LeftLeg","RightLeg"};
        condition = "(_patient getVariable ['ACME_AAJT_inguinal', false]) && {(_patient getVariable ['ACME_AAJT_inguinalSide', '']) == toLowerANSI _bodyPart}";
        callbackSuccess = "_this call ACME_fnc_aajtRemove";
        callbackFailure = "";
        callbackProgress = "";
        animationMedic = "AinvPknlMstpSnonWnonDr_medic4";
        items[] = {};
        icon = "\acm_extended\ui\items\aajt-s_ca.paa";
        ACM_menuIcon = "ACME_AAJT";
    };
    class ACME_ApplyAAJT_Axilla: CheckPulse {
        displayName = "Apply AAJT-S (Axilla)";
        displayNameProgress = "Applying AAJT-S...";
        category = "bandage";
        treatmentLocations = 0;
        medicRequired = 0;
        treatmentTime = 20;
        allowedSelections[] = {"LeftArm","RightArm"};
        condition = "((toLowerANSI _bodyPart) == 'leftarm' && {!(_patient getVariable ['ACME_AAJT_axillaleft', false])}) || {(toLowerANSI _bodyPart) == 'rightarm' && {!(_patient getVariable ['ACME_AAJT_axillaright', false])}}";
        callbackStart = "[_this select 1, 'aajtApplying', [toLowerANSI (_this select 2), true]] call ACME_fnc_ownerDispatch";
        callbackSuccess = "_this call ACME_fnc_aajtApply";
        callbackFailure = "[_this select 1, 'aajtApplying', ['', false]] call ACME_fnc_ownerDispatch";
        callbackProgress = "";
        animationMedic = "AinvPknlMstpSnonWnonDr_medic4";
        items[] = {"ACME_AAJT_S"};
        consumeItem = 1;
        icon = "\acm_extended\ui\items\aajt-s_ca.paa";
        ACM_menuIcon = "ACME_AAJT";
    };
    class ACME_RemoveAAJT_Axilla: CheckPulse {
        displayName = "Remove AAJT-S (Axilla)";
        displayNameProgress = "Removing AAJT-S...";
        category = "bandage";
        treatmentLocations = 0;
        medicRequired = 0;
        treatmentTime = 4;
        allowedSelections[] = {"LeftArm","RightArm"};
        condition = "((toLowerANSI _bodyPart) == 'leftarm' && {_patient getVariable ['ACME_AAJT_axillaleft', false]}) || {(toLowerANSI _bodyPart) == 'rightarm' && {_patient getVariable ['ACME_AAJT_axillaright', false]}}";
        callbackSuccess = "_this call ACME_fnc_aajtRemove";
        callbackFailure = "";
        callbackProgress = "";
        animationMedic = "AinvPknlMstpSnonWnonDr_medic4";
        items[] = {};
        icon = "\acm_extended\ui\items\aajt-s_ca.paa";
        ACM_menuIcon = "ACME_AAJT";
    };
    class ACME_ApplyAAJT_Zone3: CheckPulse {
        displayName = "Apply AAJT-S (Zone 3 REBOA)";
        displayNameProgress = "Applying AAJT-S (Zone 3 REBOA)...";
        category = "bandage";
        treatmentLocations = 0;
        medicRequired = 0;
        treatmentTime = 20;
        allowedSelections[] = {"Body"};
        condition = "!(_patient getVariable ['ACME_AAJT_zone3', false])";
        callbackStart = "[_this select 1, 'aajtApplying', ['body', true]] call ACME_fnc_ownerDispatch";
        callbackSuccess = "_this call ACME_fnc_aajtApply";
        callbackFailure = "[_this select 1, 'aajtApplying', ['', false]] call ACME_fnc_ownerDispatch";
        callbackProgress = "";
        animationMedic = "AinvPknlMstpSnonWnonDr_medic4";
        items[] = {"ACME_AAJT_S"};
        consumeItem = 1;
        icon = "\acm_extended\ui\items\aajt-s_zone3_reboa_ca.paa";
        ACM_menuIcon = "ACME_AAJT";
    };
    class ACME_RemoveAAJT_Zone3: CheckPulse {
        displayName = "Remove AAJT-S (Zone 3 REBOA)";
        displayNameProgress = "Removing AAJT-S (Zone 3 REBOA)...";
        category = "bandage";
        treatmentLocations = 0;
        medicRequired = 0;
        treatmentTime = 4;
        allowedSelections[] = {"Body"};
        condition = "_patient getVariable ['ACME_AAJT_zone3', false]";
        callbackSuccess = "_this call ACME_fnc_aajtRemove";
        callbackFailure = "";
        callbackProgress = "";
        animationMedic = "AinvPknlMstpSnonWnonDr_medic4";
        items[] = {};
        icon = "\acm_extended\ui\items\aajt-s_zone3_reboa_ca.paa";
        ACM_menuIcon = "ACME_AAJT";
    };
    // a pak, the personal aid kit, normally requires a fully stable patient. an XStat is a temporising measure
    // that requires surgical removal, so a pak, which represents definitive care at a ccp, can be used on an XStat
    // casualty even when they are not otherwise stable. the heal clears the XStat, through ace_medical_FullHeal.
    class PersonalAidKit {
        condition = "((_patient call ace_medical_status_fnc_isInStableCondition) || {_patient getVariable ['ACME_XStat_needsSurgery', false]}) && {!(_patient getVariable ['ACME_requiresEvac', false]) || {(_patient getVariable ['ACME_evacuated', false]) || {!isNull objectParent _patient}}}";
    };

    // we do not override removetourniquet. modifying it in place, as a bare class removetourniquet { ... } with no
    // parent forward-declared, does not merge with ACM's class. it replaces it with a stub that loses ACM's
    // callbacksuccess and displayname, so the action either does not show or does nothing on click. that is
    // exactly what was breaking tourniquet removal. ACM's native removetourniquet is left untouched.
    // AAJT-s leg protection, so a medic does not manually pull the leg tourniquet of the device, is handled at the
    // device level instead. those legs already hide the tourniquet icon and injury row, and fn_aajtremove pulls
    // the tourniquet when the device comes off.

    // XStat 30, an injectable hemostatic sponge bolus, for an inguinal junctional wound only.
    // it is an extreme-case, one-way device. it is offered only on a fresh open inguinal, or leg, junctional wound,
    // with no inguinal AAJT in place and the item carried. it therefore cannot be stacked on any other treatment,
    // cannot be used on arms, and cannot be reapplied, because once seated the state is xstat rather than open.
    // there is no remove action. it is permanent until surgery or a full heal. the insert takes about 3 s and
    // fn_xstatapply does the rest.
    class ACME_ApplyXStat: CheckPulse {
        displayName = "Insert XStat 30";
        displayNameProgress = "Inserting XStat...";
        category = "bandage";
        treatmentLocations[] = {"All"};
        medicRequired = 0;
        treatmentTime = 3;
        // arms are included. an axillary wound is junctional and is exactly the kind of bleed XStat is for, because it
        // is one you cannot tourniquet and cannot reliably pack by hand. the wound state already lives on LeftArm and
        // RightArm, as ACME_Junc_leftarm and _rightarm, so the condition below already resolved correctly for them.
        // this list was the only thing refusing. the AAJT keeps its legs-only list, because inguinal is the only site
        // it fits.
        allowedSelections[] = {"LeftLeg","RightLeg","LeftArm","RightArm"};
        // axillary wounds too. XStat is a junctional hemostatic and the axilla is a junctional site. it is one of the
        // places the sponges are indicated, because it is a wound you cannot tourniquet and cannot reliably pack by
        // hand. the AAJT exclusion stays inguinal only, because that is the only site the AAJT occupies.
        condition = "private _i = ['head','body','leftarm','rightarm','leftleg','rightleg'] find toLowerANSI _bodyPart; ((_patient getVariable [format ['ACME_Junc_%1', toLowerANSI _bodyPart], '']) == 'open') && {_i >= 0} && {!([_patient, _i] call ACME_fnc_aajtOccludes)} && {([_medic, 'ACME_XStat'] call ACME_fnc_itemCount) > 0}";
        callbackSuccess = "_this call ACME_fnc_xstatApply";
        callbackFailure = "";
        callbackProgress = "";
        animationMedic = "AinvPknlMstpSnonWnonDr_medic4";
        // keep the real item in items[], so ACM and ACE inventory gating, the tooltip count and medical-menu filtering
        // all recognize the treatment as XStat-backed. consumeitem=0 below stops ACE deleting the carried applicator
        // after insertion, so the same pack can still gate additional sites.
        items[] = {"ACME_XStat"};
        consumeItem = 0;
        ACM_menuIcon = "ACME_XStat";
        icon = "\acm_extended\ui\items\xstat_ca.paa";
    };

    // non-rebreather mask, apply and remove. it sits in airway, on the head.
    // the menu icon inherits ACM's capnograph body symbol for now. a full yellow tint on the live monitor and body
    // image needs either a recolored .paa or an updatebodyimage hook. see the readme.
    class ACME_ApplyNRB: CheckAirway {
        // CheckAirway forces a crouch through its callbackStart now. this restates an empty one so this action
        // keeps the behavior it had. delete this line to give it the crouch as well.
        callbackStart = "";
        // this action already declares its own animationMedic below, so nothing is restated here.
        displayName = "Apply Non-Rebreather Mask";
        displayNameProgress = "Applying NRB...";
        category = "airway";
        treatmentLocations[] = {"All"};
        medicRequired = 0;
        treatmentTime = 1;
        allowedSelections[] = {"Head"};
        condition = "(missionNamespace getVariable ['ACME_sys_nrb', true]) && {[_patient] call ACME_fnc_nrbAirwayCompatible} && {!(_patient getVariable ['ACME_nrb_on', false]) && {([_medic, 'ACM_NRBMask'] call ACME_fnc_itemCount) > 0}}";
        callbackSuccess = "_this call ACME_fnc_nrbApply";
        callbackFailure = "";
        callbackProgress = "";
        animationMedic = "AinvPknlMstpSnonWnonDr_medic4";
        items[] = {};
        icon = "\acm_extended\ui\items\nrbmask_ca.paa";
        ACM_menuIcon = "ACM_NRBMask";
    };
    class ACME_RemoveNRB: CheckAirway {
        // CheckAirway forces a crouch through its callbackStart now. this restates an empty one so this action
        // keeps the behavior it had. delete this line to give it the crouch as well.
        callbackStart = "";
        // and it keeps the animation it inherited before CheckAirway moved to the rifle carrying variant.
        animationMedic = "AinvPknlMstpSnonWnonDr_medic4";
        animationMedicProne = "AinvPknlMstpSnonWnonDr_medic4";
        displayName = "Remove Non-Rebreather Mask";
        displayNameProgress = "Removing NRB...";
        category = "airway";
        treatmentLocations[] = {"All"};
        medicRequired = 0;
        treatmentTime = 2;
        allowedSelections[] = {"Head"};
        condition = "_patient getVariable ['ACME_nrb_on', false]";
        callbackSuccess = "_this call ACME_fnc_nrbRemove";
        callbackFailure = "";
        callbackProgress = "";
        items[] = {};
        icon = "\acm_extended\ui\items\nrbmask_ca.paa";
        ACM_menuIcon = "ACM_NRBMask";
    };
    class ACME_PrepHPMK: CheckPulse {
        displayName = "Prep HPMK";
        displayNameProgress = "Prepping HPMK...";
        category = "advanced";
        treatmentLocations[] = {"All"};
        medicRequired = 0;
        treatmentTime = 5.699;
        allowedSelections[] = {"Body"};
        condition = "!(_patient isEqualTo _medic) && {(_patient getVariable ['ACE_isUnconscious', false]) || {(stance _patient) == 'PRONE'} || {_patient getVariable ['ACM_core_Lying_State', false]}} && {(missionNamespace getVariable ['ACME_sys_hpmk', true]) && {((_patient getVariable ['ACME_hpmk_state', '']) == '') && {([_medic, 'ACM_HPMK'] call ACME_fnc_itemCount) > 0}}}";
        callbackStart = "params ['_medic','_patient']; if (!isNull _patient) then {[_patient, 5.699] call ACME_fnc_markImportantSfx}; if (!isNull _medic) then {[_medic, 'ACM_HPMK_Wrap'] remoteExec ['say3D', 0]}";
        callbackSuccess = "_this call ACME_fnc_hpmkPrep";
        callbackFailure = "";
        callbackProgress = "";
        animationMedic = "AinvPknlMstpSnonWnonDr_medic4";
        items[] = {};
        icon = "\acm_extended\ui\items\HPMK_ca.paa";
        ACM_menuIcon = "ACM_HPMK";
    };
    class ACME_WrapHPMK: CheckPulse {
        displayName = "Wrap in HPMK";
        displayNameProgress = "Wrapping in HPMK...";
        category = "advanced";
        treatmentLocations[] = {"All"};
        medicRequired = 0;
        treatmentTime = 1.242;
        allowedSelections[] = {"Body"};
        condition = "!(_patient isEqualTo _medic) && {(_patient getVariable ['ACE_isUnconscious', false]) || {(stance _patient) == 'PRONE'} || {_patient getVariable ['ACM_core_Lying_State', false]}} && {(_patient getVariable ['ACME_hpmk_state', '']) == 'prepped'}";
        callbackStart = "";
        callbackSuccess = "_this call ACME_fnc_hpmkWrap";
        callbackFailure = "";
        callbackProgress = "";
        animationMedic = "AinvPknlMstpSnonWnonDr_medic4";
        items[] = {};
        icon = "\acm_extended\ui\items\HPMK_ca.paa";
        ACM_menuIcon = "ACM_HPMK";
    };
    class ACME_UnwrapHPMK: CheckPulse {
        displayName = "Unwrap HPMK";
        displayNameProgress = "Unwrapping HPMK...";
        category = "advanced";
        treatmentLocations[] = {"All"};
        medicRequired = 0;
        treatmentTime = 1.019;
        allowedSelections[] = {"Body"};
        condition = "!(_patient isEqualTo _medic) && {(_patient getVariable ['ACME_hpmk_state', '']) in ['wrapped', 'exposed']}";
        callbackStart = "params ['_medic','_patient']; if (!isNull _patient) then {[_patient, 1.019] call ACME_fnc_markImportantSfx}; if (!isNull _medic) then {[_medic, 'ACME_HPMK_Unwrap'] remoteExec ['say3D', 0]}";
        callbackSuccess = "_this call ACME_fnc_hpmkUnwrap";
        callbackFailure = "";
        callbackProgress = "";
        animationMedic = "AinvPknlMstpSnonWnonDr_medic4";
        items[] = {};
        icon = "\acm_extended\ui\items\HPMK_ca.paa";
        ACM_menuIcon = "ACM_HPMK";
    };
    // partially expose chest. it shows directly under "Unwrap HPMK" while the patient is fully wrapped. it opens
    // the chest and left arm for care, while the right arm and the legs stay wrapped, and passive rewarming keeps
    // running.
    class ACME_ExposeChestHPMK: CheckPulse {
        displayName = "Partially Expose Chest";
        displayNameProgress = "Exposing chest...";
        category = "advanced";
        treatmentLocations[] = {"All"};
        medicRequired = 0;
        treatmentTime = 2.377;
        allowedSelections[] = {"Body"};
        condition = "!(_patient isEqualTo _medic) && {(_patient getVariable ['ACME_hpmk_state', '']) == 'wrapped'}";
        callbackStart = "params ['_medic','_patient']; if (!isNull _patient) then {[_patient, 2.377] call ACME_fnc_markImportantSfx}; if (!isNull _medic) then {[_medic, 'ACME_HPMK_Expose'] remoteExec ['say3D', 0]}";
        callbackSuccess = "_this call ACME_fnc_hpmkExposeChest";
        callbackFailure = "";
        callbackProgress = "";
        animationMedic = "AinvPknlMstpSnonWnonDr_medic4";
        items[] = {};
        icon = "\acm_extended\ui\items\HPMK_ca.paa";
        ACM_menuIcon = "ACM_HPMK";
    };
    // cover chest. it re-seals a partially exposed chest back to fully wrapped.
    class ACME_CoverChestHPMK: CheckPulse {
        displayName = "Cover Chest";
        displayNameProgress = "Re-covering chest...";
        category = "advanced";
        treatmentLocations[] = {"All"};
        medicRequired = 0;
        treatmentTime = 2.377;
        allowedSelections[] = {"Body"};
        condition = "!(_patient isEqualTo _medic) && {(_patient getVariable ['ACME_hpmk_state', '']) == 'exposed'}";
        callbackStart = "params ['_medic','_patient']; if (!isNull _patient) then {[_patient, 2.377] call ACME_fnc_markImportantSfx}; if (!isNull _medic) then {[_medic, 'ACME_HPMK_Expose'] remoteExec ['say3D', 0]}";
        callbackSuccess = "_this call ACME_fnc_hpmkCoverChest";
        callbackFailure = "";
        callbackProgress = "";
        animationMedic = "AinvPknlMstpSnonWnonDr_medic4";
        items[] = {};
        icon = "\acm_extended\ui\items\HPMK_ca.paa";
        ACM_menuIcon = "ACM_HPMK";
    };
    class ACME_RemoveHPMK: CheckPulse {
        displayName = "Remove HPMK";
        displayNameProgress = "Removing HPMK...";
        category = "advanced";
        treatmentLocations[] = {"All"};
        medicRequired = 0;
        treatmentTime = 3.924;
        allowedSelections[] = {"Body"};
        condition = "!(_patient isEqualTo _medic) && {(_patient getVariable ['ACME_hpmk_state', '']) == 'prepped'}";
        callbackStart = "params ['_medic','_patient']; if (!isNull _patient) then {[_patient, 3.924] call ACME_fnc_markImportantSfx}; if (!isNull _medic) then {[_medic, 'ACM_HPMK_Remove'] remoteExec ['say3D', 0]}";
        callbackSuccess = "_this call ACME_fnc_hpmkRemove";
        callbackFailure = "";
        callbackProgress = "";
        items[] = {};
        icon = "\acm_extended\ui\items\HPMK_ca.paa";
        ACM_menuIcon = "ACM_HPMK";
    };
    class ACME_AttachEMMA: CheckPulse {
        displayName = "Attach EMMA to My BVM";
        displayNameProgress = "Attaching EMMA...";
        category = "airway";
        treatmentLocations[] = {"All"};
        medicRequired = 0;
        allowSelfTreatment = 1;
        treatmentTime = 0.5;
        allowedSelections[] = {"Head","Body","LeftArm","RightArm","LeftLeg","RightLeg"};
        condition = "!(_medic getVariable ['ACME_emma_bvmAttached', false]) && {([_medic, 'ACM_EMMA'] call ACME_fnc_itemCount) > 0}";
        callbackStart = "params ['_medic']; if (!isNull _medic) then {[_medic, 'ACME_EMMA_Attach'] remoteExec ['say3D', 0]}";
        callbackSuccess = "_this call ACME_fnc_emmaAttach";
        callbackFailure = "";
        callbackProgress = "";
        items[] = {};
        icon = "\acm_extended\ui\emma\emma_etco2_ca.paa";
        ACM_menuIcon = "ACM_EMMA";
    };
    // the EMMA on an et tube.
    // it is a separate pair from the i-gel actions rather than a widened condition on them, because the medic
    // should read which airway they are attaching to. an EMMA inline on a tube is the normal place for it, and it
    // is the one that matters most: a tube in the esophagus and a tube in the trachea look identical until
    // something reads the CO2 coming back.
    // the underlying attach and remove are shared with the i-gel, because the device and the routing are the same
    // once it is on. only the condition differs.
    class ACME_AttachEMMAETT: CheckPulse {
        displayName = "Attach EMMA to ETT";
        displayNameProgress = "Attaching EMMA...";
        category = "airway";
        treatmentLocations[] = {"All"};
        medicRequired = 0;
        allowSelfTreatment = 0;
        treatmentTime = 0.5;
        allowedSelections[] = {"Head"};
        condition = "[_medic, _patient, 'ett'] call ACME_fnc_emmaCanAttachIGel";
        callbackStart = "params ['_medic']; if (!isNull _medic) then {[_medic, 'ACME_EMMA_Attach'] remoteExec ['say3D', 0]}";
        callbackSuccess = "[_medic, _patient, _bodyPart, 'ett'] call ACME_fnc_emmaAttachIGel";
        callbackFailure = "";
        callbackProgress = "";
        items[] = {};
        icon = "\acm_extended\ui\emma\emma_etco2_ca.paa";
        ACM_menuIcon = "ACM_EMMA";
    };
    class ACME_RemoveEMMAETT: ACME_AttachEMMAETT {
        displayName = "Remove EMMA from ETT";
        displayNameProgress = "Removing EMMA...";
        condition = "(_patient isNotEqualTo _medic) && {_patient getVariable ['ACME_ETT_Inserted', false]} && {[_medic, _patient] call ACME_fnc_emmaCanRemoveIGel}";
        callbackStart = "params ['_medic']; if (!isNull _medic) then {[_medic, 'ACME_EMMA_Detach'] remoteExec ['say3D', 0]}";
        callbackSuccess = "_this call ACME_fnc_emmaRemoveIGel";
    };
    class ACME_AttachEMMAIGel: CheckPulse {
        displayName = "Attach EMMA to their i-gel";
        displayNameProgress = "Attaching EMMA...";
        category = "airway";
        treatmentLocations[] = {"All"};
        medicRequired = 0;
        allowSelfTreatment = 0;
        treatmentTime = 0.5;
        allowedSelections[] = {"Head"};
        condition = "[_medic, _patient, 'igel'] call ACME_fnc_emmaCanAttachIGel";
        callbackStart = "params ['_medic']; if (!isNull _medic) then {[_medic, 'ACME_EMMA_Attach'] remoteExec ['say3D', 0]}";
        callbackSuccess = "[_medic, _patient, _bodyPart, 'igel'] call ACME_fnc_emmaAttachIGel";
        callbackFailure = "";
        callbackProgress = "";
        items[] = {};
        icon = "\acm_extended\ui\emma\emma_etco2_ca.paa";
        ACM_menuIcon = "ACM_EMMA";
    };
    class ACME_RemoveEMMAIGel: CheckPulse {
        displayName = "Remove EMMA from their i-gel";
        displayNameProgress = "Removing EMMA...";
        category = "airway";
        treatmentLocations[] = {"All"};
        medicRequired = 0;
        allowSelfTreatment = 0;
        treatmentTime = 0.5;
        allowedSelections[] = {"Head"};
        condition = "!(_patient getVariable ['ACME_ETT_Inserted', false]) && {[_medic, _patient] call ACME_fnc_emmaCanRemoveIGel}";
        callbackStart = "params ['_medic']; if (!isNull _medic) then {[_medic, 'ACME_EMMA_Detach'] remoteExec ['say3D', 0]}";
        callbackSuccess = "_this call ACME_fnc_emmaRemoveIGel";
        callbackFailure = "";
        callbackProgress = "";
        items[] = {};
        icon = "\acm_extended\ui\emma\emma_etco2_ca.paa";
        ACM_menuIcon = "ACM_EMMA";
    };
    class ACME_RemoveEMMA: CheckPulse {
        displayName = "Remove EMMA from My BVM";
        displayNameProgress = "Removing EMMA...";
        category = "airway";
        treatmentLocations[] = {"All"};
        medicRequired = 0;
        allowSelfTreatment = 1;
        treatmentTime = 0.5;
        allowedSelections[] = {"Head","Body","LeftArm","RightArm","LeftLeg","RightLeg"};
        condition = "_medic getVariable ['ACME_emma_bvmAttached', false]";
        callbackStart = "params ['_medic']; if (!isNull _medic) then {[_medic, 'ACME_EMMA_Detach'] remoteExec ['say3D', 0]}";
        callbackSuccess = "_this call ACME_fnc_emmaRemove";
        callbackFailure = "";
        callbackProgress = "";
        items[] = {};
        icon = "\acm_extended\ui\emma\emma_etco2_ca.paa";
        ACM_menuIcon = "ACM_EMMA";
    };

    // re-open the suction actions of ACM so both open the airway screen in suction mode instead of running a timed
    // treatment. the screen is the treatment: it owns the device animation, the airway fill and its own sound, so
    // there is no progress bar, no callbackstart and no sfx wiring here.
    // The legacy type argument remains accepted. Current provider inventory selects the device.
    // ACCUVAC takes priority; the manual driver consumes a bag on the first squeeze.
    // CheckAirway is already declared at the top of this class.
    class UseSuctionBag: CheckAirway {
        // this action already declares its own callbackStart below, so nothing is restated here. it therefore
        // does not inherit the CheckAirway crouch, which is the behavior it had before.
        // and it keeps the animation it inherited before CheckAirway moved to the rifle carrying variant.
        animationMedic = "AinvPknlMstpSnonWnonDr_medic4";
        animationMedicProne = "AinvPknlMstpSnonWnonDr_medic4";
        // 0.1, not 0. ACE does not fire callbacksuccess on a zero-duration treatment, so setting this to 0 to skip the
        // progress bar meant the action ran and then called nothing at all. every other minigame opener in this addon
        // uses 0.1 or higher and every one of them works. 0.1 is short enough that there is no visible bar and long
        // enough that the callback fires.

        // manual suction opens the airway screen, the same way UseAccuvac does. there is no callbackstart, because
        // the screen is the treatment and it owns its own sound. a squeeze noise has to land on the squeeze rather
        // than on a progress bar that has already finished.

        treatmentTime = 0.1;
        callbackStart = "";
        consumeItem = 0; // The manual device is consumed on its first squeeze in fn_suctionBulb.
        callbackSuccess = "[_medic, _patient, 0] call ACME_fnc_suctionOpen";
        callbackFailure = "";
    };
    // the ACCUVAC opens the same screen, with the device type set to 1. there is no visible progress bar and the
    // medic steers the suction themselves, so ACE completes at once and hands over.
    // note that fn_suctionopen does not create the dialog in this callback. it waits 0.1 s first, because ACE is
    // still closing its progress bar and reopening the medical menu on the frames right after callbacksuccess
    // returns, and a dialog made during that is destroyed by it.
    // the sound is not started here either. the screen owns it, because it has to start and stop with the trigger
    // rather than with a bar that has already finished.
    // UseSuctionBag above takes the same path. both devices are on the screen now.
    class UseAccuvac: UseSuctionBag {
        // the same 0.1 as the parent, restated so the value is visible on the class that uses it.

        treatmentTime = 0.1;
        callbackStart = "";
        callbackSuccess = "[_medic, _patient, 1] call ACME_fnc_suctionOpen";
        callbackFailure = "";
    };

    // the mannitol bolus button is removed. a medic gives mannitol through the normal medication push or the
    // custom syringe menu, not a dedicated button. acme_fnc_tbiosmobolus is retained for HTS.
    // calcium chloride push. it repletes ionized calcium in a massive transfusion and reverses citrate-driven
    // hypotension, through contractility, and coagulopathy.
    class ACME_GiveCalcium: CheckPulse {
        displayName = "Administer Calcium Gluconate (1g)";
        displayNameProgress = "Pushing calcium...";
        category = "medication";
        treatmentLocations[] = {"All"};
        medicRequired = 1;
        treatmentTime = 5;
        allowedSelections[] = {"Body","LeftArm","RightArm","LeftLeg","RightLeg"};
        // hidden. calcium gluconate is still givable through "Use Syringe", the narc box draw and administer, and as
        // an infusion. the class is kept. flip back to the item-count check to re-enable the bolus.
        condition = "false";
        callbackSuccess = "_this call ACME_fnc_administerCalcium";
        callbackFailure = "";
        callbackProgress = "";
        items[] = {"ACM_Vial_CalciumGluconate"};
        animationMedic = "AinvPknlMstpSnonWnonDr_medic4";
    };
    // magnesium sulfate, 2 g in 50 ml. it is first-line for torsades and polymorphic vt. the bolus ACE-menu action
    // is disabled, at condition false. magnesium is given only as a drip by default. hang the premixed magnesium
    // bag through add bag and it auto-registers as an infusion, in fn_syncpremixedbags. torsades termination is no
    // longer instant, because fn_circhandle waits for ACM's Magnesium_IV effect curve. the class is kept rather
    // than deleted, so the function wiring and inheritance are untouched. flip the condition back to re-enable the
    // bolus if it is ever needed.
    class ACME_GiveMagnesium: CheckPulse {
        displayName = "Administer Magnesium Sulfate (2g)";
        displayNameProgress = "Giving magnesium...";
        category = "medication";
        treatmentLocations[] = {"All"};
        medicRequired = 1;
        treatmentTime = 8;
        allowedSelections[] = {"Body","LeftArm","RightArm","LeftLeg","RightLeg"};
        condition = "false";
        callbackSuccess = "_this call ACME_fnc_administerMagnesium";
        callbackFailure = "";
        callbackProgress = "";
        items[] = {"ACME_MagnesiumBag"};
        animationMedic = "AinvPknlMstpSnonWnonDr_medic4";
    };
    // legacy medical-card hang bag action, retained only as a hidden compatibility class. hang bag now exists
    // exclusively in ACM's transfuse fluids dialog.
    class ACME_HangBag: CheckPulse {
        displayName = "Hang Bag (raise for high flow)";
        displayNameProgress = "Raising the bag...";
        category = "medication";
        treatmentLocations[] = {"All"};
        medicRequired = 0;
        treatmentTime = 1.5;
        allowedSelections[] = {"Body","LeftArm","RightArm","LeftLeg","RightLeg"};
        condition = "false";
        callbackStart = "_this call ACME_fnc_hangBagPrep";
        callbackSuccess = "_this call ACME_fnc_hangBagStart";
        callbackFailure = "[_medic] call ACME_fnc_hangBagPrepStop";
        callbackProgress = "";
        items[] = {};
        // played manually in callbackstart, so ACE's treatment animation speed limiter cannot skip it.
        animationMedic = "";
        animationMedicProne = "";
    };
    // core temperature. it is an active-use measurement of about 8 s, like a BVM hold, and then reports the core
    // temp and the clinical band. it requires the thermometer in the inventory and does not consume it, because
    // items[] is empty and it is reusable, with presence gated by the condition. it is the hypothermia
    // assessment.
    class ACME_ReadCoreTemp: CheckPulse {
        displayName = "Measure Core Temperature";
        displayNameProgress = "Taking core temperature...";
        category = "examine";
        treatmentLocations[] = {"All"};
        medicRequired = 0;
        treatmentTime = 8;
        allowedSelections[] = {"Body"};
        condition = "([_medic, 'ACM_Thermometer'] call ACME_fnc_itemCount) > 0";
        callbackSuccess = "_this call ACME_fnc_readCoreTemp";
        callbackFailure = "";
        callbackProgress = "";
        items[] = {};
        animationMedic = "AmovPknlMstpSrasWpstDnon_AmovPknlMstpSrasWpstDnon_gear";
    };
    // feel skin. it is a brief, color-coded outward skin sign, covering pallor, temperature and moisture, read
    // from perfusion and core temp. the same signs always show in the injury list, through skinInjuryEntry.
    class ACME_FeelSkin: CheckPulse {
        displayName = "Feel Skin";
        displayNameProgress = "Feeling skin...";
        category = "examine";
        treatmentLocations[] = {"All"};
        medicRequired = 0;
        treatmentTime = 2;
        allowedSelections[] = {"Head","Body","LeftArm","RightArm","LeftLeg","RightLeg"};
        condition = "true";
        callbackSuccess = "_this call ACME_fnc_feelSkin";
        callbackFailure = "";
        callbackProgress = "";
        items[] = {};
        animationMedic = "AmovPknlMstpSrasWpstDnon_AmovPknlMstpSrasWpstDnon_gear";
    };
    // it requires a prepared push-dose syringe, made from a flush. see the self actions.
    class ACME_PushDoseEpi: CheckPulse {
        displayName = "Push-Dose Epi (10 mcg IV/IO)";
        displayNameProgress = "Pushing epinephrine...";
        category = "medication";
        treatmentLocations[] = {"All"};
        medicRequired = "ACME_skillMedicationBolus";
        treatmentTime = 2;
        // the head is included for the same reason as the narc box: an established ej is a valid push site.
        allowedSelections[] = {"Head","Body","LeftArm","RightArm","LeftLeg","RightLeg"};
        condition = "([_medic, 'ACME_PushDoseEpi'] call ACME_fnc_procedureActionAllowed) && {(((_medic getVariable ['ACME_narcStore', []]) findIf {(_x param [6,'']) == 'epiMixB12'}) >= 0) && {([_patient, _bodyPart, 0] call ACM_circulation_fnc_hasIV) || {[_patient, _bodyPart, 0] call ACM_circulation_fnc_hasIO}}}";
        callbackSuccess = "_this call ACME_fnc_administerPushDoseEpi";
        callbackFailure = "";
        callbackProgress = "";
        items[] = {};
        animationMedic = "AinvPknlMstpSnonWnonDr_medic4";
    };
    // syringe kit, on the patient side. it opens ACM's own syringe-draw dialog targeting the patient, so a medic
    // can draw any medication from the inventory and administer it, with the same flow and drug list as ACM's "Use
    // Syringe". it is always accessible and lives in the medication category.
    class ACME_SyringeKit_DrawPatient: CheckPulse {
        displayName = "Narc Box: Draw + Administer";
        displayNameProgress = "Opening Narc Box...";
        category = "medication";
        treatmentLocations[] = {"All"};
        medicRequired = "ACME_skillMedicationPreparation";
        treatmentTime = 0.01;
        // the head is included because ej access is a real administration site. with an ej iv established a medic
        // draws and gives through the neck exactly as they would through a limb, so the box has to be reachable by
        // clicking the head. everything downstream is body-part agnostic and already treats the head as ej, because
        // fn_vesicantinjure maps it to peripheral ej access, so this gate was the only thing hiding it.
        allowedSelections[] = {"Head","Body","LeftArm","RightArm","LeftLeg","RightLeg"};
        condition = "([_medic, 'ACME_SyringeKit_DrawPatient'] call ACME_fnc_procedureActionAllowed) && {!isNil ""ACM_circulation_fnc_Syringe_Draw""}";
        callbackSuccess = "if ([_medic, 'medicationPreparation'] call ACME_fnc_procedureAllowed) then {ACME_infusion_pendingContext = nil; [10, _this select 1, _this select 2] call ACME_fnc_skOpenDraw;};";
        callbackFailure = "";
        callbackProgress = "";
        items[] = {};
        ACM_menuIcon = "ACME_NarcBox";
    };
    // scenario hook. it induces and clears fluid-refractory peri-arrest shock on a patient.
    class ACME_ToggleShock: CheckPulse {
        displayName = "Induce/Clear Peri-Arrest Shock";
        displayNameProgress = "";
        category = "advanced";
        treatmentLocations[] = {"All"};
        medicRequired = 1;
        treatmentTime = 0.01;
        allowedSelections[] = {"Head"};
        condition = "[] call ACME_fnc_debugEnabled";
        callbackSuccess = "_this call ACME_fnc_toggleShock";
        callbackFailure = "";
        callbackProgress = "";
        items[] = {};
    };
    // debug. it induces and clears over-resuscitation pulmonary edema, with crackles, hypoxia and tachypnea.
    class ACME_ToggleOverResus: CheckPulse {
        displayName = "Induce/Clear Over-Resuscitation (debug)";
        displayNameProgress = "";
        category = "advanced";
        treatmentLocations[] = {"All"};
        medicRequired = 1;
        treatmentTime = 0.01;
        allowedSelections[] = {"Head"};
        condition = "[] call ACME_fnc_debugEnabled";
        callbackSuccess = "_this call ACME_fnc_toggleOverResus";
        callbackFailure = "";
        callbackProgress = "";
        items[] = {};
    };
    class ACME_ToggleObtunded: CheckPulse {
        displayName = "Induce/Clear Obtunded Back (debug)";
        displayNameProgress = "";
        category = "advanced";
        treatmentLocations[] = {"All"};
        medicRequired = 1;
        treatmentTime = 0.01;
        allowedSelections[] = {"Head"};
        condition = "[] call ACME_fnc_debugEnabled";
        callbackSuccess = "_this call ACME_fnc_setObtunded";
        callbackFailure = "";
        callbackProgress = "";
        items[] = {};
    };
    class ACME_ToggleObtundedProne: ACME_ToggleObtunded {
        displayName = "Induce/Clear Obtunded Prone (debug)";
        callbackSuccess = "[_this select 0, _this select 1, _this select 2, 'prone'] call ACME_fnc_setObtunded";
    };
    class ACME_DebugObtundedBackPose: ACME_ToggleObtunded {
        displayName = "Obtunded BACK pose only (debug)";
        callbackSuccess = "_this call ACME_fnc_debugObtundedBack";
    };
    class ACME_ToggleHypothermia: CheckPulse {
        displayName = "Step Hypothermia: mild/mod/severe/clear (debug)";
        displayNameProgress = "";
        category = "advanced";
        treatmentLocations[] = {"All"};
        medicRequired = 1;
        treatmentTime = 0.01;
        allowedSelections[] = {"Head"};
        condition = "[] call ACME_fnc_debugEnabled";
        callbackSuccess = "_this call ACME_fnc_toggleHypothermia";
        callbackFailure = "";
        callbackProgress = "";
        items[] = {};
    };
    class ACME_RhythmAFibRVR: CheckPulse {
        displayName = "Rhythm: AFib-RVR on/off (debug)";
        displayNameProgress = "";
        category = "advanced";
        treatmentLocations[] = {"All"};
        medicRequired = 1;
        treatmentTime = 0.01;
        allowedSelections[] = {"Head"};
        condition = "[] call ACME_fnc_debugEnabled";
        callbackSuccess = "_this call ACME_fnc_rhythmAFibRVR";
        callbackFailure = "";
        callbackProgress = "";
        items[] = {};
    };
    class ACME_RhythmAFib: CheckPulse {
        displayName = "Rhythm: Atrial Fibrillation (controlled) on/off (debug)";
        displayNameProgress = "";
        category = "advanced";
        treatmentLocations[] = {"All"};
        medicRequired = 1;
        treatmentTime = 0.01;
        allowedSelections[] = {"Head"};
        condition = "[] call ACME_fnc_debugEnabled";
        callbackSuccess = "_this call ACME_fnc_rhythmAFib";
        callbackFailure = "";
        callbackProgress = "";
        items[] = {};
    };
    class ACME_RhythmAtrialTach: CheckPulse {
        displayName = "Rhythm: Atrial Tachycardia on/off (debug)";
        displayNameProgress = "";
        category = "advanced";
        treatmentLocations[] = {"All"};
        medicRequired = 1;
        treatmentTime = 0.01;
        allowedSelections[] = {"Head"};
        condition = "[] call ACME_fnc_debugEnabled";
        callbackSuccess = "_this call ACME_fnc_rhythmAtrialTach";
        callbackFailure = "";
        callbackProgress = "";
        items[] = {};
    };
    class ACME_RhythmTorsades: CheckPulse {
        displayName = "Rhythm: Torsades / polymorphic VT on/off (debug)";
        displayNameProgress = "";
        category = "advanced";
        treatmentLocations[] = {"All"};
        medicRequired = 1;
        treatmentTime = 0.01;
        allowedSelections[] = {"Head"};
        condition = "[] call ACME_fnc_debugEnabled";
        callbackSuccess = "_this call ACME_fnc_rhythmTorsades";
        callbackFailure = "";
        callbackProgress = "";
        items[] = {};
    };
    class ACME_RhythmSVT: CheckPulse {
        displayName = "Rhythm: SVT on/off (debug)";
        displayNameProgress = "";
        category = "advanced";
        treatmentLocations[] = {"All"};
        medicRequired = 1;
        treatmentTime = 0.01;
        allowedSelections[] = {"Head"};
        condition = "[] call ACME_fnc_debugEnabled";
        callbackSuccess = "_this call ACME_fnc_rhythmSVT";
        callbackFailure = "";
        callbackProgress = "";
        items[] = {};
    };
    class ACME_DebugVFXHypoxia: CheckPulse {
        displayName = "Visual FX: Hypoxia cycle (debug)"; displayNameProgress = ""; category = "advanced"; treatmentLocations[] = {"All"}; medicRequired = 1; treatmentTime = 0.01; allowedSelections[] = {"Head"}; condition = "[] call ACME_fnc_debugEnabled"; callbackSuccess = "[_this select 0,_this select 1,'hypoxia'] call ACME_fnc_visualFxDebugCycle"; callbackFailure = ""; callbackProgress = ""; items[] = {};
    };
    class ACME_DebugVFXHypotension: ACME_DebugVFXHypoxia {displayName = "Visual FX: Hypotension / shock cycle (debug)"; callbackSuccess = "[_this select 0,_this select 1,'hypotension'] call ACME_fnc_visualFxDebugCycle";};
    class ACME_DebugVFXHypercapnia: ACME_DebugVFXHypoxia {displayName = "Visual FX: Hypercapnia cycle (debug)"; callbackSuccess = "[_this select 0,_this select 1,'hypercapnia'] call ACME_fnc_visualFxDebugCycle";};
    class ACME_DebugVFXKetamine: ACME_DebugVFXHypoxia {displayName = "Visual FX: Ketamine / dissociation cycle (debug)"; callbackSuccess = "[_this select 0,_this select 1,'ketamine'] call ACME_fnc_visualFxDebugCycle";};
    class ACME_DebugVFXSyncope: ACME_DebugVFXHypoxia {displayName = "Visual FX: Near-syncope cycle (debug)"; callbackSuccess = "[_this select 0,_this select 1,'syncope'] call ACME_fnc_visualFxDebugCycle";};
    class ACME_DebugVFXClear: ACME_DebugVFXHypoxia {displayName = "Visual FX: Clear debug overrides"; callbackSuccess = "[_this select 0,_this select 1] call ACME_fnc_visualFxDebugClear";};
    // cheyne-stokes respirations, on and off, for debug. it drives a proper crescendo and decrescendo breathing
    // cycle with an apneic pause, independent of the TBI, so it can be demonstrated and tested on any casualty. a
    // medic's check breathing reads the live rate, and the capnography EtCO2 waxes and wanes with it.
    // Validate wording in the current mode without changing settings. No RPT output.
    class ACME_DebugDescriptorSelfTest: CheckPulse {
        displayName = "Descriptor Self-Test (debug)";
        displayNameProgress = "";
        category = "advanced";
        treatmentLocations[] = {"All"};
        medicRequired = 1;
        treatmentTime = 0.01;
        allowedSelections[] = {"Head"};
        condition = "[] call ACME_fnc_debugEnabled";
        callbackSuccess = "_this call ACME_fnc_descriptorSelfTest";
        callbackFailure = "";
        callbackProgress = "";
        items[] = {};
    };
    class ACME_DebugCheyneStokes: CheckPulse {
        displayName = "Respirations: Cheyne-Stokes on/off (debug)";
        displayNameProgress = "";
        category = "advanced";
        treatmentLocations[] = {"All"};
        medicRequired = 1;
        treatmentTime = 0.01;
        allowedSelections[] = {"Head"};
        condition = "[] call ACME_fnc_debugEnabled";
        callbackSuccess = "_this call ACME_fnc_debugCheyneStokes";
        callbackFailure = "";
        callbackProgress = "";
        items[] = {};
    };

    // Head-only seizure test. This enters the real ACME seizure physiology rather than playing gestures alone.
    // It is invisible unless the provider has the ACME Debug Menu setting enabled.
    class ACME_DebugInduceSeizure: CheckPulse {
        displayName = "Induce Seizure (debug)";
        displayNameProgress = "";
        category = "advanced";
        treatmentLocations[] = {"All"};
        medicRequired = 0;
        treatmentTime = 0.01;
        allowedSelections[] = {"Head"};
        condition = "([] call ACME_fnc_debugEnabled) && {alive _patient} && {!(_patient getVariable ['ace_medical_inCardiacArrest', false])}";
        callbackSuccess = "_this call ACME_fnc_debugInduceSeizure";
        callbackFailure = "";
        callbackProgress = "";
        animationMedic = "";
        animationMedicProne = "";
        items[] = {};
    };
    // field shortcut. an empty flush drawn from a hung dirty-epi bag is one 10 mcg push.
    class ACME_FlushDrawDirty: ACME_PushDoseEpi {
        medicRequired = 1;
        displayName = "Draw Push-Dose from Running Epi (10mcg)";
        displayNameProgress = "Drawing from dirty-epi bag...";
        category = "medication";
        treatmentTime = 4.946;
        condition = "false";  // B13: retired unmetered bag-charge route
        callbackStart = "playSound 'ACME_SyringeDraw'";
        callbackSuccess = "[_this select 0, _this select 1, _this select 2, ['drawDirty']] call ACME_fnc_salineFlush";
        items[] = {};
    };
    // flush the selected iv or io site. a medic uses it after an iv or io push med. it shows on any selected body
    // part that actually has an iv or io line and consumes one 10 ml saline flush. pending meds are delivered from
    // that site only, and pending meds parked in other lines stay parked until those sites are flushed.
    class ACME_FlushLine: ACME_PushDoseEpi {
        medicRequired = 1;
        displayName = "Flush IV Site (Saline)";
        displayNameProgress = "Flushing IV/IO site...";
        category = "medication";
        treatmentTime = 3;
        condition = "(([_medic, 'ACM_SalineFlush_10'] call ACME_fnc_itemCount) > 0) && {([_patient, _bodyPart, 0] call ACM_circulation_fnc_hasIV) || {[_patient, _bodyPart, 0] call ACM_circulation_fnc_hasIO}}";
        callbackStart = "playSound 'ACME_SyringeDraw'";
        callbackSuccess = "[_this select 0, _this select 1, _this select 2, ['flushLine']] call ACME_fnc_salineFlush";
        items[] = {};
    };
    // osmotherapy, pushed rather than hung.
    // fn_tbiosmobolus has existed and been complete since it was written, and nothing ever called it. its own
    // header said it was used by "the HTS 23.4 percent, 30 ml, bullet and the mannitol push treatment actions",
    // and neither of those actions existed, so the herniation rescue was unreachable. these are them.
    // the bound arguments are [agent, dose, item]. the agent selects the model branch in fn_tbiapplyosmotherapy,
    // the dose is ml for HTS and grams for mannitol, and the item is what gets consumed.
    // there is a sodium ceiling in the model, so this cannot be pushed indefinitely. above it osmotherapy stops
    // helping and arguably harms, which is the honest answer to a medic who reaches for it a fourth time.
    class ACME_OsmoBolus_HTS: CheckPulse {
        displayName = "Push 23.4% Hypertonic Saline";
        displayNameProgress = "Pushing hypertonic saline...";
        category = "medication";
        treatmentLocations[] = {"All"};
        medicRequired = "ACME_skillMedicationBolus";
        treatmentTime = 6;
        items[] = {"ACME_HTSBullet"};
        consumeItem = 0;
        allowedSelections[] = {"All"};
        allowSelfTreatment = 0;
        // no TBI gate. a medic decides to give osmotherapy on the findings in front of them, and being wrong about
        // that is the thing being taught. it is the same rule the NCD and the chest inspection follow.
        condition = "[_medic, 'ACME_OsmoBolus_HTS'] call ACME_fnc_procedureActionAllowed";
        callbackSuccess = "[_this select 0, _this select 1, _this select 2, ['HTS3', 30, 'ACME_HTSBullet']] call ACME_fnc_tbiOsmoBolus";
        callbackFailure = "";
        callbackProgress = "";
        litter[] = {};
    };
    class ACME_OsmoBolus_Mannitol: ACME_OsmoBolus_HTS {
        displayName = "Push Mannitol 20%";
        displayNameProgress = "Pushing mannitol...";
        items[] = {"ACME_MannitolVial"};
        callbackSuccess = "[_this select 0, _this select 1, _this select 2, ['Mannitol', 50, 'ACME_MannitolVial']] call ACME_fnc_tbiOsmoBolus";
    };
    // 18g placement, at the upper, middle and lower sites, which are the distal sites the danger model cares
    // about, listed upper first. accesssite is 0 for upper, 1 for middle and 2 for lower.
    class ACME_Place18g_Upper: CheckPulse {
        // no animation for anything to do with an IV. the work is done in the screen, and a treatment pose
        // played on the body at the same time reads as the medic doing something else entirely.
        // these inherit CheckPulse, which declares one, so it is silenced rather than left to the parent.
        animationMedic = "";
        animationMedicProne = "";
        displayName = "Place 18g IV (Upper)";
        ACM_menuIcon = "ACME_IV_18g";
        displayNameProgress = "Placing 18g IV...";
        category = "advanced";
        treatmentLocations[] = {"All"};
        medicRequired = 1;
        treatmentTime = 5;
        allowedSelections[] = {"LeftArm","RightArm","LeftLeg","RightLeg"};
        // hidden. peripheral IVs are placed through the "Establish IV" mini-game now. condition=false here also hides
        // middle and lower, because they inherit it. remove18g_* restate their own condition, so removal still
        // works.
        condition = "false";
        callbackSuccess = "[_this select 0, _this select 1, _this select 2, [0]] call ACME_fnc_place18g";
        callbackFailure = "";
        callbackProgress = "";
        items[] = {};
    };
    class ACME_Place18g_Middle: ACME_Place18g_Upper {
        displayName = "Place 18g IV (Middle)";
        callbackSuccess = "[_this select 0, _this select 1, _this select 2, [1]] call ACME_fnc_place18g";
    };
    class ACME_Place18g_Lower: ACME_Place18g_Upper {
        displayName = "Place 18g IV (Lower)";
        callbackSuccess = "[_this select 0, _this select 1, _this select 2, [2]] call ACME_fnc_place18g";
    };
    class ACME_Remove18g_Upper: ACME_Place18g_Upper {
        // no animation for anything to do with an IV. the work is done in the screen, and a treatment pose
        // played on the body at the same time reads as the medic doing something else entirely.
        // these inherit CheckPulse, which declares one, so it is silenced rather than left to the parent.
        animationMedic = "";
        animationMedicProne = "";
        displayName = "Remove 18g IV (Upper)";
        displayNameProgress = "Removing 18g IV...";
        treatmentTime = 3;
        medicRequired = 0;
        // HIDDEN at v0.9.999r-42. an IV comes out in the IV screen now: take hold of the hub and pull it.
        // the button did the same job from a menu and it made the removal look like a treatment rather than
        // something done with the hands. the class and the callback stay, so restoring the button is one line.
        // to restore: condition = "!isNil 'ACM_circulation_fnc_hasIV' && {[_patient, _bodyPart, 5, 0] call ACM_circulation_fnc_hasIV}";
        condition = "false";
        callbackSuccess = "[_this select 0, _this select 1, _this select 2, [0]] call ACME_fnc_remove18g";
    };
    class ACME_Remove18g_Middle: ACME_Remove18g_Upper {
        displayName = "Remove 18g IV (Middle)";
        condition = "false";  // see ACME_Remove18g_Upper. a child must restate this or it inherits nothing.
        callbackSuccess = "[_this select 0, _this select 1, _this select 2, [1]] call ACME_fnc_remove18g";
    };
    class ACME_Remove18g_Lower: ACME_Remove18g_Upper {
        displayName = "Remove 18g IV (Lower)";
        condition = "false";  // see ACME_Remove18g_Upper.
        callbackSuccess = "[_this select 0, _this select 1, _this select 2, [2]] call ACME_fnc_remove18g";
    };
};

// norepinephrine medication concentration. ACM's syringe_draw reads three keys from
// ACM_Medication>concentration><med>. concentration is a number in mg/ml, used to compute the drawn dose. dose
// is the text label shown in the draw dialog. volume is a number, the vial ml, which becomes
// syringedraw_maxdose, the bottom limit of the plunger.
// an earlier version set concentration only, so volume read 0 and the plunger froze, because linearconversion
// [0,size,0,top,bottom] collapses the travel to the top.
// levophed is 4 mg in 4 ml, so 1 mg/ml. it merges additively with ACM's table.
class ACM_Medication {
    class MedicationType {
        class Norepinephrine { classnames[] = {"Norepinephrine_IV"}; };
        class Sugammadex { classnames[] = {"Sugammadex_IV"}; };
        class Magnesium { classnames[] = {"Magnesium_IV"}; };
        class Midazolam { classnames[] = {"Midazolam_IV", "Midazolam"}; };
        class CalciumGluconate { classnames[] = {"CalciumGluconate_IV"}; };
        class Ceftriaxone { classnames[] = {"Ceftriaxone_IV", "Ceftriaxone"}; };
        class Rocuronium { classnames[] = {"Rocuronium_IV", "Rocuronium"}; };
        class Propofol { classnames[] = {"Propofol_IV"}; };
        class Phentolamine { classnames[] = {"Phentolamine"}; };
        class Hyaluronidase { classnames[] = {"Hyaluronidase"}; };
    };

    class Concentration {
        class EpinephrineCardiac {
            concentration = 0.1; // mg/mL, NOT the original 1 mg/mL vial
            dose = "1mg/10ml (1:10,000)";
            volume = 10;
        };
        // The Extended fentanyl inventory item is the 500 mcg / 10 mL presentation. Keep the native
        // 0.05 mg/mL concentration, but its source capacity/dose label must match that physical vial rather than
        // ACM's stock 100 mcg / 2 mL presentation.
        class Fentanyl {
            concentration = 0.05;
            dose = "500mcg/10ml";
            volume = 10;
        };
        class Norepinephrine {
            concentration = 1;  // mg/ml.
            dose = "4mg/4ml";  // display label.
            volume = 4;  // vial ml, which becomes the max draw and the plunger travel.
        };
        // HTS3 is osmotic rather than mg-dosed. the infusion loop drives osmotherapy by the ml delivered, not by a
        // medication pulse. the concentration is nominal, and volume sets the plunger travel for the draw dialog.
        class HTS3 {
            concentration = 30;  // nominal. 3 percent NaCl is 513 mosm/l, and the osmo path does not use this.
            dose = "3% NaCl";  // display label.
            volume = 10;  // ml, which becomes the max draw and the plunger travel.
        };
        // new infusible drugs, the drug layer. concentration is mg/ml and volume is the vial ml, which is the plunger
        // travel.
        class Ceftriaxone {
            concentration = 100;  // 1 g in 10 ml.
            dose = "1g/10ml";
            volume = 10;
        };
        class CalciumGluconate {
            concentration = 100;  // 5 g in 50 ml, a 10 percent solution.
            dose = "5g/50ml";
            volume = 50;
        };
        // propofol, 500 mg in 50 ml, so 10 mg/ml. it is a sedative-hypnotic, drawable and pushable, with the infusion
        // to come once the pump lands.
        class Propofol {
            concentration = 10;  // mg/ml, from 500 mg in 50 ml.
            dose = "500mg/50ml";
            volume = 50;  // ml, which becomes the plunger travel.
        };
        class Midazolam {
            concentration = 1;  // 5 mg in 5 ml.
            dose = "5mg/5ml";
            volume = 5;
        };
        // rocuronium, 100 mg in 10 ml, so 10 mg/ml. it is a paralytic. ACME_fnc_rocuroniumOnBoard reads the recorded
        // dose, concentration times ml/100, to gate paralysis. a 1 mg/kg intubating dose, about 70 to 100 mg, is a
        // full or near-full 10 ml draw.
        class Rocuronium {
            concentration = 10;  // mg/ml, from 100 mg in 10 ml.
            dose = "100mg/10ml";
            volume = 10;
        };
        // sugammadex, 500 mg in 5 ml, so 100 mg/ml. it is the reversal agent, dosed by weight in mg/kg. the recorded
        // dose is concentration times ml/100, so a full 5 ml vial records 5.0, which is 500 mg, because the recorded
        // value times 100 gives milligrams.
        // the field dose is 16 mg/kg, so a 70 kg casualty needs 1120 mg, which is three of these vials. the 500 mg
        // presentation exists precisely so that dose is carryable. the 200 mg one was not.
        class Sugammadex {
            concentration = 100;  // mg/ml, from 500 mg in 5 ml.
            dose = "500mg/5ml";
            volume = 5;
        };
        // extravasation antidotes, as drawable and pushable vials. they are dosed by the volume delivered at the
        // affected site, and the reversal is applied in the vesicant eh rather than by an ACM systemic effect.
        class Phentolamine {
            concentration = 5;  // mg/ml, from 5 mg in 1 ml, reconstituted.
            dose = "5mg/1ml";
            volume = 1;
        };
        class Hyaluronidase {
            concentration = 150;  // units/ml, from 150 u in 1 ml. the concentration is nominal, because the reversal is volume-driven.
            dose = "150U/1ml";
            volume = 1;
        };
    };

    // intranasal esketamine analgesia. ACM's medicationlocal looks up the effect by the treatment-action classname,
    // 'esketamine', so this block, merged additively into ACM_Medication>medications, is what the in spray
    // actually does. it is modeled on ketamine but through the inhalant and in route, the same mechanism penthrox
    // uses.
    // it gives strong analgesia, through painreduce, reached fast through the in onset.
    // it has a mild positive hrincrease, so it is sympathomimetic and tolerated in shock and hemodynamic
    // instability, instead of dropping hr and bp the way an opioid does.
    // it has zero rr and breathing-effectiveness change, so respiratory depression is minimal and the gag reflex
    // is preserved.
    class Medications {
        class ACM_Inhalant_Medication;  // external base, from ACM. it is the intranasal and inhaled route.
        class ACM_IV_Medication;  // external base, from ACM. it is the iv push and infusion route.
        class ACM_IM_Medication;  // external base, from ACM. it is the im route.
        class Ertapenem_IV;  // external, from ACM. ceftriaxone inherits its effect.
        class Ertapenem;  // external, from ACM.
        // Ceftriaxone keeps its own record identity on every route. Native Ertapenem
        // effect type is retained for the game's shared antibiotic-care abstraction.

        // Naloxone deliberately inherits the supplied ACM handler and timing unchanged.
        class Midazolam: ACM_IM_Medication {
            timeTillMaxEffect = 900;  // B13: slower IM absorption; game-calibrated peak, not a clinical PK fit.
            timeInSystem = 3600;
            maxEffectTime = 900;
        };
        // B14: ketamine's shared dose-dependent cardiovascular helper owns chronotropy.
        // Re-declaring the class against ACM_IM/IV_Medication replaces the upstream Ketamine class at config merge,
        // so every Ketamine-specific value must be retained explicitly here. Otherwise it silently falls back to the
        // generic 1 mg/default clocks and ceases to behave like ACM Ketamine even when the medication record exists.
        class Adenosine_IV: ACM_IV_Medication {
            timeTillMaxEffect = 1; maxEffectTime = 1; timeInSystem = 15;
            hrIncrease[] = {0,0}; // short AV-nodal helper owns this effect; no long native brady tail.
        };
        class Ketamine: ACM_IM_Medication {
            medicationType = "Ketamine";
            minPainReduce = 0.4;
            painReduce = 0.95;
            maxPainReduce = 1;
            hrIncrease[] = {0,0};
            timeInSystem = 900;
            timeTillMaxEffect = 20;
            maxEffectTime = 600;
            maxDose = 500;
            maxDoseDeviation = 100;
            minEffectDose = 41.5;
            maxEffectDose = 62.25;
        };
        class Ketamine_IV: ACM_IV_Medication {
            medicationType = "Ketamine";
            minPainReduce = 0.5;
            painReduce = 0.85;
            maxPainReduce = 1;
            hrIncrease[] = {0,0};
            timeInSystem = 660;
            timeTillMaxEffect = 5;
            maxEffectTime = 540;
            maxDose = 250;
            maxDoseDeviation = 50;
            minEffectDose = 8.3;
            maxEffectDose = 16.6;
        };

        // Local infiltration classes. These exit medicationLocal before systemic deposition.
        class Phentolamine: ACM_IM_Medication {
            medicationType = "Phentolamine";
            minEffectDose = 5; maxEffectDose = 5; weightEffect = 0;
            painReduce = 0; hrIncrease[] = {0,0}; rrAdjust[] = {0,0}; maxDose = 0;
        };
        class Hyaluronidase: ACM_IM_Medication {
            medicationType = "Hyaluronidase";
            minEffectDose = 150; maxEffectDose = 150; weightEffect = 0;
            painReduce = 0; hrIncrease[] = {0,0}; rrAdjust[] = {0,0}; maxDose = 0;
        };
        class Ceftriaxone_IV: Ertapenem_IV {};
        class Ceftriaxone: Ertapenem {};
        // Rocuronium has no analgesia or sedation. B13 paralysis state owns apnea;
        // no native negative RR term remains after dose-specific reversal.
        class Sugammadex_IV: ACM_IV_Medication {
            medicationType = "Sugammadex";
            minPainReduce = 0;
            painReduce = 0;  // a reversal agent, not an analgesic.
            maxPainReduce = 0;
            hrIncrease[] = {0, 0};  // clinically near-inert on the vitals.
            maxHRIncrease = 0;
            rrAdjust[] = {0, 0};  // it does not drive respiration. it removes what was suppressing it.
            maxRRAdjust = 0;
            breathingEffectivenessAdjust[] = {0, 0};
            maxBreathingEffectivenessAdjust = 0;
            timeInSystem = 2100;  // Donor activity expires; already bound mass stays linked to its target record.
            timeTillMaxEffect = 150;  // about 2.5 min to full reversal, which is the real sugammadex onset.
            maxEffectTime = 1500;
            maxDose = 0;  // 16 mg/kg needs several vials, so do not cap that out.
            incompatibleMedication[] = {};
            viscosityChange = 0;

            minEffectDose = 100;

            maxEffectDose = 100;

            weightEffect = 0;

            maxDoseDeviation = 0;
};

        class Rocuronium_IV: ACM_IV_Medication {
            medicationType = "Rocuronium";
            minPainReduce = 0;
            painReduce = 0;  // a paralytic is not an analgesic.
            maxPainReduce = 0;
            hrIncrease[] = {0, 0};
            maxHRIncrease = 0;
            rrAdjust[] = {0, 0};  // B13: patient paralysis state owns apnea; no unreversed native RR penalty.
            maxRRAdjust = 0;
            breathingEffectivenessAdjust[] = {0, 0};  // do not impair gas exchange. a BVM or a vent oxygenates normally.
            maxBreathingEffectivenessAdjust = 0;
            timeInSystem = 2400;  // about 40 min of clinical duration.
            timeTillMaxEffect = 60;  // about 60 s to full paralysis, which is the real rocuronium onset.
            maxEffectTime = 1800;  // about 30 min of full block before it starts to wear off.
            maxDose = 0;
            maxDoseDeviation = 0;
            minEffectDose = 24.9;
            maxEffectDose = 83;
        };
        class Rocuronium: Rocuronium_IV {
            medicationType = "Rocuronium";
            timeTillMaxEffect = 90;  // Legacy class retained for config compatibility; new non-IV administration is blocked.
        };
        // calcium chloride, the class every calcium infusion is delivered as. gluconate is routed here too.
        // ACM ships CalciumChloride_IV with hrincrease[] = {1, 10}. for a continuous drip the per-pulse concentration
        // ratio sits well under 0.5, and ACM's unclamped linearconversion [0.5, 1, ratio, 1, 10] in medicationlocal
        // extrapolates that curve backwards to a large negative value, about -7 bpm per pulse. the infusion then
        // accumulates those into progressive bradycardia and arrest, even at a therapeutic drip such as 1 g in 50 ml
        // at 100 gtt/min. this is the same misfire already zeroed for esmolol, epi, norepi and mag, and calcium was
        // the one that got missed.
        // zero the native chronotropy and let fn_circhandle own the genuine fast-push bradycardia of calcium, which
        // only bites a true rapid push at 500 mg/min or more, not a slow drip. the hyperkalemia and hypocalcemia
        // effect of calcium, in handlemed_calciumchloridelocal and the medication effect level, is untouched, and only
        // the misfiring hr term is removed. the other props mirror ACM's stock values.
        class CalciumChloride_IV: ACM_IV_Medication {
            hrIncrease[] = {0, 0};
            // Retained gameplay timing, not a liver-metabolism model or validated clinical PK.
            timeInSystem = 2700;  // 45 min total. the clinical range is 30 to 60.
            timeTillMaxEffect = 300;  // 5 min to peak.
            maxEffectTime = 600;  // 10 min plateau, then a 30 min taper.
            viscosityChange = -10;
            unstableDose = 4000;
            maxEffectDose = 1000;
            weightEffect = 0;
        };
        class CalciumGluconate_IV: ACM_IV_Medication {
            medicationType = "CalciumGluconate";
            hrIncrease[] = {0, 0};  // the same infusion-pulse misfire guard. gluconate has no meaningful chronotropy.
            // Retained slower gameplay envelope; calcium gluconate does not require hepatic activation.
            timeInSystem = 2700;  // 45 min total.
            timeTillMaxEffect = 420;  // 7 min to peak. the clinical range is 5 to 10.
            maxEffectTime = 600;  // 10 min plateau.
            viscosityChange = -6;
            unstableDose = 12000;
            maxEffectDose = 3000;
            weightEffect = 0;
        };
        // amiodarone. ACM ships hrincrease[] = {-5, -10}. on a continuous drip ACM's medicationlocal accumulates one
        // hr-adjustment record per pulse, and each small-ratio pulse extrapolates toward 0 but they sum, so a long
        // drip stacks into a spurious deep bradycardia. that is the same per-pulse accumulation already zeroed for the
        // other drips.
        // zero the native chronotropy so the amiodarone drip runs clean. fn_circhandle owns the real drip consequences
        // of amiodarone, the fast-infusion hypotension and the cumulative qt ceiling that induces torsades. the
        // antiarrhythmic effect level, from getmedicationeffect, and the cumulative dose are unchanged.
        class Amiodarone_IV: ACM_IV_Medication {
            medicationType = "Amiodarone";
            hrIncrease[] = {0, 0};
            timeInSystem = 720;
            timeTillMaxEffect = 10;
            maxEffectTime = 480;
            maxDose = 2200;
            maxDoseDeviation = 200;
            unstableDose = 900;
            maxEffectDose = 150;
            weightEffect = 0;
        };
        // midazolam iv. ACM ships an im midazolam only, so this mirrors it as iv, with a faster onset, so it can be
        // pushed or infused. the medicationtype is "Midazolam", so its hr and rr depression group under one cap.
        // hrincrease is zeroed, because ACM ships {-1,-5}, which on a continuous drip accumulates one per-pulse record
        // into a spurious bradycardia. that is the same misfire zeroed for the other drips. the respiratory
        // depression, rradjust, is the clinically important effect and is unchanged, and the mild chronotropy of
        // midazolam is not modeled separately.
        class Midazolam_IV: ACM_IV_Medication {
            medicationType = "Midazolam";
            // clinical timing. iv midazolam takes 1 to 3 min to start and peaks at 3 to 5 min, and the sedation then runs
            // 30 to 60 min. the inherited values peaked in 10 s and were gone in 20 min, so the respiratory depression
            // arrived instantly and wore off far too early. the slower ramp is what makes titrating it a real skill,
            // because you have to wait for the last dose before you decide you need another.
            timeInSystem = 2700;  // 45 min total. the clinical range is 30 to 60.
            timeTillMaxEffect = 240;  // 4 min to peak. the clinical range is 3 to 5.
            maxEffectTime = 600;  // 10 min plateau, then a long benzo taper.
            hrIncrease[] = {0, 0};
            rrAdjust[] = {-1, -4};
            maxDose = 30;
            maxDoseDeviation = 10;
            unstableDose = 20;
            maxEffectDose = 5;
            weightEffect = 0;
        };
        // propofol iv, a sedative-hypnotic. it is fast on and fast off, with a short timeInSystem. its signature
        // clinical costs are dose-dependent hypotension and respiratory depression or apnea, so it carries a real
        // rradjust and a low unstabledose, past which it destabilizes the patient. hrincrease is zeroed like the other
        // drips, to avoid the per-pulse chronotropy misfire. fn_circhandle owns the deeper propofol-specific
        // hypotension, so it reads as a drip and push consequence, matching how the other cardio-active drugs are
        // handled.
        class Propofol_IV: ACM_IV_Medication {
            medicationType = "Propofol";
            // propofol genuinely is fast, so only the peak needed correcting. it acts in 15 to 45 s and peaks at 1 to 2
            // min, not the 8 s configured here. timeInSystem stays at 480, because a single bolus really is gone in 5 to
            // 10 min by redistribution, so that number was already right.
            timeInSystem = 480;  // 8 min, which is already clinical for a single bolus.
            timeTillMaxEffect = 90;  // 1.5 min to peak. the clinical range is 1 to 2.
            maxEffectTime = 180;  // 3 min plateau, then the redistribution taper.
            hrIncrease[] = {0, 0};
            rrAdjust[] = {-2, -6};  // respiratory depression and apnea at dose.
            painReduce = 0;  // a hypnotic, not an analgesic.
            maxDose = 400;
            maxDoseDeviation = 50;
            unstableDose = 200;  // hypotension and apnea past a real induction dose.
            maxEffectDose = 100;
            weightEffect = 1;
        };
        // norepinephrine and magnesium are ACM extended drugs, so we define real ACM_Medication entries for them
        // instead of letting medicationlocal fall through to the zero or default class. infusion pulses now create
        // normal ACM medication-adjustment records with an onset, a plateau and a washout.
        class Norepinephrine_IV: ACM_IV_Medication {
            medicationType = "Norepinephrine";
            timeInSystem = 360;
            timeTillMaxEffect = 30;
            maxEffectTime = 240;
            hrIncrease[] = {0, 0};  // no chronotropy. norepi is a pure vasoconstrictor, and clinically it gives a reflex bradycardia. bp is delivered through real peripheral resistance, from fn_circhandle into the updatePeripheralResistance override.
            maxDose = 1;
            maxDoseDeviation = 0.5;
            unstableDose = 1;
            maxEffectDose = 0.08;  // 80 mcg is the effective reference for small titrated pressor pulses.
            weightEffect = 0;
        };
        class Magnesium_IV: ACM_IV_Medication {
            medicationType = "Magnesium";
            timeInSystem = 1800;
            timeTillMaxEffect = 90;
            maxEffectTime = 900;
            hrIncrease[] = {0, 0};
            rrAdjust[] = {0, 0};
            maxDose = 4000;
            maxDoseDeviation = 1000;
            unstableDose = 6000;
            maxEffectDose = 2000;  // the 2 g therapeutic torsades dose.
            weightEffect = 0;
        };
        // esmolol. ACM's stock entry carries hrincrease[] = {-10,-25}, but ACM's per-delivery medication hr adjustment
        // misfires for a continuous infusion. at the low per-delivery concentration of a slow drip, where _dose over
        // maxEffectDose is well under 0.5, ACM's unclamped linearconversion [0.5,1,ratio,-10,-25] in medicationlocal
        // extrapolates the curve the wrong way to a small positive value. the infusion then accumulates those into a
        // large positive total, and a beta-blocker drove a sinus patient's hr to about 170.
        // zero the hr adjustment here and let fn_circhandle own the chronotropy of esmolol, off the bounded esmolol
        // effect. that covers rate control for SVT, atrial tach and AFib-RVR, and a bounded sinus slowing. the effect
        // level of the drug, from getmedicationeffect, is unchanged, so the rate-control gate still develops
        // normally.
        class Esmolol_IV: ACM_IV_Medication {
            hrIncrease[] = {0, 0};
            timeInSystem = 320;
            timeTillMaxEffect = 20;
            maxEffectTime = 240;
            unstableDose = 45;
            minEffectDose = 20.75;
            maxEffectDose = 41.5;
            weightEffect = 1;
        };
        // epinephrine. ACM's stock entry carries hrincrease[] = {10,20} and rradjust[] = {2,8}, and both misfire for a
        // continuous infusion, a dirty-epi drip. medicationlocal fires per delivery and registers a medication
        // adjustment each time, and over a drip those accumulate. rradjust accumulates straight to the rr cap, which
        // is the report that dirty epi only drives rr to 60, and hrincrease is a latent hr runaway at faster drip
        // rates. at the slow rate in the trace it extrapolated to about 0, so hr sat flat.
        // zero both here. the mod owns the hemodynamics of epi: bp through the pressor system, presdrive, and hr
        // through a chronotropic drive in fn_circhandle keyed off the bounded epi effect, from getmedicationeffect,
        // which covers a push and a drip and cannot run away. breathingEffectivenessAdjust and viscositychange are
        // left as they are, because they are not implicated. they can be zeroed too if they ever creep on a long
        // drip.
        class Epinephrine_IV: ACM_IV_Medication {
            medicationType = "Epinephrine";
            timeInSystem = 300;
            maxEffectTime = 180;
            hrIncrease[] = {0, 0};
            rrAdjust[] = {0, 0};
            breathingEffectivenessAdjust[] = {0.01, 0.04};
            viscosityChange = 5;
            unstableDose = 4;
            maxEffectDose = 1;
            weightEffect = 0;
        };
        class EpinephrineCardiac_IV: Epinephrine_IV {
            medicationType = "Epinephrine";
        };
        // lidocaine. ACM's stock entry is hrincrease[] = {-2,-10}, which is correctly rate-slowing for an
        // antiarrhythmic, but the same unclamped linearconversion that bit esmolol bites here. for a continuous drip
        // the per-delivery concentration is tiny, the conversion extrapolates the negative anchors to a small positive
        // value near +6, and ACM accumulates that every delivery, so hr runs away. the trace showed 102 climbing to
        // 234 while lidoeff was pinned at 1, and the bp rise and the rr collapse to 0 followed the runaway state
        // rather than lidocaine, which has no rradjust.
        // zero hrincrease here. lidocaine is not a chronotrope, so unlike epi the mod adds no hr drive of its own, and
        // the antiarrhythmic action, vt suppression, already runs off the bounded ACME_fnc_lidoEffectiveness.
        class Lidocaine_IV: ACM_IV_Medication {
            medicationType = "Lidocaine_IV";
            hrIncrease[] = {0, 0};
            timeInSystem = 600;
            maxEffectTime = 360;
            maxDose = 270;
            maxDoseDeviation = 50;
            unstableDose = 240;
            maxEffectDose = 83;
        };
        class Esketamine: ACM_Inhalant_Medication {
            medicationType = "Ketamine";  // B14: nasal product units retain their own absorption and potency.
            minPainReduce = 0.45;
            painReduce = 0.80;  // strong sub-dissociative in analgesia.
            maxPainReduce = 0.85;
            hrIncrease[] = {0, 0};  // B14 shared ketamine hemodynamics owns all route contributions.
            maxHRIncrease = 10;
            rrAdjust[] = {0, 0};  // respiration is preserved.
            maxRRAdjust = 0;
            breathingEffectivenessAdjust[] = {0, 0};  // the gag reflex and ventilation are preserved, unlike an opioid.
            // clinical timing, corrected. nasal absorption is not instant. prehospital nasal s-ketamine dropped vas from
            // 10 to 3 by 5 min, and the measured nasal plasma peak is 18 plus or minus 13 min. the old values peaked in 6
            // s and were gone in 6 min, which made an atomizer act faster than an iv push and wear off before the casualty
            // could realistically be moved. ACE ramps the effect linearly to timeTillMaxEffect, so 600 puts the patient at
            // roughly half effect at the 5 min mark and full by 10, which matches the observed curve.
            timeInSystem = 3600;  // 60 min total. in analgesia runs 45 to 90 min, and 60 is the planning figure.
            timeTillMaxEffect = 600;  // 10 min to peak.
            maxEffectTime = 600;  // it holds through 20 min, so the peak effect spans the clinical 10 to 20 min window.
            maxDose = 4;
            maxDoseDeviation = 1;
            minEffectDose = 0.5;
            maxEffectDose = 1.0;
        };
    };
};

// on-screen EMMA capnograph HUD. it is a title resource, so it captures no input, and fn_emmatick shows, hides
// and updates it. fn_emmabuilddisplay builds every control at runtime, in onload, so their geometry can be
// computed from the safezone and tuned live through the acme_emma_* globals.
class RscTitles {
    class ACME_EMMA_Display {
        idd = 71500;
        movingEnable = 0;
        enableSimulation = 1;
        duration = 1e11;  // it stays up until fn_emmatick takes it down.
        fadeIn = 0;
        fadeOut = 0;
        onLoad = "uiNamespace setVariable ['ACME_EMMA_DLG', (_this select 0)]; (_this select 0) call ACME_fnc_emmaBuildDisplay;";
        onUnload = "uiNamespace setVariable ['ACME_EMMA_DLG', displayNull];";
        class Controls {};
    };
    // hearing-impaired BVM ventilation cue: a single blue radial-gradient circle. fn_bvmventtick animates its size
    // and alpha each frame, and it is invisible at alpha 0 between ventilations, and raises and drops the layer.
    class ACME_BVMVent_Display {
        idd = 71510;
        movingEnable = 0;
        enableSimulation = 1;
        duration = 1e11;
        fadeIn = 0;
        fadeOut = 0;
        onLoad = "uiNamespace setVariable ['ACME_BVMVent_DLG', (_this select 0)];";
        onUnload = "uiNamespace setVariable ['ACME_BVMVent_DLG', displayNull];";
        class Controls {
            class ACME_BVMVent_Circle: RscPicture {
                idc = 71511;
                text = "\acm_extended\ui\dot_grad_ca.paa";
                colorText[] = {0.30, 0.55, 1.0, 0.0};  // blue. fn_bvmventtick drives the alpha.
                x = "safezoneX + safezoneW/2 - 0.025";
                y = "safezoneY + safezoneH/2 - 0.025";
                w = 0.05;
                h = 0.05;
            };
        };
    };
    // B125 one-handed medication push HUD. Static picture controls are intentional: dynamically-created
    // picture controls were surviving as text/panel controls on some ultrawide clients while the PAA layers
    // disappeared. The RscTitles resource keeps the syringe visual independent from ACE dialog rebuilds.
    class ACME_HCPush_Display {
        idd = 71520;
        movingEnable = 0;
        enableSimulation = 1;
        duration = 1e11;
        fadeIn = 0;
        fadeOut = 0;
        onLoad = "uiNamespace setVariable ['ACME_HCPush_DLG', (_this select 0)];";
        onUnload = "uiNamespace setVariable ['ACME_HCPush_DLG', displayNull];";
        class Controls {
            class ACME_HCPush_Backbit: RscPicture {
                idc = 71521;
                text = "\acm_extended\ui\syringe\hud\syringe_10_backbit_ca.paa";
                colorText[] = {1,1,1,1};
                x = 0; y = 0; w = 0.1; h = 0.1;
            };
            class ACME_HCPush_Plunger: ACME_HCPush_Backbit {
                idc = 71522;
                text = "\acm_extended\ui\syringe\hud\syringe_10_plunger_ca.paa";
            };
            class ACME_HCPush_Barrel: ACME_HCPush_Backbit {
                idc = 71523;
                text = "\acm_extended\ui\syringe\hud\syringe_10_barrel_ca.paa";
            };
            class ACME_HCPush_Panel: RscText {
                idc = 71524;
                text = "";
                colorText[] = {1,1,1,0};
                colorBackground[] = {0.02,0.03,0.06,0.90};
                x = 0; y = 0; w = 0.2; h = 0.05;
            };
            class ACME_HCPush_Text: RscStructuredText {
                idc = 71525;
                text = "";
                colorText[] = {0.94,0.91,0.82,1};
                colorBackground[] = {0,0,0,0};
                x = 0; y = 0; w = 0.2; h = 0.05;
            };
        };
    };
};

// Named remote-execution surface only. Do not change mission-wide remote execution modes.
// These entries allow missions that import mod CfgRemoteExec and run Functions mode = 1 to keep ACME's
// multiplayer owner/server dispatch paths working without whitelisting raw script commands.
class CfgRemoteExec {
    class Functions {
        class ACM_airway_fnc_remoteSay3D { allowedTargets = 0; };

        class ACME_fnc_blastLungInflict { allowedTargets = 0; };
        class ACME_fnc_bloodColdChainNudge { allowedTargets = 2; };
        class ACME_fnc_bloodFridgeSpawn { allowedTargets = 2; };
        class ACME_fnc_ccApply { allowedTargets = 0; };
        class ACME_fnc_coolerBoxApplyScale { allowedTargets = 0; jip = 1; };
        class ACME_fnc_edemaSet { allowedTargets = 0; };
        class ACME_fnc_forceWalkLocal { allowedTargets = 0; };
        class ACME_fnc_megacodeArrest { allowedTargets = 0; };
        class ACME_fnc_megacodeCableApply { allowedTargets = 2; };
        class ACME_fnc_megacodeChestInjury { allowedTargets = 0; };
        class ACME_fnc_megacodeClearWounds { allowedTargets = 0; };
        class ACME_fnc_megacodeLog { allowedTargets = 0; };
        class ACME_fnc_megacodeMenu { allowedTargets = 0; };
        class ACME_fnc_megacodePanelRetarget { allowedTargets = 0; };
        class ACME_fnc_megacodeResetUnit { allowedTargets = 0; };
        class ACME_fnc_megacodeScenario { allowedTargets = 0; };
        class ACME_fnc_remoteDeleteVehicle { allowedTargets = 2; };
        class ACME_fnc_remoteSay3D { allowedTargets = 0; };
        class ACME_fnc_zeusClearTBILocal { allowedTargets = 0; };
        class ACME_fnc_zeusInflictJunctionalLocal { allowedTargets = 0; };
        class ACME_fnc_zeusTBIApplyLocal { allowedTargets = 0; };
    };
};
