#include "..\main\script_build.hpp"
// Editable config recovered from the supplied PBO.
class CfgPatches {
    class acme_atak {
        ACME_BUILD_CONFIG("acme_atak");
        name = "ACME ATAK Enhancement";
        author = "ACME";
        units[] = {};
        weapons[] = {};
        requiredVersion = 2.20;
        requiredAddons[] = {"cba_main", "cba_xeh", "ace_common", "ace_medical_treatment", "cTab", "ctab_core", "BCE_Core", "BCE_cTab_ATAK", "BCE_cTab_UI", "ACM_Extended"};
        skipWhenMissingDependencies = 1;
        version = "1.0.0";
        versionStr = "1.0.0";
        versionAr[] = {1, 0, 0};
    };
};
class CfgFunctions {
    class ACME {
        class batdok {
            file = "\acme_atak\functions";
            class batdokAction {

            };
            class batdokCallsign {

            };
            class batdokClassify {

            };
            class batdokExport {

            };
            class batdokInit {
                postInit = 1;
            };
            class batdokNow {

            };
            class batdokOp {

            };
            class batdokPart {

            };
            class batdokPeers {

            };
            class batdokRecv {

            };
            class batdokSense {

            };
            class batdokState {

            };
            class batdokText {

            };
            class batdokTick {

            };
            class batdokToast {

            };
            class batdokTreat {

            };
            class batdokTriage {

            };
            class batdokWounds {

            };
        };
        class atak {
            file = "\acme_atak\functions";
            class atakHtml {

            };
            class atakLoop {

            };
            class atakMessage {

            };
            class atakOpened {

            };
            class atakPlace {

            };
        };
    };
};
class CfgRemoteExec {
    class Functions {
        class ACME_fnc_batdokOp {
            allowedTargets = 2;
        };
        class ACME_fnc_batdokRecv {
            allowedTargets = 1;
        };
        class ACME_fnc_batdokToast {
            allowedTargets = 1;
        };
    };
};
class RscWebBrowser;
class ACME_ATAK_Web : RscWebBrowser {
    idc = -1;
    allowExternalURL = 0;
    url = "";
    x = 0;
    y = 0;
    w = 0.1;
    h = 0.1;
    colorBackground[] = {0.012, 0.027, 0.051, 1};
};
class ATAK_AppMenu_Base;
class ACME_ATAK_BATDOK_Page : ATAK_AppMenu_Base {
    class controls {

    };
};
class BCE_ATAK_Tool_ICON;
class ATAK_APPs {
    class ACME_BATDOK : BCE_ATAK_Tool_ICON {
        class Menu_Property {
            ORDER = 7.5;
            PAGE_CTRL = "ACME_ATAK_BATDOK_Page";
            Opened = "ACME_fnc_atakOpened";
        };
        onButtonClick = "[_this # 0] call BCE_fnc_ATAK_ChangeTool;";
        text = "<t size='0.8'>BATDOK</t>";
        textureNoShortcut = "\acme_atak\data\batdok_ca.paa";
    };
};
class RscTitles {
    class BCE_ATAK_Tool_ICON;
    class ATAK_AppMenu_Base;
    class ACME_ATAK_BATDOK_Page : ATAK_AppMenu_Base {
        class controls {

        };
    };
    class ATAK_APPs {
        class ACME_BATDOK : BCE_ATAK_Tool_ICON {
            class Menu_Property {
                ORDER = 7.5;
                PAGE_CTRL = "ACME_ATAK_BATDOK_Page";
                Opened = "ACME_fnc_atakOpened";
            };
            onButtonClick = "[_this # 0] call BCE_fnc_ATAK_ChangeTool;";
            text = "<t size='0.8'>BATDOK</t>";
            textureNoShortcut = "\acme_atak\data\batdok_ca.paa";
        };
    };
};
