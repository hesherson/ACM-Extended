// These controls belong only to the transfusion menu. The roller clamp uses its existing classes unchanged.
class ACME_TransfusionActionButton: RscButton {
    text = "";
    action = "";
    colorText[] = {1,1,1,1};
    colorDisabled[] = {0.76,0.76,0.76,0.35};
    colorBackground[] = {0,0,0,1};
    colorBackgroundDisabled[] = {0,0,0,0.50};
    colorBackgroundActive[] = {0.20,0.20,0.20,1};
    colorFocused[] = {0.20,0.20,0.20,1};
    colorBorder[] = {0,0,0,0};
    style = 2;
    shadow = 0;
    font = "RobotoCondensed";
    sizeEx = "safeZoneH * 0.020";
    x = "safeZoneX - 1";
    y = "safeZoneY - 1";
    w = "safeZoneW / 8";
    h = "safeZoneH * 0.033";
};

class ACME_TransfusionCaption: RscText {
    text = "";
    colorText[] = {0.76,0.76,0.76,1};
    colorBackground[] = {0,0,0,0};
    font = "RobotoCondensed";
    sizeEx = "safeZoneH * 0.017";
    shadow = 0;
    x = "safeZoneX - 1";
    y = "safeZoneY - 1";
    w = "safeZoneW / 8";
    h = "safeZoneH * 0.027";
};

// Selected-line information stays visible under the shared body map. Long bag names
// and multiple medication/cuff rows scroll inside this area instead of opening a modal.
class ACME_TransfusionInlineDetails: RscControlsGroupNoHScrollbars {
    x = "safeZoneX - 1";
    y = "safeZoneY - 1";
    w = "(safeZoneW min (safeZoneH * 1.7777778)) * 0.290";
    h = "safeZoneH * 0.090";
    class Controls {
        class Contents: RscStructuredText {
            idc = 86192;
            x = 0;
            y = 0;
            w = "(safeZoneW min (safeZoneH * 1.7777778)) * 0.280";
            h = "safeZoneH * 0.090";
            size = "safeZoneH * 0.016";
            colorBackground[] = {0,0,0,0};
            class Attributes {font = "RobotoCondensed";color = "#cccccc";align = "left";shadow = 0;};
        };
    };
};
