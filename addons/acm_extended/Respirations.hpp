// B213: an observation watch has its own monotonic seconds, independent of mission daytime.
class ACME_Respiration_Display {
    idd = 71590;
    movingEnable = 0;
    enableSimulation = 1;
    duration = 1e11;
    fadeIn = 0;
    fadeOut = 0;
    onLoad = "uiNamespace setVariable ['ACME_RespirationDisplay', (_this select 0)];";
    onUnload = "uiNamespace setVariable ['ACME_RespirationDisplay', displayNull];";
    class Controls {
        class Title: RscText {
            idc = 71591;
            style = 2;
            text = "Measure Respirations";
            x = "safezoneX";
            y = "safezoneY + safezoneH * 0.015";
            w = "safezoneW";
            h = "safezoneH * 0.06";
            sizeEx = "safezoneH * 0.03";
            shadow = 2;
        };
        class Patient: Title {
            idc = 71592;
            text = "";
            y = "safezoneY + safezoneH * 0.07";
            sizeEx = "safezoneH * 0.023";
        };
        class Circle: RscPicture {
            idc = 71593;
            text = "\acm_extended\ui\dot_grad_ca.paa";
            colorText[] = {0.30, 0.55, 1.0, 0.0};
            x = "safezoneX + safezoneW/2 - 0.025";
            y = "safezoneY + safezoneH/2 - 0.025";
            w = 0.05;
            h = 0.05;
        };
        class WatchBackground: RscText {
            idc = 71597;
            text = "";
            colorBackground[] = {0.015,0.02,0.03,0.82};
            x = "safezoneX + safezoneW * 0.435";
            y = "safezoneY + safezoneH * 0.68";
            w = "safezoneW * 0.13";
            h = "safezoneH * 0.14";
        };
        class WatchLabel: Title {
            idc = -1;
            text = "OBSERVING...";
            y = "safezoneY + safezoneH * 0.685";
            h = "safezoneH * 0.035";
            sizeEx = "safezoneH * 0.019";
        };
        class WatchSeconds: Title {
            idc = 71594;
            text = "Preparing...";
            y = "safezoneY + safezoneH * 0.72";
            h = "safezoneH * 0.055";
            sizeEx = "safezoneH * 0.036";
        };
        class Instructions: Title {
            idc = 71595;
            text = "Esc to cancel";
            y = "safezoneY + safezoneH * 0.78";
            h = "safezoneH * 0.03";
            sizeEx = "safezoneH * 0.018";
        };
    };
};
