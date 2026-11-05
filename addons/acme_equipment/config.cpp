// The existing ACME inventory and clinical state remain authoritative.
#include "..\main\script_build.hpp"
class CfgPatches {
    class acme_equipment {
        ACME_BUILD_CONFIG("equipment");
        name = "ACME medical equipment integration";
        author = "mavis";
        requiredVersion = 2.20;
        requiredAddons[] = {"ACM_Extended", "acme_accuvac", "acme_bloodcooler", "acme_hpmk", "acme_ventway", "acme_tempus", "acme_tempusls"};
        units[] = {"ACME_TempusPro_Mount","ACME_TempusLS_Mount"};
        weapons[] = {};
    };
};
class CfgWeapons {
    class ACE_ItemCore;
    class ACM_SuctionBag;
    class ACME_Ventilator: ACE_ItemCore {
        model = "\acme_ventway\ventway_bare.p3d";
        picture = "\acme_ventway\data\ui\icon_ventway_ca.paa";
        hiddenSelections[] = {"camo", "screen", "screen_fio2"};
        hiddenSelectionsTextures[] = {"\acme_ventway\data\ventway_body_co.paa", "\acme_ventway\data\ventway_screen_off_co.paa", "\acme_ventway\data\ventway_screen_off_co.paa"};
    };
    class ACM_ACCUVAC: ACM_SuctionBag {
        model = "\acme_accuvac\accuvac_rescue.p3d";
        picture = "\acme_accuvac\data\ui\icon_accuvac_ca.paa";
        hiddenSelections[] = {"camo", "cover"};
        hiddenSelectionsTextures[] = {"\acme_accuvac\data\accuvac_body_co.paa", "\acme_accuvac\data\accuvac_cover_co.paa"};
    };
    class ACM_HPMK: ACE_ItemCore {
        model = "\acme_hpmk\hpmk_pouch.p3d";
        picture = "\acme_hpmk\data\ui\icon_hpmk_ca.paa";
    };
    class ACME_BloodCooler_CSWB1U: ACE_ItemCore {
        model = "\acme_bloodcooler\bloodcooler1u_closed.p3d";
        picture = "\acme_bloodcooler\data\ui\icon_bloodcooler1u_ca.paa";
        hiddenSelections[] = {"camo"};
        hiddenSelectionsTextures[] = {"\acme_bloodcooler\data\bloodcooler_camo_co.paa"};
    };
    class ACME_BloodCooler_CSWB2U: ACE_ItemCore {
        model = "\acme_bloodcooler\bloodcooler2u_closed.p3d";
        picture = "\acme_bloodcooler\data\ui\icon_bloodcooler2u_ca.paa";
        hiddenSelections[] = {"camo"};
        hiddenSelectionsTextures[] = {"\acme_bloodcooler\data\bloodcooler_camo_co.paa"};
    };
    class ACME_BloodCooler_CSWB4U: ACE_ItemCore {
        model = "\acme_bloodcooler\bloodcooler4u_closed.p3d";
        picture = "\acme_bloodcooler\data\ui\icon_bloodcooler4u_ca.paa";
        hiddenSelections[] = {"camo"};
        hiddenSelectionsTextures[] = {"\acme_bloodcooler\data\bloodcooler_camo_co.paa"};
    };
};
class CfgMagazines {
    class ACME_PreparedIVSet;
    class ACME_CoolerCarrier_CSWB1U: ACME_PreparedIVSet {
        model = "\acme_bloodcooler\bloodcooler1u_closed.p3d";
        picture = "\acme_bloodcooler\data\ui\icon_bloodcooler1u_ca.paa";
    };
    class ACME_CoolerCarrier_CSWB2U: ACME_CoolerCarrier_CSWB1U {
        model = "\acme_bloodcooler\bloodcooler2u_closed.p3d";
        picture = "\acme_bloodcooler\data\ui\icon_bloodcooler2u_ca.paa";
    };
    class ACME_CoolerCarrier_CSWB4U: ACME_CoolerCarrier_CSWB1U {
        model = "\acme_bloodcooler\bloodcooler4u_closed.p3d";
        picture = "\acme_bloodcooler\data\ui\icon_bloodcooler4u_ca.paa";
    };
};
class CfgVehicles {
    class Items_base_F;
    class ACME_TempusPro_Mount: Items_base_F {
        scope = 2;
        scopeCurator = 2;
        displayName = "Tempus Pro Field Mount";
        destrType = "DestructNo";
        author = "mavis";
        model = "\acme_equipment\models\tempus_pro_mount.p3d";
        editorCategory = "EdCat_Things";
        editorSubcategory = "EdSubcat_Storage";
        ACME_eq_mountKind = "pro";
    };
    class ACME_TempusLS_Mount: ACME_TempusPro_Mount {
        displayName = "Tempus LS Field Mount";
        model = "\acme_equipment\models\tempus_ls_mount.p3d";
        ACME_eq_mountKind = "ls";
    };
    class Box_NATO_Ammo_F;
    class Box_NATO_Wps_F;
    class ACME_BloodCoolerBox_CSWB1U: Box_NATO_Ammo_F {
        model = "\acme_bloodcooler\bloodcooler1u_closed.p3d";
        hiddenSelections[] = {"camo"};
        hiddenSelectionsTextures[] = {"\acme_bloodcooler\data\bloodcooler_camo_co.paa"};
        ACME_preserveModelTextures = 1;
        ACME_modelScale = 1;
    };
    class ACME_BloodCoolerBox_CSWB2U: Box_NATO_Ammo_F {
        model = "\acme_bloodcooler\bloodcooler2u_closed.p3d";
        hiddenSelections[] = {"camo"};
        hiddenSelectionsTextures[] = {"\acme_bloodcooler\data\bloodcooler_camo_co.paa"};
        ACME_preserveModelTextures = 1;
        ACME_modelScale = 1;
    };
    class ACME_BloodCoolerBox_CSWB4U: Box_NATO_Wps_F {
        model = "\acme_bloodcooler\bloodcooler4u_closed.p3d";
        hiddenSelections[] = {"camo"};
        hiddenSelectionsTextures[] = {"\acme_bloodcooler\data\bloodcooler_camo_co.paa"};
        ACME_preserveModelTextures = 1;
        ACME_modelScale = 1;
    };
};
class Extended_PostInit_EventHandlers {
    class acme_equipment {
        init = "ACME_hpmk_blanketClass = 'ACME_HPMK_Open';";
    };
};

class CfgFunctions { class ACME { class equipment { file="\acme_equipment\functions";
class equipmentLayout {};
class equipmentPose {};
class equipmentSeat {};
class equipmentSetup {};
class equipmentInventory {};
class equipmentTransferStamp {};
class equipmentRequest {};
class equipmentPickupReady {};
class equipmentUsbRelease {};
class equipmentAck {};
class equipmentVent {};
class equipmentPreInit {preInit=1;};
class equipmentMountApply {};
class equipmentMountRelease {};
class equipmentMountInit {};
class equipmentMountRequest {};
class equipmentMountMenu {};
class equipmentUsbMenu {};
class equipmentLinkRequest {};
class equipmentMonitorTick {};
class equipmentCableAnchor {};
class equipmentCableSpecs {};
class equipmentCablePose {};
class equipmentCableVisualTick {};
class equipmentWorldSchema {};
class equipmentWorldSnapshot {};
class equipmentWorldCaptureValid {};
class equipmentWorldRestore {};
class equipmentTick {};
class equipmentAvailable {};
class equipmentCoolerLease {};
class equipmentCoolerOpen {};
class equipmentCoolerClose {};
class equipmentCoolerTrack {};
class equipmentCoolerVisualTick {};
class equipmentCoolerMenu {};
class equipmentSensorMenu {};
class equipmentCoolerLoad {};
class equipmentVentScreen {};
class equipmentLsConnections {};
class equipmentInit {postInit=1;};
}; }; };
class CfgRemoteExec { class Functions {
class ACME_fnc_equipmentMountRequest {allowedTargets=2;};
class ACME_fnc_equipmentLinkRequest {allowedTargets=2;};
class ACME_fnc_equipmentCoolerLease {allowedTargets=2;};
class ACME_fnc_equipmentCoolerLoad {allowedTargets=2;};
class ACME_fnc_equipmentRequest {allowedTargets=2;};
class ACME_fnc_equipmentAck {allowedTargets=2;};
class ACME_fnc_equipmentInventory {allowedTargets=0;};
};};

class Extended_InitPost_EventHandlers {
 class ACME_TempusPro_Mount {class acme_equipment {init="[_this select 0] call ACME_fnc_equipmentMountInit";};};
 class ACME_TempusLS_Mount {class acme_equipment {init="[_this select 0] call ACME_fnc_equipmentMountInit";};};
 class ACME_BloodCoolerBox_CSWB1U {class acme_equipment {init="[_this select 0] call ACME_fnc_equipmentCoolerTrack";};};
 class ACME_BloodCoolerBox_CSWB2U {class acme_equipment {init="[_this select 0] call ACME_fnc_equipmentCoolerTrack";};};
 class ACME_BloodCoolerBox_CSWB4U {class acme_equipment {init="[_this select 0] call ACME_fnc_equipmentCoolerTrack";};};
};
