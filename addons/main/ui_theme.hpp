#ifndef ACM_UI_THEME_HPP
#define ACM_UI_THEME_HPP

// Shared presentation roles for ACM-owned controls. Keep dimensions and hit areas at their original definitions.
#define ACM_UI_FONT "RobotoCondensed"
#define ACM_UI_PANEL(A) {0.067,0.071,0.078,A}
#define ACM_UI_SURFACE(A) {0.094,0.098,0.110,A}
#define ACM_UI_RULE(A) {0.161,0.169,0.188,A}
#define ACM_UI_HOVER(A) {0.125,0.129,0.145,A}
#define ACM_UI_ACTIVE(A) {0.188,0.196,0.224,A}
#define ACM_UI_INK(A) {0.953,0.945,0.929,A}
#define ACM_UI_SECONDARY(A) {0.796,0.816,0.855,A}
#define ACM_UI_MUTED(A) {0.659,0.659,0.659,A}
#define ACM_UI_DARK_INK(A) {0.067,0.071,0.078,A}

#define ACM_UI_BUTTON_COLORS \
    colorText[] = ACM_UI_INK(1); \
    colorDisabled[] = ACM_UI_MUTED(0.65); \
    colorBackground[] = ACM_UI_SURFACE(1); \
    colorBackgroundActive[] = ACM_UI_HOVER(1); \
    colorBackgroundDisabled[] = ACM_UI_PANEL(1); \
    colorFocused[] = ACM_UI_ACTIVE(1); \
    font = ACM_UI_FONT;

// SQF uses the same roles for colors set when the dialog is already open.
#define ACM_UI_PANEL_RGB [0.067,0.071,0.078]
#define ACM_UI_SURFACE_RGB [0.094,0.098,0.110]

#endif
