/* Carousel hover is bookkeeping only.
   It never rebuilds the carousel and never changes syringe opacity. Geometry and presentation are changed only
   by explicit navigation/edit/admin actions, which prevents MouseEnter/MouseExit repaint loops on overlapping hitboxes. */
params [["_hover",false,[false]]];
if ((uiNamespace getVariable ["ACME_SK_View","syringe"]) != "body") exitWith {};
if (uiNamespace getVariable ["ACME_SK_TagEditMode",false]) exitWith {};
uiNamespace setVariable ["ACME_SK_CarouselHover",_hover];
if (uiNamespace getVariable ["ACME_SK_CarouselExpanded",false]) then {
    uiNamespace setVariable ["ACME_SK_CarouselCollapseAt",diag_tickTime + (if (_hover) then {1.10} else {0.70})];
};
