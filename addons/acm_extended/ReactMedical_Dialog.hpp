class ACME_ReactMedicalDialog {
    idd = 89300;
    movingEnable = 0;
    enableSimulation = 1;
    onUnload = "_this call ACME_fnc_reactMedicalClose";
    onKeyDown = "if ((_this select 1) == 1) then {(_this select 0) closeDisplay 0;true} else {false}";
    class controlsBackground {
        class Background: RscText {
            idc = -1;
            x = "safeZoneX + safeZoneW * 0.06"; y = "safeZoneY + safeZoneH * 0.06";
            w = "safeZoneW * 0.88"; h = "safeZoneH * 0.88";
            colorBackground[] = {0.035,0.055,0.065,1};
        };
    };
    class controls {
        class Browser: RscText {
            type = 106;
            idc = 89301;
            style = 0;
            x = "safeZoneX + safeZoneW * 0.06"; y = "safeZoneY + safeZoneH * 0.12";
            w = "safeZoneW * 0.88"; h = "safeZoneH * 0.82";
            allowExternalURL = 0;
            url = "";
            onPageLoaded = "_this call ACME_fnc_reactMedicalPage";
            onJSDialog = "_this call ACME_fnc_reactMedicalMessage";
        };
        class Title: RscText {
            idc = -1;
            text = "FLUID MANAGEMENT";
            x = "safeZoneX + safeZoneW * 0.075"; y = "safeZoneY + safeZoneH * 0.07";
            w = "safeZoneW * 0.5"; h = "safeZoneH * 0.04";
            colorText[] = {0.87,0.94,0.93,1};
        };
        class NativeControls: RscButton {
            idc = 89302;
            text = "Native controls";
            x = "safeZoneX + safeZoneW * 0.75"; y = "safeZoneY + safeZoneH * 0.07";
            w = "safeZoneW * 0.13"; h = "safeZoneH * 0.04";
            onButtonClick = "[ctrlParent (_this select 0)] call ACME_fnc_reactMedicalFallback";
        };
        class Close: NativeControls {
            idc = 89303;
            text = "X";
            x = "safeZoneX + safeZoneW * 0.89";
            w = "safeZoneW * 0.03";
            onButtonClick = "(ctrlParent (_this select 0)) closeDisplay 0";
        };
    };
};
