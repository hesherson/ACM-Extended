class RscControlsGroupNoScrollbars;
// These controls belong only to the transfusion menu. The roller clamp uses its existing classes unchanged.
class ACME_TransfusionActionButton: RscButton {
    text = "";
    action = "";
    colorText[] = {1,1,1,1};
    colorDisabled[] = {0.76,0.76,0.76,0.35};
    colorBackground[] = {0,0,0,0};
    colorBackgroundDisabled[] = {0,0,0,0};
    colorBackgroundActive[] = {0,0,0,0};
    colorFocused[] = {0,0,0,0};
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

class ACME_TransfusionTabButton: ACME_TransfusionActionButton {
    sizeEx = "safeZoneH * 0.017";
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

// Selected-line information stays visible beneath the Infusions section. Long bag names
// and multiple medication/cuff rows scroll inside this area instead of opening a modal.
class ACME_TransfusionInlineDetails: RscControlsGroupNoHScrollbars {
    x = "safeZoneX - 1";
    y = "safeZoneY - 1";
    w = "(safeZoneW min (safeZoneH * 1.7777778)) * 0.212";
    h = "safeZoneH * 0.068";
    class Controls {
        class Contents: RscStructuredText {
            idc = 86192;
            x = 0;
            y = 0;
            w = "(safeZoneW min (safeZoneH * 1.7777778)) * 0.202";
            h = "safeZoneH * 0.068";
            size = "safeZoneH * 0.016";
            colorBackground[] = {0,0,0,0};
            class Attributes {font = "RobotoCondensed";color = "#cccccc";align = "left";shadow = 0;};
        };
    };
};

// B275: quiet patient/access captions; exact source icon artwork is displayed separately.
class ACME_TransfusionCenteredCaption: ACME_TransfusionCaption {
    style = 2;
    sizeEx = "safeZoneH * 0.017";
};

class ACME_TransfusionAccessCaption: ACME_TransfusionCenteredCaption {
    style = 0;
};

// B276: sliced native textures preserve circular corners instead of stretching a bitmap.
#define ACME_TX_SLICE(Name, Id) class Name: RscPicture { idc = Id; x = 0; y = 0; w = 0; h = 0; text = ""; colorText[] = {1,1,1,1}; };
#define ACME_TX_SLICES ACME_TX_SLICE(TL,0) ACME_TX_SLICE(T,1) ACME_TX_SLICE(TR,2) ACME_TX_SLICE(L,3) ACME_TX_SLICE(C,4) ACME_TX_SLICE(R,5) ACME_TX_SLICE(BL,6) ACME_TX_SLICE(B,7) ACME_TX_SLICE(BR,8)
class ACME_TransfusionRoundedFrame: RscControlsGroupNoScrollbars {
    x = "safeZoneX - 1"; y = "safeZoneY - 1"; w = 0; h = 0;
    class Controls { ACME_TX_SLICES };
};
class ACME_TransfusionCard: ACME_TransfusionRoundedFrame {
    class Controls {
        ACME_TX_SLICES
        class Name: ACME_TransfusionCaption { idc = 10; style = 0; sizeEx = "safeZoneH * 0.018"; colorText[] = {0.94,0.94,0.94,1}; };
        class Detail: Name { idc = 11; sizeEx = "safeZoneH * 0.014"; colorText[] = {0.66,0.66,0.66,1}; };
        class Status: Detail { idc = 12; style = 0; sizeEx = "safeZoneH * 0.0125"; };
        class Thermal: Detail { idc = 13; style = 1; sizeEx = "safeZoneH * 0.0125"; };
        class BagIcon: RscPictureKeepAspect { idc = 14; x = 0; y = 0; w = 0; h = 0; text = ""; };
        class VialIcon: BagIcon { idc = 15; };
        class Track: RscText { idc = 16; x = 0; y = 0; w = 0; h = 0; colorBackground[] = {0.25,0.25,0.25,1}; };
        class Progress: Track { idc = 17; colorBackground[] = {0.76,0.76,0.76,1}; };
#define ACME_TX_MARK(Index, TickID, LabelID) class Tick_##Index: Track { idc = TickID; colorBackground[] = {0.65,0.65,0.65,1}; }; class Mark_##Index: Detail { idc = LabelID; style = 2; sizeEx = "safeZoneH * 0.010"; };
        ACME_TX_MARK(0,18,29) ACME_TX_MARK(1,19,30) ACME_TX_MARK(2,20,31)
        ACME_TX_MARK(3,21,32) ACME_TX_MARK(4,22,33) ACME_TX_MARK(5,23,34)
        ACME_TX_MARK(6,24,35) ACME_TX_MARK(7,25,36) ACME_TX_MARK(8,26,37)
        ACME_TX_MARK(9,27,38) ACME_TX_MARK(10,28,39)
#undef ACME_TX_MARK
        // Last child is the native button face: decorative captions/art cannot
        // sit above the hit target and swallow native mouse clicks or sounds.
        class Hit: ACME_TransfusionActionButton { idc = 9; x = 0; y = 0; w = 0; h = 0; sizeEx = 0; };
    };
};
#undef ACME_TX_SLICES
#undef ACME_TX_SLICE
