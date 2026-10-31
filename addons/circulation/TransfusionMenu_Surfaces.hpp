// B276: fixed, noninteractive background decorations. Native list/button controls
// remain the sole input/selection owners. No surfaces are created during refresh.
class TransfusionSurface: RscPicture {
    idc = -1;
    text = QPATHTOF(ui\transfusionmenu\surfaces\button_ca.paa);
    x = QUOTE(ACM_UI_CANVAS_X - 1);
    y = QUOTE(safeZoneY - 1);
    w = 0;
    h = 0;
    enable = 0;
    colorText[] = {1,1,1,1};
};

#define TX_BUTTON_SURFACE(name,sidc) class name: TransfusionSurface {idc = sidc;}
TX_BUTTON_SURFACE(StopSurface,86300);
TX_BUTTON_SURFACE(MoveSurface,86301);
TX_BUTTON_SURFACE(PullSurface,86302);
TX_BUTTON_SURFACE(InfuseSurface,86303);
TX_BUTTON_SURFACE(RaiseSurface,86304);
TX_BUTTON_SURFACE(PressureSurface,86305);
TX_BUTTON_SURFACE(DiscardYSurface,86306);
TX_BUTTON_SURFACE(PrepInfusionSurface,86307);
TX_BUTTON_SURFACE(GiveInfusionSurface,86308);
TX_BUTTON_SURFACE(AdjustInfusionSurface,86309);
TX_BUTTON_SURFACE(MoveInfusionSurface,86310);
TX_BUTTON_SURFACE(RemoveInfusionSurface,86311);
TX_BUTTON_SURFACE(PressureInfusionSurface,86312);
TX_BUTTON_SURFACE(SpikeSurface,86313);
TX_BUTTON_SURFACE(YSurface,86314);
TX_BUTTON_SURFACE(ServiceSurface,86315);
TX_BUTTON_SURFACE(PreparedToggleSurface,86316);
TX_BUTTON_SURFACE(BagActionsSurface,86317);
TX_BUTTON_SURFACE(InfusionActionsSurface,86318);
TX_BUTTON_SURFACE(PiggybackSurface,86319);
TX_BUTTON_SURFACE(WarmerSurface,86320);
TX_BUTTON_SURFACE(WarmerYesSurface,86321);
TX_BUTTON_SURFACE(WarmerNoSurface,86322);
TX_BUTTON_SURFACE(SpikeDropdownSurface,86323);
#undef TX_BUTTON_SURFACE

class TransfusionRowSurface: TransfusionSurface {
    text = QPATHTOF(ui\transfusionmenu\surfaces\row_ca.paa);
};
class TransfusionRowCaption: RscText {
    idc = -1;
    x = QUOTE(ACM_UI_CANVAS_X - 1);
    y = QUOTE(safeZoneY - 1);
    w = 0;
    h = 0;
    enable = 0;
    font = "RobotoCondensed";
    sizeEx = QUOTE(safeZoneH * 0.013);
    colorText[] = {0.65,0.65,0.65,1};
    colorBackground[] = {0,0,0,0};
    shadow = 0;
    text = "";
};
class TransfusionRowTrack: TransfusionRowCaption {
    colorBackground[] = {0.26,0.26,0.26,1};
};
class TransfusionRowFill: TransfusionRowTrack {
    colorBackground[] = {0.76,0.76,0.76,1};
};

#define TX_ROW_SURFACE(name,sidc) \
    class name: TransfusionRowSurface {idc = sidc;}; \
    class name##_Caption: TransfusionRowCaption {idc = sidc + 1;}; \
    class name##_Track: TransfusionRowTrack {idc = sidc + 2;}; \
    class name##_Fill: TransfusionRowFill {idc = sidc + 3;}
TX_ROW_SURFACE(FluidCard0,86400);
TX_ROW_SURFACE(FluidCard1,86404);
TX_ROW_SURFACE(FluidCard2,86408);
TX_ROW_SURFACE(FluidCard3,86412);
TX_ROW_SURFACE(InfusionCard0,86420);
TX_ROW_SURFACE(InfusionCard1,86424);
TX_ROW_SURFACE(InfusionCard2,86428);
TX_ROW_SURFACE(InfusionCard3,86432);
TX_ROW_SURFACE(StockCard0,86440);
TX_ROW_SURFACE(StockCard1,86444);
TX_ROW_SURFACE(StockCard2,86448);
TX_ROW_SURFACE(StockCard3,86452);
TX_ROW_SURFACE(SetCard0,86460);
TX_ROW_SURFACE(SetCard1,86464);
TX_ROW_SURFACE(SetCard2,86468);
TX_ROW_SURFACE(SetCard3,86472);
TX_ROW_SURFACE(PreparedInfusionCard0,86480);
TX_ROW_SURFACE(PreparedInfusionCard1,86484);
TX_ROW_SURFACE(PreparedInfusionCard2,86488);
TX_ROW_SURFACE(PreparedInfusionCard3,86492);
#undef TX_ROW_SURFACE

class FluidEmptySurface: TransfusionRowSurface {idc = 86370;};
class InfusionEmptySurface: TransfusionRowSurface {idc = 86371;};
class PreparedEmptySurface: TransfusionRowSurface {idc = 86372;};
class InlineDetailsSurface: TransfusionSurface {
    idc = 86373;
    text = QPATHTOF(ui\transfusionmenu\surfaces\list_ca.paa);
};
class HeaderDivider: TransfusionRowTrack {
    idc = -1;
    x = QUOTE(ACM_TRANSFUSION_WINDOW_X + ACM_UI_CANVAS_W * 0.013);
    y = QUOTE(safeZoneY + safeZoneH * 0.146);
    w = QUOTE(ACM_TRANSFUSION_WINDOW_W - ACM_UI_CANVAS_W * 0.026);
    h = QUOTE(pixelH);
    colorBackground[] = {0.20,0.20,0.20,1};
};
