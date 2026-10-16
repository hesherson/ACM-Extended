class RscControlsGroupNoScrollbars;
#include "TransfusionMenu_defines.hpp"

class GVAR(TransfusionMenu_Dialog) {
    idd = IDC_TRANSFUSIONMENU;
    movingEnable = 0;
    onLoad = "";
    onUnload = QUOTE(uiNamespace setVariable [ARR_2(QQGVAR(TransfusionMenu_DLG),nil)]);
    onKeyDown = QUOTE([ARR_3('onKeyDown',_this,QQGVAR(display))] call FUNC(TransfusionMenu_onKeyDown));
    objects[] = {};

    class ControlsBackground {
        // B276: this frame is authored first, beneath all native body/device artwork.
        class MenuBackground: RscControlsGroupNoScrollbars {
            idc = 86400;
            x = QUOTE(ACM_TRANSFUSION_WINDOW_X);
            y = QUOTE(safeZoneY + safeZoneH * 0.08);
            w = QUOTE(ACM_TRANSFUSION_WINDOW_W);
            h = QUOTE(safeZoneH * 0.84);
            class Controls {
                class Slice_0: RscPicture { idc = 0; x = QUOTE(0); y = QUOTE(0); w = QUOTE(safeZoneH * 0.012 * pixelW / pixelH); h = QUOTE(safeZoneH * 0.012); text = "\acm_extended\ui\transfusion\window_tl_ca.paa"; };
                class Slice_1: RscPicture { idc = 1; x = QUOTE(safeZoneH * 0.012 * pixelW / pixelH); y = QUOTE(0); w = QUOTE(ACM_TRANSFUSION_WINDOW_W - safeZoneH * 0.024 * pixelW / pixelH); h = QUOTE(safeZoneH * 0.012); text = "\acm_extended\ui\transfusion\window_top_ca.paa"; };
                class Slice_2: RscPicture { idc = 2; x = QUOTE(ACM_TRANSFUSION_WINDOW_W - safeZoneH * 0.012 * pixelW / pixelH); y = QUOTE(0); w = QUOTE(safeZoneH * 0.012 * pixelW / pixelH); h = QUOTE(safeZoneH * 0.012); text = "\acm_extended\ui\transfusion\window_tr_ca.paa"; };
                class Slice_3: RscPicture { idc = 3; x = QUOTE(0); y = QUOTE(safeZoneH * 0.012); w = QUOTE(safeZoneH * 0.012 * pixelW / pixelH); h = QUOTE(safeZoneH * (0.84 - 0.024)); text = "\acm_extended\ui\transfusion\window_left_ca.paa"; };
                class Slice_4: RscPicture { idc = 4; x = QUOTE(safeZoneH * 0.012 * pixelW / pixelH); y = QUOTE(safeZoneH * 0.012); w = QUOTE(ACM_TRANSFUSION_WINDOW_W - safeZoneH * 0.024 * pixelW / pixelH); h = QUOTE(safeZoneH * (0.84 - 0.024)); text = "\acm_extended\ui\transfusion\window_center_ca.paa"; };
                class Slice_5: RscPicture { idc = 5; x = QUOTE(ACM_TRANSFUSION_WINDOW_W - safeZoneH * 0.012 * pixelW / pixelH); y = QUOTE(safeZoneH * 0.012); w = QUOTE(safeZoneH * 0.012 * pixelW / pixelH); h = QUOTE(safeZoneH * (0.84 - 0.024)); text = "\acm_extended\ui\transfusion\window_right_ca.paa"; };
                class Slice_6: RscPicture { idc = 6; x = QUOTE(0); y = QUOTE(safeZoneH * (0.84 - 0.012)); w = QUOTE(safeZoneH * 0.012 * pixelW / pixelH); h = QUOTE(safeZoneH * 0.012); text = "\acm_extended\ui\transfusion\window_bl_ca.paa"; };
                class Slice_7: RscPicture { idc = 7; x = QUOTE(safeZoneH * 0.012 * pixelW / pixelH); y = QUOTE(safeZoneH * (0.84 - 0.012)); w = QUOTE(ACM_TRANSFUSION_WINDOW_W - safeZoneH * 0.024 * pixelW / pixelH); h = QUOTE(safeZoneH * 0.012); text = "\acm_extended\ui\transfusion\window_bottom_ca.paa"; };
                class Slice_8: RscPicture { idc = 8; x = QUOTE(ACM_TRANSFUSION_WINDOW_W - safeZoneH * 0.012 * pixelW / pixelH); y = QUOTE(safeZoneH * (0.84 - 0.012)); w = QUOTE(safeZoneH * 0.012 * pixelW / pixelH); h = QUOTE(safeZoneH * 0.012); text = "\acm_extended\ui\transfusion\window_br_ca.paa"; };
            };
        };
        // Presentation panels stay behind the shared body-map artwork and its device overlays.
        class HeaderBackground: RscText {
            idc = 86091;
            x = QUOTE(ACM_TRANSFUSION_WINDOW_X);
            y = QUOTE(safeZoneY + safeZoneH * 0.08);
            w = QUOTE(ACM_TRANSFUSION_WINDOW_W);
            h = QUOTE(safeZoneH * 0.066);
            colorBackground[] = {0,0,0,0};
        };
        class PatientPanelBackground: HeaderBackground {
            idc = 86180;
            x = QUOTE(ACM_TRANSFUSION_LEFT_X - ACM_UI_CANVAS_W * 0.007);
            y = QUOTE(safeZoneY + safeZoneH * 0.152);
            w = QUOTE(ACM_TRANSFUSION_LEFT_W + ACM_UI_CANVAS_W * 0.014);
            h = QUOTE(safeZoneH * 0.739);
        };
        class MapPanelBackground: PatientPanelBackground {
            idc = 86181;
            x = QUOTE(ACM_UI_CANVAS_X + ACM_UI_CANVAS_W * 0.35);
            w = QUOTE(ACM_UI_CANVAS_W * 0.30);
            colorBackground[] = {0,0,0,0};
        };
        class BodyMapGradient: RscPictureKeepAspect {
            idc = 86215;
            x = QUOTE(ACM_UI_CANVAS_X + (ACM_UI_CANVAS_W / 2) - (ACM_UI_CANVAS_W / 6.8));
            y = QUOTE(safeZoneY + (safeZoneH / 2) - (safeZoneH / 3.5));
            w = QUOTE(ACM_UI_CANVAS_W / 3.4);
            h = QUOTE(safeZoneH / 1.75);
            text = "\acm_extended\ui\transfusion\body_gradient_ca.paa";
        };
        class PreparationPanelBackground: PatientPanelBackground {
            idc = 86182;
            x = QUOTE(ACM_TRANSFUSION_RIGHT_X - ACM_UI_CANVAS_W * 0.007);
            w = QUOTE(ACM_TRANSFUSION_RIGHT_W + ACM_UI_CANVAS_W * 0.014);
        };
        // Local action popovers live in the background layer, below the unchanged native action buttons.
        class BagActionsBackground: PatientPanelBackground {
            idc = 86173;
            x = QUOTE(ACM_UI_CANVAS_X - 1);
            y = QUOTE(safeZoneY + safeZoneH * 0.228);
            w = QUOTE(ACM_UI_CANVAS_W * 0.206);
            h = QUOTE(safeZoneH * 0.234);
            colorBackground[] = {0,0,0,0};
        };
        class InfusionActionsBackground: BagActionsBackground {
            idc = 86174;
            y = QUOTE(safeZoneY + safeZoneH * 0.593);
            h = QUOTE(safeZoneH * 0.142);
        };
        class FluidsTitle: RscText {
            idc = 86160;
            text = "Fluids";
            x = QUOTE(ACM_TRANSFUSION_LEFT_X);
            y = QUOTE(safeZoneY + safeZoneH * 0.151);
            w = QUOTE(ACM_TRANSFUSION_LEFT_W);
            h = QUOTE(safeZoneH * 0.027);
            font = "RobotoCondensed";
            sizeEx = QUOTE(safeZoneH * 0.021);
            colorText[] = ACM_TRANSFUSION_COLOR_TEXT;
            colorBackground[] = {0,0,0,0};
            shadow = 0;
        };
        class InventoryTitle: FluidsTitle {
            idc = 86161;
            text = "Inventory";
            x = QUOTE(ACM_TRANSFUSION_RIGHT_X + ACM_UI_CANVAS_W * 0.008);
            y = QUOTE(safeZoneY + safeZoneH * 0.164);
            w = QUOTE(ACM_TRANSFUSION_RIGHT_W - ACM_UI_CANVAS_W * 0.008);
        };
        class SelectedAccessCaption: FluidsTitle {
            idc = 86162;
            text = "SELECTED ACCESS";
            x = QUOTE(ACM_UI_CANVAS_X + ACM_UI_CANVAS_W * 0.35);
            y = QUOTE(safeZoneY + safeZoneH * 0.157);
            w = QUOTE(ACM_UI_CANVAS_W * 0.30);
            h = QUOTE(safeZoneH * 0.020);
            style = ST_CENTER;
            sizeEx = QUOTE(safeZoneH * 0.015);
            colorText[] = ACM_TRANSFUSION_COLOR_MUTED;
        };
        class SelectedAccessStatus: SelectedAccessCaption {
            idc = 86175;
            text = "";
            y = QUOTE(safeZoneY + safeZoneH * 0.213);
            h = QUOTE(safeZoneH * 0.025);
            sizeEx = QUOTE(safeZoneH * 0.017);
        };
        class FooterHint: FluidsTitle {
            idc = 86163;
            text = "Select access on the body map.   Esc: Back";
            x = QUOTE(ACM_TRANSFUSION_LEFT_X);
            y = QUOTE(safeZoneY + safeZoneH * 0.897);
            w = QUOTE(ACM_TRANSFUSION_WINDOW_W - ACM_UI_CANVAS_W * 0.03);
            h = QUOTE(safeZoneH * 0.021);
            sizeEx = QUOTE(safeZoneH * 0.015);
            colorText[] = ACM_TRANSFUSION_COLOR_MUTED;
        };
        class PatientName: RscText {
            idc = IDC_TRANSFUSIONMENU_PATIENTNAME;
            style = ST_CENTER;
            font = "RobotoCondensed";
            x = QUOTE(ACM_UI_CANVAS_X);
            y = QUOTE(safeZoneY + safeZoneH * 0.095);
            w = QUOTE(ACM_UI_CANVAS_W);
            h = QUOTE(safeZoneH / 20);
            colorText[] = ACM_TRANSFUSION_COLOR_TEXT;
            colorBackground[] = {0,0,0,0};
            text = "";
            lineSpacing = 0;
            sizeEx = QUOTE(GUI_GRID_H * 1.8 * NORMALIZE_SIZEEX);
            shadow = 1;
            colorShadow[] = {0,0,0,0.5};
        };
        class SelectedLimbText: PatientName {
            idc = IDC_TRANSFUSIONMENU_SELECTIONTEXT;
            x = QUOTE(ACM_UI_CANVAS_X + ACM_UI_CANVAS_W * 0.35);
            y = QUOTE(safeZoneY + safeZoneH * 0.177);
            w = QUOTE(ACM_UI_CANVAS_W * 0.30);
            h = QUOTE(safeZoneH * 0.031);
            text = "";
            sizeEx = QUOTE(safeZoneH * 0.021);
        };
        class SelectedInventoryText: SelectedLimbText {
            idc = IDC_TRANSFUSIONMENU_SELECTION_INV_TEXT;
            x = QUOTE(ACM_UI_CANVAS_X + ACM_UI_CANVAS_W * 0.673);
            text = __EVAL(call compile QUOTE(format [ARR_2(C_LLSTRING(Common_InventoryTarget),C_LLSTRING(Common_Self))]));
            y = QUOTE(safeZoneY + safeZoneH * 0.193);
            w = QUOTE(ACM_UI_CANVAS_W * 0.160);
            h = QUOTE(safeZoneH * 0.030);
            sizeEx = QUOTE(safeZoneH * 0.019);
            style = 0;
        };
        class BodyBackground: RscPictureKeepAspect {
            idc = -1;
            x = QUOTE(ACM_UI_CANVAS_X + (ACM_UI_CANVAS_W / 2) - (ACM_UI_CANVAS_W / 6.8));
            y = QUOTE(safeZoneY + (safeZoneH / 2) - (safeZoneH / 3.5));
            w = QUOTE(ACM_UI_CANVAS_W / 3.4);
            h = QUOTE(safeZoneH / 1.75);
            type = 0;
            size = 0;
            text = QPATHTOEF(gui,ui\body_background.paa);
        };
        /*class SelectionRemainingText: PatientName {
            idc = -1;
            style = 0;
            x = QUOTE(ACM_UI_CANVAS_X + (ACM_UI_CANVAS_W / 2) - (ACM_UI_CANVAS_W / 7.7));
            y = QUOTE(safeZoneY + (safeZoneH / 2) - (safeZoneH / 6));
            w = QUOTE(ACM_UI_CANVAS_W / 20);
            h = QUOTE(safeZoneH / 40);
            text = "Remaining: 1000ml";
            sizeEx = QUOTE(GUI_GRID_H * 0.65 * NORMALIZE_SIZEEX);
        };*/
        class BodyBackground_IO_Torso: BodyBackground {
            idc = IDC_TRANSFUSIONMENU_BG_IO_TORSO;
            text = QPATHTOEF(gui,data\body_image\torso_fast_io.paa);
            colorText[] = COLOR_CIRCULATION;
        };
        class BodyBackground_IO_RightArm: BodyBackground_IO_Torso {
            idc = IDC_TRANSFUSIONMENU_BG_IO_RIGHTARM;
            text = QPATHTOEF(gui,data\body_image\rightarm_io.paa);
        };
        class BodyBackground_IO_LeftArm: BodyBackground_IO_Torso {
            idc = IDC_TRANSFUSIONMENU_BG_IO_LEFTARM;
            text = QPATHTOEF(gui,data\body_image\leftarm_io.paa);
        };
        class BodyBackground_IO_RightLeg: BodyBackground_IO_Torso {
            idc = IDC_TRANSFUSIONMENU_BG_IO_RIGHTLEG;
            text = QPATHTOEF(gui,data\body_image\rightleg_io.paa);
        };
        class BodyBackground_IO_LeftLeg: BodyBackground_IO_Torso {
            idc = IDC_TRANSFUSIONMENU_BG_IO_LEFTLEG;
            text = QPATHTOEF(gui,data\body_image\leftleg_io.paa);
        };
        BODY_BACKGROUND_IV(RightArm,Upper,IDC_TRANSFUSIONMENU_BG_IV_RIGHTARM_UPPER);
        BODY_BACKGROUND_IV(RightArm,Middle,IDC_TRANSFUSIONMENU_BG_IV_RIGHTARM_MIDDLE);
        BODY_BACKGROUND_IV(RightArm,Lower,IDC_TRANSFUSIONMENU_BG_IV_RIGHTARM_LOWER);

        BODY_BACKGROUND_IV(LeftArm,Upper,IDC_TRANSFUSIONMENU_BG_IV_LEFTARM_UPPER);
        BODY_BACKGROUND_IV(LeftArm,Middle,IDC_TRANSFUSIONMENU_BG_IV_LEFTARM_MIDDLE);
        BODY_BACKGROUND_IV(LeftArm,Lower,IDC_TRANSFUSIONMENU_BG_IV_LEFTARM_LOWER);

        BODY_BACKGROUND_IV(RightLeg,Upper,IDC_TRANSFUSIONMENU_BG_IV_RIGHTLEG_UPPER);
        BODY_BACKGROUND_IV(RightLeg,Middle,IDC_TRANSFUSIONMENU_BG_IV_RIGHTLEG_MIDDLE);
        BODY_BACKGROUND_IV(RightLeg,Lower,IDC_TRANSFUSIONMENU_BG_IV_RIGHTLEG_LOWER);

        BODY_BACKGROUND_IV(LeftLeg,Upper,IDC_TRANSFUSIONMENU_BG_IV_LEFTLEG_UPPER);
        BODY_BACKGROUND_IV(LeftLeg,Middle,IDC_TRANSFUSIONMENU_BG_IV_LEFTLEG_MIDDLE);
        BODY_BACKGROUND_IV(LeftLeg,Lower,IDC_TRANSFUSIONMENU_BG_IV_LEFTLEG_LOWER);

        class BodyBackground_Tourniquet_RightArm: BodyBackground {
            idc = IDC_TRANSFUSIONMENU_BG_TOURNIQUET_RIGHTARM;
            text = QPATHTOEF(gui,data\body_image\rightarm_tourniquet.paa);
            colorText[] = {0, 0, 0.8, 1};
        };
        class BodyBackground_Tourniquet_LeftArm: BodyBackground_Tourniquet_RightArm {
            idc = IDC_TRANSFUSIONMENU_BG_TOURNIQUET_LEFTARM;
            text = QPATHTOEF(gui,data\body_image\leftarm_tourniquet.paa);
        };
        class BodyBackground_Tourniquet_RightLeg: BodyBackground_Tourniquet_RightArm {
            idc = IDC_TRANSFUSIONMENU_BG_TOURNIQUET_RIGHTLEG;
            text = QACEPATHTOF(medical_gui,data\body_image\leg_right_t.paa);
        };
        class BodyBackground_Tourniquet_LeftLeg: BodyBackground_Tourniquet_RightArm {
            idc = IDC_TRANSFUSIONMENU_BG_TOURNIQUET_LEFTLEG;
            text = QACEPATHTOF(medical_gui,data\body_image\leg_left_t.paa);
        };
    };
    class Controls {
        class BodyPart_Torso: RscButton {
            text = "";
            colorText[] = {1,1,1,0};
            colorDisabled[] = {1,1,1,0};
            colorBackground[] = {1,1,1,0};
            colorBackgroundDisabled[] = {1,1,1,0};
            colorBackgroundActive[] = {1,1,1,0};
            colorFocused[] = {1,1,1,0};
            colorBorder[] = {0,0,0,0};
            idc = -1;
            style = 0;
            x = QUOTE(ACM_UI_CANVAS_X + (ACM_UI_CANVAS_W / 2) - (ACM_UI_CANVAS_W / 54));
            y = QUOTE(safeZoneY + (safeZoneH / 2) - (safeZoneH / 9));
            w = QUOTE(ACM_UI_CANVAS_W / 27);
            h = QUOTE(safeZoneH / 7.15);
            shadow = 0;
            font = "RobotoCondensed";
            sizeEx = "0";
            tooltip = ACECSTRING(medical_gui,Torso);
            enable = 0;
            action = "";
        };
        /*class BodyPart_Head: BodyPart_Torso {
            idc = -1;
            x = QUOTE(ACM_UI_CANVAS_X + (ACM_UI_CANVAS_W / 2) - (ACM_UI_CANVAS_W / 68));
            y = QUOTE(safeZoneY + (safeZoneH / 2) - (safeZoneH / 5.9));
            w = QUOTE(ACM_UI_CANVAS_W / 34);
            h = QUOTE(safeZoneH / 17.1);
            tooltip = "Head";
        };*/
        class BodyPart_RightArm_Upper: BodyPart_Torso {
            idc = -1;
            x = QUOTE(ACM_UI_CANVAS_X + (ACM_UI_CANVAS_W / 2) - (ACM_UI_CANVAS_W / 22));
            y = QUOTE(safeZoneY + (safeZoneH / 2) - (safeZoneH / 9.4));
            w = QUOTE(ACM_UI_CANVAS_W / 37);
            h = QUOTE(safeZoneH / 13.9);
            tooltip = __EVAL(call compile BODYPART_PART(RightArm,Upper));
            action = "";
        };
        class BodyPart_RightArm_Middle: BodyPart_RightArm_Upper {
            y = QUOTE(safeZoneY + (safeZoneH / 2) - (safeZoneH / 29));
            h = QUOTE(safeZoneH / 26);
            tooltip = __EVAL(call compile BODYPART_PART(RightArm,Middle));
            action = "";
        };
        class BodyPart_RightArm_Lower: BodyPart_RightArm_Upper {
            y = QUOTE(safeZoneY + (safeZoneH / 2) + (safeZoneH / 300));
            h = QUOTE(safeZoneH / 20);
            tooltip = __EVAL(call compile BODYPART_PART(RightArm,Lower));
            action = "";
        };
        class BodyPart_LeftArm_Upper: BodyPart_RightArm_Upper {
            x = QUOTE(ACM_UI_CANVAS_X + (ACM_UI_CANVAS_W / 2) + (ACM_UI_CANVAS_W / 54));
            tooltip = __EVAL(call compile BODYPART_PART(LeftArm,Upper));
            action = "";
        };
        class BodyPart_LeftArm_Middle: BodyPart_LeftArm_Upper {
            y = QUOTE(safeZoneY + (safeZoneH / 2) - (safeZoneH / 29));
            h = QUOTE(safeZoneH / 26);
            tooltip = __EVAL(call compile BODYPART_PART(LeftArm,Middle));
            action = "";
        };
        class BodyPart_LeftArm_Lower: BodyPart_LeftArm_Upper {
            y = QUOTE(safeZoneY + (safeZoneH / 2) + (safeZoneH / 300));
            h = QUOTE(safeZoneH / 20);
            tooltip = __EVAL(call compile BODYPART_PART(LeftArm,Lower));
            action = "";
        };
        class BodyPart_RightLeg_Upper: BodyPart_Torso {
            x = QUOTE(ACM_UI_CANVAS_X + (ACM_UI_CANVAS_W / 2) - (ACM_UI_CANVAS_W / 47));
            y = QUOTE(safeZoneY + (safeZoneH / 2) + (safeZoneH / 35));
            w = QUOTE(ACM_UI_CANVAS_W / 47);
            h = QUOTE(safeZoneH / 16);
            tooltip = __EVAL(call compile BODYPART_PART(RightLeg,Upper));
            action = "";
        };
        class BodyPart_RightLeg_Middle: BodyPart_RightLeg_Upper {
            y = QUOTE(safeZoneY + (safeZoneH / 2) + (safeZoneH / 11));
            tooltip = __EVAL(call compile BODYPART_PART(RightLeg,Middle));
            action = "";
        };
        class BodyPart_RightLeg_Lower: BodyPart_RightLeg_Upper {
            y = QUOTE(safeZoneY + (safeZoneH / 2) + (safeZoneH / 6.55));
            tooltip = __EVAL(call compile BODYPART_PART(RightLeg,Lower));
            action = "";
        };
        class BodyPart_LeftLeg_Upper: BodyPart_RightLeg_Upper {
            x = QUOTE(ACM_UI_CANVAS_X + (ACM_UI_CANVAS_W / 2) + (ACM_UI_CANVAS_W / 5000));
            tooltip = __EVAL(call compile BODYPART_PART(LeftLeg,Upper));
            action = "";
        };
        class BodyPart_LeftLeg_Middle: BodyPart_LeftLeg_Upper {
            y = QUOTE(safeZoneY + (safeZoneH / 2) + (safeZoneH / 11));
            tooltip = __EVAL(call compile BODYPART_PART(LeftLeg,Middle));
            action = "";
        };
        class BodyPart_LeftLeg_Lower: BodyPart_LeftLeg_Upper {
            y = QUOTE(safeZoneY + (safeZoneH / 2) + (safeZoneH / 6.55));
            tooltip = __EVAL(call compile BODYPART_PART(LeftLeg,Lower));
            action = "";
        };
        class LeftPanelList: RscListBox
        {
            idc = IDC_TRANSFUSIONMENU_LEFTLISTPANEL;
            x = QUOTE(ACM_UI_CANVAS_X + ACM_UI_CANVAS_W * 0.137);
            y = QUOTE(safeZoneY + safeZoneH * 0.228);
            w = QUOTE(ACM_UI_CANVAS_W * 0.200);
            h = QUOTE(safeZoneH * 0.230);
            rowHeight = QUOTE(safeZoneH / 20);
            colorText[] = ACM_TRANSFUSION_COLOR_TEXT;
            colorSelect[] = ACM_TRANSFUSION_COLOR_TEXT;
            colorSelect2[] = ACM_TRANSFUSION_COLOR_TEXT;
            colorBackground[] = {0,0,0,0.75};
            colorSelectBackground[] = ACM_TRANSFUSION_COLOR_SELECTED;
            colorSelectBackground2[] = ACM_TRANSFUSION_COLOR_SELECTED;
            sizeEx = QUOTE(safeZoneH * 0.019);
            class Items {};
            font = "RobotoCondensed";
        };
        class SwitchTargetInventory: RscButtonMenu {
            idc = IDC_TRANSFUSIONMENU_SWITCHTARGET;
            x = QUOTE(ACM_UI_CANVAS_X + ACM_UI_CANVAS_W * 0.838);
            y = QUOTE(safeZoneY + safeZoneH * 0.193);
            w = QUOTE(ACM_UI_CANVAS_W * 0.033);
            h = QUOTE(safeZoneH * 0.030);
            shadow = 0;
            font = "RobotoCondensed";
            sizeEx = "0";
            action = QUOTE([] call FUNC(TransfusionMenu_SwitchTargetInventory));
            textureNoShortcut = QPATHTOF(ui\transfusionmenu\inventory_select_ca.paa);
            tooltip = CSTRING(Common_SwitchTargetInventory);
            colorBackground[] = {1,1,1,0};
            colorBackgroundFocused[] = {1,1,1,0};
            period = 0;
            periodFocus = 0;
            periodOver = 0;
            class ShortcutPos
            {
                left = 0;
                top = 0;
                w = QUOTE(ACM_UI_CANVAS_W / 55);
                h = QUOTE(safeZoneH / 30);
            };
        };
        class StopTransfusionButton: RscButton {
            text = "";
            colorText[] = ACM_TRANSFUSION_COLOR_TEXT;
            colorDisabled[] = {0.76,0.76,0.76,0.35};
            colorBackground[] = {0,0,0,0};
            colorBackgroundDisabled[] = {0,0,0,0};
            colorBackgroundActive[] = {0,0,0,0};
            colorFocused[] = {0,0,0,0};
            colorBorder[] = {0,0,0,0};
            idc = IDC_TRANSFUSIONMENU_BUTTON_STOPIV;
            style = ST_CENTER;
            x = QUOTE(ACM_TRANSFUSION_LEFT_X);
            y = QUOTE(safeZoneY + safeZoneH * 0.188);
            w = QUOTE(ACM_TRANSFUSION_LEFT_W);
            h = QUOTE(safeZoneH * 0.029);
            shadow = 0;
            font = "RobotoCondensed";
            sizeEx = QUOTE(safeZoneH * 0.020);
            action = QUOTE(call FUNC(TransfusionMenu_ToggleIVFlow));
            tooltip = "";
        };
        class MoveBagButton: StopTransfusionButton {
            colorDisabled[] = {0.76,0.76,0.76,0.35};
            colorBackgroundDisabled[] = {0,0,0,0};
            text = CSTRING(TransfusionMenu_MoveBag_Display);
            idc = IDC_TRANSFUSIONMENU_BUTTON_MOVEBAG;
            x = QUOTE(ACM_UI_CANVAS_X + ACM_UI_CANVAS_W * 0.141);
            y = QUOTE(safeZoneY + safeZoneH * 0.226);
            w = QUOTE(ACM_UI_CANVAS_W * 0.180);
            action = QUOTE(call FUNC(TransfusionMenu_MoveBag));
            tooltip = CSTRING(TransfusionMenu_MoveBag_ToolTip);
            h = QUOTE(safeZoneH * 0.033);
        };
        class RemoveBagButton: MoveBagButton {
            text = CSTRING(TransfusionMenu_RemoveBag_Display);
            idc = IDC_TRANSFUSIONMENU_BUTTON_REMOVEBAG;
            y = QUOTE(safeZoneY + safeZoneH * 0.265);
            action = QUOTE(call FUNC(TransfusionMenu_RemoveBag));
            tooltip = CSTRING(TransfusionMenu_RemoveBag_ToolTip);
        };
        /*class InfuseBagButton: MoveBagButton {
            text = "Infuse";
            idc = -1;
            y = QUOTE(safeZoneY + (safeZoneH / 2) - (safeZoneH / 10));
            action = "";
            tooltip = "Infuse medication into fluid bag";
        };*/

        class RightPanelList: LeftPanelList
        {
            idc = IDC_TRANSFUSIONMENU_RIGHTLISTPANEL;
            x = QUOTE(ACM_UI_CANVAS_X + ACM_UI_CANVAS_W * 0.673);
            y = QUOTE(safeZoneY + safeZoneH * 0.279);
            w = QUOTE(ACM_UI_CANVAS_W * 0.202);
            h = QUOTE(safeZoneH * 0.235);
        };
        class AddBagButton: StopTransfusionButton {
            text = CSTRING(TransfusionMenu_AddBag_Display);
            idc = IDC_TRANSFUSIONMENU_BUTTON_ADDBAG;
            x = QUOTE(ACM_UI_CANVAS_X + ACM_UI_CANVAS_W * 0.673);
            action = QUOTE(call FUNC(TransfusionMenu_AddBag));
            tooltip = CSTRING(TransfusionMenu_AddBag_ToolTip);
            y = QUOTE(safeZoneY + safeZoneH * 0.526);
            w = QUOTE(ACM_UI_CANVAS_W * 0.202);
        };
    };
};
