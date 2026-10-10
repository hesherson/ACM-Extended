// These controls belong only to the transfusion menu. The roller clamp uses its existing classes unchanged.
class ACME_TransfusionActionButton: RscButton {
    text = "";
    action = "";
    colorText[] = {0.94,0.91,0.82,1};
    colorDisabled[] = {0.73,0.76,0.81,0.35};
    colorBackground[] = {0.043,0.075,0.153,1};
    colorBackgroundDisabled[] = {0.043,0.075,0.153,0.50};
    colorBackgroundActive[] = {0.188,0.255,0.353,1};
    colorFocused[] = {0.188,0.255,0.353,1};
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
    colorText[] = {0.73,0.76,0.81,1};
    colorBackground[] = {0,0,0,0};
    font = "RobotoCondensed";
    sizeEx = "safeZoneH * 0.017";
    shadow = 0;
    x = "safeZoneX - 1";
    y = "safeZoneY - 1";
    w = "safeZoneW / 8";
    h = "safeZoneH * 0.027";
};
