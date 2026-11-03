#include "..\main\script_build.hpp"
// Editable config recovered from the supplied PBO.
class CfgPatches {
    class acme_tempusls {
        ACME_BUILD_CONFIG("acme_tempusls");
        name = "ACME Tempus LS";
        author = "ACME";
        units[] = {"ACME_TempusLS"};
        weapons[] = {"ACME_TempusLS_Item"};
        requiredVersion = 2.20;
        requiredAddons[] = {"A3_Structures_F", "A3_Ui_F", "A3_Weapons_F", "cba_main", "cba_common", "cba_xeh", "ace_interact_menu", "ace_common", "ace_medical_status", "ACM_Extended", "acme_tempus"};
        version = "1.0.0";
        versionStr = "1.0.0";
        versionAr[] = {1, 0, 0};
    };
};
class CfgFunctions {
    class ACME {
        class tempusls {
            file = "\acme_tempusls\functions";
            class tempusLsCanUse {

            };
            class tempusLsConnect {

            };
            class tempusLsDischarge {

            };
            class tempusLsFeed {

            };
            class tempusLsFront {

            };
            class tempusLsHtml {

            };
            class tempusLsInit {
                postInit = 1;
            };
            class tempusLsKey {

            };
            class tempusLsLights {

            };
            class tempusLsMetro {

            };
            class tempusLsMirror {

            };
            class tempusLsMove {

            };
            class tempusLsPacingRate {};
            class tempusLsPace {

            };
            class tempusLsPair {

            };
            class tempusLsPick {

            };
            class tempusLsPlace {

            };
            class tempusLsPower {

            };
            class tempusLsPush {

            };
            class tempusLsScreen {

            };
            class tempusLsShock {

            };
            class tempusLsSound {

            };
            class tempusLsSpot {

            };
            class tempusLsUiMessage {

            };
            class tempusLsUiOnLoad {

            };
            class tempusLsUiOnUnload {

            };
            class tempusLsUse {

            };
            class tempusLsView {

            };
            class tempusLsVitals {

            };
        };
    };
};
class CfgWeapons {
    class CBA_MiscItem;
    class CBA_MiscItem_ItemInfo;
    class ACME_TempusLS_Item : CBA_MiscItem {
        scope = 2;
        scopeArsenal = 2;
        scopeCurator = 2;
        author = "ACME";
        displayName = "Tempus LS Defibrillator";
        descriptionShort = "Defibrillator, pacer and ECG monitor";
        picture = "\acme_tempusls\data\tempusls_icon_ca.paa";
        model = "\acme_tempusls\data\tempus_ls.p3d";
        class ItemInfo : CBA_MiscItem_ItemInfo {
            mass = 44;
        };
    };
};
class CfgRemoteExec {
    class Functions {
        class ACME_fnc_tempusLsFeed {
            allowedTargets = 0;
        };
        class ACME_fnc_tempusLsShock {
            allowedTargets = 0;
        };
        class ACME_fnc_tempusLsPace {
            allowedTargets = 0;
        };
    };
};
class CfgVehicles {
    class Items_base_F;
    class ACME_TempusLS : Items_base_F {
        scope = 2;
        scopeCurator = 2;
        author = "ACME";
        displayName = "Tempus LS Defibrillator";
        model = "\acme_tempusls\data\tempus_ls.p3d";
        icon = "iconObject_1x1";
        vehicleClass = "Small_items";
        editorCategory = "EdCat_Things";
        editorSubcategory = "EdSubcat_Electronics";
        destrType = "DestructNo";
        hiddenSelections[] = {"screen", "glow", "led", "shock"};
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
class ACME_TempusLS_Web : RscWebBrowser {
    idc = -1;
    allowExternalURL = 0;
    url = "";
    x = 0;
    y = 0;
    w = 1;
    h = 1;
    colorBackground[] = {0, 0, 0, 1};
};
class ACME_TempusLS_Key : RscButton {
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
    colorBackgroundActive[] = {1, 1, 1, 0.14};
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
class ACME_TempusLS_dlg {
    idd = 73961;
    movingEnable = 0;
    enableSimulation = 1;
    onLoad = "[_this select 0] call ACME_fnc_tempusLsUiOnLoad";
    onUnload = "[] call ACME_fnc_tempusLsUiOnUnload";
    class controls {
        class web : ACME_TempusLS_Web {
            idc = 100;
            x = "safezoneX - 2";
        };
    };
};
