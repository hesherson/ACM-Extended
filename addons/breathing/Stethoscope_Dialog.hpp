#include "..\main\ui_theme.hpp"
#include "Stethoscope_defines.hpp"

class GVAR(Stethoscope_Dialog) {
    idd = IDC_STETHOSCOPE;
    movingEnable = 0;
    onLoad = "";
    onUnload = "_this call ACME_fnc_stethoscopeClose;";
    objects[] = {};

    class ControlsBackground {
        class BodyBackground: RscPicture {
            idc = IDC_STETHOSCOPE_BODY;
            x = QUOTE(ACM_STETHOSCOPE_BG_POS_X_CENTER(180));
            y = QUOTE(ACM_STETHOSCOPE_BG_POS_Y_CENTER(135,36));
            w = QUOTE(ACM_STETHOSCOPE_POS_W(180));
            h = QUOTE(ACM_STETHOSCOPE_POS_H(135));
            type = 0;
            size = 0;
            text = QPATHTOEF(gui,ui\body_background.paa);
        };

        class RightLung_Space: RscText {
            idc = IDC_STETHOSCOPE_RIGHTLUNG_SPACE;
            x = QUOTE(ACM_STETHOSCOPE_POS_X(12.5));
            y = QUOTE(ACM_STETHOSCOPE_POS_Y(-1.5));
            w = QUOTE(ACM_STETHOSCOPE_POS_W(5.8));
            h = QUOTE(ACM_STETHOSCOPE_POS_H(10));
            colorBackground[] = {1,1,1,0.5};
            show = 0;
        };

        class RightLung_Space_2: RightLung_Space {
            idc = IDC_STETHOSCOPE_RIGHTLUNG_SPACE_2;
            x = QUOTE(ACM_STETHOSCOPE_POS_X(10));
            y = QUOTE(ACM_STETHOSCOPE_POS_Y(3));
            w = QUOTE(ACM_STETHOSCOPE_POS_W(5));
            h = QUOTE(ACM_STETHOSCOPE_POS_H(8));
        };

        class LeftLung_Space: RightLung_Space {
            idc = IDC_STETHOSCOPE_LEFTLUNG_SPACE;
            x = QUOTE(ACM_STETHOSCOPE_POS_X(22));
        };
        class LeftLung_Space_2: RightLung_Space_2 {
            idc = IDC_STETHOSCOPE_LEFTLUNG_SPACE_2;
            x = QUOTE(ACM_STETHOSCOPE_POS_X(25.5));
        };

        class RightSide: RightLung_Space {
            idc = IDC_STETHOSCOPE_RIGHTSIDE;
            x = QUOTE(ACM_STETHOSCOPE_POS_X(8.5));
            y = QUOTE(ACM_STETHOSCOPE_POS_Y(-5.3));
            w = QUOTE(ACM_STETHOSCOPE_POS_W(11.5));
            h = QUOTE(ACM_STETHOSCOPE_POS_H(22));
            colorBackground[] = {0,1,0,0.5};
            show = 0;
        };
        class LeftSide: RightSide {
            idc = IDC_STETHOSCOPE_LEFTSIDE;
            x = QUOTE(ACM_STETHOSCOPE_POS_X(20));
        };

        class Bone_Sternum: RightLung_Space {
            idc = IDC_STETHOSCOPE_BONE_STERNUM;
            x = QUOTE(ACM_STETHOSCOPE_POS_X(18));
            y = QUOTE(ACM_STETHOSCOPE_POS_Y(-1.5));
            w = QUOTE(ACM_STETHOSCOPE_POS_W(4));
            h = QUOTE(ACM_STETHOSCOPE_POS_H(9));
            colorBackground[] = {1,1,0.5,0.5};
        };

        class RightLung_Bronchial: RightLung_Space {
            idc = IDC_STETHOSCOPE_RIGHTLUNG_BRONCHIAL;
            x = QUOTE(ACM_STETHOSCOPE_POS_X(14.3));
            y = QUOTE(ACM_STETHOSCOPE_POS_Y(-5.2));
            w = QUOTE(ACM_STETHOSCOPE_POS_W(3));
            h = QUOTE(ACM_STETHOSCOPE_POS_H(3));
            colorBackground[] = {0,1,0,0.5};
        };
        class RightLung_BronchoVesticular: RightLung_Bronchial {
            idc = IDC_STETHOSCOPE_RIGHTLUNG_BRONCHOVESTICULAR;
            x = QUOTE(ACM_STETHOSCOPE_POS_X(14));
            y = QUOTE(ACM_STETHOSCOPE_POS_Y(-0.2));
        };
        class RightLung_Vesticular_Middle: RightLung_Bronchial {
            idc = IDC_STETHOSCOPE_RIGHTLUNG_VESTICULAR_MIDDLE;
            x = QUOTE(ACM_STETHOSCOPE_POS_X(11.5));
            y = QUOTE(ACM_STETHOSCOPE_POS_Y(4.8));
        };
        class RightLung_Vesticular_Lower: RightLung_Bronchial {
            idc = IDC_STETHOSCOPE_RIGHTLUNG_VESTICULAR_LOWER;
            x = QUOTE(ACM_STETHOSCOPE_POS_X(10.6));
            y = QUOTE(ACM_STETHOSCOPE_POS_Y(9.8));
        };

        class LeftLung_Bronchial: RightLung_Bronchial {
            idc = IDC_STETHOSCOPE_LEFTLUNG_BRONCHIAL;
            x = QUOTE(ACM_STETHOSCOPE_POS_X(23));
        };
        class LeftLung_BronchoVesticular: RightLung_BronchoVesticular {
            idc = IDC_STETHOSCOPE_LEFTLUNG_BRONCHOVESTICULAR;
            x = QUOTE(ACM_STETHOSCOPE_POS_X(23));
        };
        class LeftLung_Vesticular_Middle: RightLung_Vesticular_Middle {
            idc = IDC_STETHOSCOPE_LEFTLUNG_VESTICULAR_MIDDLE;
            x = QUOTE(ACM_STETHOSCOPE_POS_X(26.2));
        };
        class LeftLung_Vesticular_Lower: RightLung_Vesticular_Lower {
            idc = IDC_STETHOSCOPE_LEFTLUNG_VESTICULAR_LOWER;
            x = QUOTE(ACM_STETHOSCOPE_POS_X(27.4));
        };

        class Heart_1: RightLung_Space {
            idc = IDC_STETHOSCOPE_HEART_1;
            x = QUOTE(ACM_STETHOSCOPE_POS_X(16.6));
            y = QUOTE(ACM_STETHOSCOPE_POS_Y(0.3));
            w = QUOTE(ACM_STETHOSCOPE_POS_W(2));
            h = QUOTE(ACM_STETHOSCOPE_POS_H(2));
            colorBackground[] = {1,0,0,0.5};
        };
        class Heart_2: Heart_1 {
            idc = IDC_STETHOSCOPE_HEART_2;
            x = QUOTE(ACM_STETHOSCOPE_POS_X(21.5));
        };
        class Heart_3: Heart_1 {
            idc = IDC_STETHOSCOPE_HEART_3;
            x = QUOTE(ACM_STETHOSCOPE_POS_X(21.7));
            y = QUOTE(ACM_STETHOSCOPE_POS_Y(2.4));
        };
        class Heart_4: Heart_1 {
            idc = IDC_STETHOSCOPE_HEART_4;
            x = QUOTE(ACM_STETHOSCOPE_POS_X(21.9));
            y = QUOTE(ACM_STETHOSCOPE_POS_Y(4.6));
        };
        class Heart_Center: Heart_1 {
            idc = IDC_STETHOSCOPE_HEART_CENTER;
            x = QUOTE(ACM_STETHOSCOPE_POS_X(20));
            y = QUOTE(ACM_STETHOSCOPE_POS_Y(1));
            w = QUOTE(ACM_STETHOSCOPE_POS_W(1));
            h = QUOTE(ACM_STETHOSCOPE_POS_H(1));
        };
    };
    class Controls {
        class TopText: RscText {
            idc = -1;
            style = ST_CENTER;
            font = ACM_UI_FONT;
            x = QUOTE(safeZoneX);
            y = QUOTE(safeZoneY);
            w = QUOTE(safeZoneW);
            h = QUOTE(safeZoneH / 10);
            colorText[] = ACM_UI_INK(1);
            colorBackground[] = {0,0,0,0};
            text = "Hold left mouse to listen and drag. Release to lift the bell.";
            lineSpacing = 0;
            sizeEx = QUOTE(GUI_GRID_H * 1.4 * NORMALIZE_SIZEEX);
            fixedWidth = 0;
            deletable = 0;
            fade = 0;
            access = 0;
            type = 0;
            shadow = 1;
            colorShadow[] = {0,0,0,0.5};
        };
        class BottomText: TopText {
            idc = IDC_STETHOSCOPE_TEXT;
            h = QUOTE(safeZoneH / 6);
            text = "";
        };

        class ViewLabel: TopText {
            idc = IDC_STETHOSCOPE_VIEW_LABEL;
            x = 0;
            y = 0;
            w = 0;
            h = 0;
            sizeEx = QUOTE(GUI_GRID_H * 0.8 * NORMALIZE_SIZEEX);
            text = "";
        };
        class ChangeView: RscButton {
            idc = IDC_STETHOSCOPE_VIEW;
            x = QUOTE(safeZoneX + safeZoneW * 0.4625);
            y = QUOTE(safeZoneY + safeZoneH * 0.92);
            w = QUOTE(safeZoneW * 0.075);
            h = QUOTE(safeZoneH * 0.045);
            text = "Flip Side";
            tooltip = "Turn the patient over (front / back)";
            onButtonClick = "[] call ACME_fnc_stethoscopeFlip;";
            colorBackground[] = {0.14, 0.20, 0.30, 0.90};
            colorText[] = {0.93, 0.89, 0.80, 1};
            colorDisabled[] = ACM_UI_MUTED(0.65);
            colorBackgroundActive[] = ACM_UI_HOVER(1);
            colorBackgroundDisabled[] = ACM_UI_PANEL(1);
            colorFocused[] = ACM_UI_ACTIVE(1);
            font = ACM_UI_FONT;
        };
        class Bell: RscPicture {
            idc = IDC_STETHOSCOPE_BELL;
            x = QUOTE(ACM_pxToScreen_X(960));
            y = QUOTE(ACM_pxToScreen_Y(800));
            w = QUOTE(ACM_pxToScreen_W(152));
            h = QUOTE(ACM_pxToScreen_H(152));
            shadow = 0;
            text = QPATHTOF(ui\stethoscope_bell.paa);
        };
    };
};
