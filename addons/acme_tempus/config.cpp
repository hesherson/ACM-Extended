#include "..\main\script_build.hpp"
// Editable config recovered from the supplied PBO.
class CfgPatches {
    class acme_tempus {
        ACME_BUILD_CONFIG("acme_tempus");
        name = "ACME Tempus Pro";
        author = "ACME";
        units[] = {"ACME_TempusPro"};
        weapons[] = {"ACME_TempusPro_Item"};
        requiredVersion = 2.20;
        requiredAddons[] = {"A3_Structures_F", "A3_Ui_F", "A3_Weapons_F", "cba_main", "cba_common", "cba_xeh", "ace_interact_menu", "ace_common", "ace_medical_status", "ACM_Extended"};
        version = "1.2.1";
        versionStr = "1.2.1";
        versionAr[] = {1, 2, 1};
    };
};
class CfgFunctions {
    class ACME {
        class tempus {
            file = "\acme_tempus\functions";
            class tempusCanUse {

            };
            class tempusConnect {

            };
            class tempusFeed {

            };
            class tempusFront {

            };
            class tempusHtml {

            };
            class tempusInit {
                postInit = 1;
            };
            class tempusMirror {

            };
            class tempusMove {

            };
            class tempusPick {

            };
            class tempusPlace {

            };
            class tempusPowerKey {};
            class tempusPower {

            };
            class tempusPush {

            };
            class tempusScreen {

            };
            class tempusSpot {

            };
            class tempusUiMessage {

            };
            class tempusUiOnLoad {

            };
            class tempusUiOnUnload {

            };
            class tempusUse {

            };
            class tempusView {

            };
            class tempusWaveforms {};
            class tempusVitals {

            };
        };
    };
};
class CfgWeapons {
    class ACE_ItemCore;
    class CBA_MiscItem_ItemInfo;
    class ACME_TempusPro_Item : ACE_ItemCore {
        scope = 2;
        scopeArsenal = 2;
        scopeCurator = 2;
        author = "ACME";
        displayName = "Tempus Pro Monitor";
        ACE_isMedicalItem = 1;
        descriptionShort = "Patient monitor";
        picture = "\acme_tempus\data\tempus_icon_ca.paa";
        model = "\acme_tempus\data\tempus_pro.p3d";
        class ItemInfo : CBA_MiscItem_ItemInfo {
            mass = 64;
        };
    };
};
class CfgRemoteExec {
    class Functions {
        class ACME_fnc_tempusFeed {
            allowedTargets = 0;
        };
    };
};
class CfgVehicles {
    class Items_base_F;
    class ACME_TempusPro : Items_base_F {
        scope = 2;
        scopeCurator = 2;
        author = "ACME";
        displayName = "Tempus Pro Monitor";
        model = "\acme_tempus\data\tempus_pro.p3d";
        icon = "iconObject_1x1";
        vehicleClass = "Small_items";
        editorCategory = "EdCat_Things";
        editorSubcategory = "EdSubcat_Electronics";
        destrType = "DestructNo";
        hiddenSelections[] = {"screen"};
        hiddenSelectionsTextures[] = {"#(argb,8,8,3)color(0,0,0,1,co)"};
        ace_dragging_canDrag = 1;
        ace_dragging_dragPosition[] = {0, 1.2, 0};
        ace_dragging_canCarry = 1;
        ace_dragging_carryPosition[] = {0, 0.9, 1};
        ace_dragging_carryDirection = 0;
    };
};
class RscButton;
class RscWebBrowser;
class ACME_Tempus_Web : RscWebBrowser {
    idc = -1;
    allowExternalURL = 0;
    url = "";
    x = 0;
    y = 0;
    w = 1;
    h = 1;
    colorBackground[] = {0, 0, 0, 1};
};
class ACME_Tempus_Key : RscButton {
    idc = -1;
    text = "";
    x = 0;
    y = 0;
    w = 0.05;
    h = 0.05;
    colorText[] = {0, 0, 0, 0};
    colorDisabled[] = {0, 0, 0, 0};
    colorBackground[] = {0, 0, 0, 0};
    colorBackgroundDisabled[] = {0, 0, 0, 0};
    colorBackgroundActive[] = {0, 0, 0, 0};
    colorBackgroundFocused[] = {0, 0, 0, 0};
    period = 0;
    periodFocus = 0;
    periodOver = 0;
    colorFocused[] = {0, 0, 0, 0};
    colorShadow[] = {0, 0, 0, 0};
    colorBorder[] = {0, 0, 0, 0};
    offsetX = 0;
    offsetY = 0;
    offsetPressedX = 0;
    offsetPressedY = 0;
    borderSize = 0;
    soundClick[] = {"\A3\ui_f\data\sound\RscButton\soundClick", 0.09, 1};
};
class ACME_Tempus_dlg {
    idd = 73960;
    movingEnable = 0;
    enableSimulation = 1;
    onLoad = "[_this select 0] call ACME_fnc_tempusUiOnLoad";
    onUnload = "[] call ACME_fnc_tempusUiOnUnload";
    class controls {
        class web : ACME_Tempus_Web {
            idc = 100;
            x = "safezoneX - 2";
        };
    };
};
