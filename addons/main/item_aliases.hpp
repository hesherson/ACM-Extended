// Old class names that still load. B378: only the four supply CRATES have one (addons/core/CfgVehicles.hpp):
// a mission that has a crate of a class that does not exist does not open. ITEMS have no old-name classes any
// more: each item exists once, under its ACME_ name (a kit saved with old names is read by
// acm_extended, fn_itemClassCanonical.sqf).
#define ACME_ITEM_ALIAS_IMPL(oldClass,newClass) class oldClass: newClass {scope = 1; scopeArsenal = 0; scopeCurator = 0; ace_arsenal_hide = 1; baseWeapon = #newClass; ACME_itemReplacement = #newClass;}
#define ACME_ITEM_ALIAS(oldClass,newClass) ACME_ITEM_ALIAS_IMPL(oldClass,newClass)
