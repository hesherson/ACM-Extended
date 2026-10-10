// Transfusion-only details. The existing roller-clamp dialog and styles are independent.
class ACME_TransfusionDetails_Dialog {
    idd = 86190;
    movingEnable = 0;
    onUnload = "uiNamespace setVariable ['ACME_TransfusionDetailsContext',nil]";
    class ControlsBackground {
        class Background: RscText {
            idc = -1;
            x = "safeZoneX + safeZoneW / 2 - safeZoneH * 0.25";
            y = "safeZoneY + safeZoneH * 0.25";
            w = "safeZoneH * 0.50";
            h = "safeZoneH * 0.50";
            colorBackground[] = {0.063,0.110,0.212,1};
        };
    };
    class Controls {
        class Title: ACME_TransfusionCaption {
            idc = 86191;
            text = "Line Details";
            x = "safeZoneX + safeZoneW / 2 - safeZoneH * 0.225";
            y = "safeZoneY + safeZoneH * 0.267";
            w = "safeZoneH * 0.45";
            h = "safeZoneH * 0.07";
        };
        class Contents: RscStructuredText {
            idc = 86192;
            x = "safeZoneX + safeZoneW / 2 - safeZoneH * 0.225";
            y = "safeZoneY + safeZoneH * 0.35";
            w = "safeZoneH * 0.45";
            h = "safeZoneH * 0.31";
            size = "safeZoneH * 0.020";
            class Attributes {font = "RobotoCondensed";color = "#efe8d1";align = "left";shadow = 0;};
        };
        class Done: ACME_TransfusionActionButton {
            idc = 86193;
            text = "Done";
            x = "safeZoneX + safeZoneW / 2 + safeZoneH * 0.075";
            y = "safeZoneY + safeZoneH * 0.69";
            w = "safeZoneH * 0.15";
            h = "safeZoneH * 0.035";
            action = "closeDialog 0";
        };
    };
};
