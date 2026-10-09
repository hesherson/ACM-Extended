// NOT INCLUDED. config.cpp carries no #include directive at all, so nothing in this file reaches the build.
// it is kept as a reference copy of the item block. the iv_18 picture path was corrected here at
// v0.9.999r-50 only so the file does not point at a texture that no longer exists.
// the item definitions for the infusion extension.
// on the medical-items tab: ACE's arsenal filter keys on ACE_isMedicalItem = 1. ACM's vials set it explicitly and
// ACM's blood and saline bags inherit it from ACE's ACE_bloodIV base. we mirror both, so the HTS bags sit with
// the bags and the norepinephrine vial sits with the vials, exactly like the native items.
class CfgWeapons {
    class ACE_ItemCore;
    class CBA_MiscItem_ItemInfo;
    class ACE_bloodIV;  // the ACE base for iv fluid bags, medical-tagged.
    class ACE_salineIV_250;  // the ACE 250 ml saline bag, the carrier base for our premixed drips.
    // the norepinephrine, or levophed, vial. it is in the vial family.
    class ACM_Vial_Norepinephrine: ACE_ItemCore {
        scope = 2;
        author = "mavis";
        displayName = "Norepinephrine (4mg/4ml)";
        descriptionShort = "Vasopressor. CPP support AFTER volume resuscitation.";
        picture = "\acm_extended\ui\items\vial_norepinephrine_ca.paa";
        ACE_isMedicalItem = 1;
        ACM_isVial = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 0.3;
        };
    };

    // hypertonic saline 3 percent, a premixed transfusable bag.
    // it is a real fluid bag in the same family as saline, plasma and blood. it is not flagged ACM_isVial, so it no
    // longer appears in the infusion draw list and cannot be mixed into another bag, because it is already premixed.
    // ACME_premixedBag marks it for the auto-attach loop, fn_syncpremixedbags, which layers HTS osmotherapy on the
    // active bag. it is registered into ACM's fluid list in fn_postInit, so it lists in add bag.
    class ACM_Vial_HTS3: ACE_salineIV_250 {
        scope = 2;
        author = "mavis";
        displayName = "Hypertonic Saline 3% (250ml)";
        descriptionShort = "Osmotherapy for raised ICP / hyponatremia. NOT volume resuscitation. Premixed transfusable bag.";
        picture = "\acm_extended\ui\items\htsiv_ca.paa";
        ACE_isMedicalItem = 1;
        ACME_premixedBag = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 8;
        };
    };

    // the premixed esmolol drip bag, 2500 mg in 250 ml, which is 10 mg/ml.
    // it is a real fluid bag in the same family as saline, plasma and blood. it is not flagged ACM_isVial, so it
    // leaves the infusion draw list and cannot be mixed into another bag, because it is already premixed.
    // ACME_premixedBag marks it for the auto-attach loop, fn_syncpremixedbags, which layers esmolol rate control on
    // the active bag. the premixed content is declared in ACME_infusion_PremixedBags and premixedbytype, in
    // fn_postInit.
    class ACM_EsmololBag: ACE_salineIV_250 {
        scope = 2;
        author = "mavis";
        displayName = "Esmolol 2500mg/250ml (10mg/ml)";
        descriptionShort = "Premixed esmolol drip. Rate control for AFib-RVR / atrial tach (titrate to mcg/kg/min). Transfusable bag.";
        picture = "\acm_extended\ui\items\esmololbagiv_ca.paa";
        ACE_isMedicalItem = 1;
        ACME_premixedBag = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 8;
        };
    };

    // display-only proxy classes for the active premixed bags.
    // ACM resolves the shown name of an active bag from the CfgWeapons class whose name is
    // formatfluidbagname(type,volume), which is ace_<lowertype>iv_<vol>. with distinct fluid types, esmolol and hts
    // at 250 ml, the active bags resolve to these, which gives the correct name and icon instead of a generic saline
    // label. scope is 1, so they are never offered from inventory.
    class ACE_esmololIV_250: ACE_salineIV_250 {
        scope = 1;
        author = "mavis";
        displayName = "Esmolol 2500mg/250ml (10mg/ml)";
        picture = "\acm_extended\ui\items\esmololbagiv_ca.paa";
    };
    class ACE_htsIV_250: ACE_salineIV_250 {
        scope = 1;
        author = "mavis";
        displayName = "Hypertonic Saline 3% (250ml)";
        picture = "\acm_extended\ui\items\htsiv_ca.paa";
    };

    // calcium chloride 10 percent, 1 g in 10 ml, for citrate and hypocalcemia.
    class ACM_CaCl2_10: ACE_ItemCore {
        scope = 2;
        author = "mavis";
        displayName = "Calcium Chloride 10% (1g/10ml)";
        descriptionShort = "Repletes ionized calcium in massive transfusion (citrate). Slow IV push.";
        picture = "\acm_extended\ui\items\vial_norepinephrine_ca.paa";  // todo[art]: a calcium icon.
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 0.5;
        };
    };

    // mannitol 20 percent, a 100 g push, for osmotherapy and diuresis.
    class ACM_Mannitol_100: ACE_ItemCore {
        scope = 2;
        author = "mavis";
        displayName = "Mannitol 20% (push)";
        descriptionShort = "Osmotic diuretic for raised ICP. Watch for hypotension.";
        picture = "\acm_extended\ui\items\vial_norepinephrine_ca.paa";  // todo[art]: a mannitol icon.
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 3;
        };
    };

    // the 18g iv catheter: a smaller-bore peripheral line with a slower flow.
    class ACM_IV_18g: ACE_ItemCore {
        scope = 2;
        author = "mavis";
        displayName = "18g IV";
        descriptionShort = "Smaller-bore peripheral IV. Slower flow than 16G. Distal limb sites risk a hypertensive surge with drips/pressors.";
        picture = "\acm_extended\ui\items\iv_18g_ca.paa";
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 1;
        };
    };

    // the prefilled 10 ml saline flush, the push-dose epi base.
    class ACM_SalineFlush_10: ACE_ItemCore {
        scope = 2;
        author = "mavis";
        displayName = "Saline Flush (10ml)";
        descriptionShort = "Prefilled 10 mL flush. Base for improvised push-dose epi (1:100,000).";
        picture = "\acm_extended\ui\items\salineFlush_ca.paa";
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 0.6;
        };
    };

    // the core thermometer, a reusable tool. it is the only way to read the core temperature.
    // it is reusable, so it must be in the inventory and is never consumed. it is gated through a condition with an
    // empty items[].
    class ACM_Thermometer: ACE_ItemCore {
        scope = 2;
        author = "mavis";
        displayName = "Core Thermometer";
        descriptionShort = "Measures patient core temperature for hypothermia assessment. Reusable.";
        picture = "\acm_extended\ui\items\htsiv_ca.paa";  // todo[art]: a thermometer icon.
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 7.9;
        };
    };

    // the non-rebreather mask, a reusable o2 tool. it gives high-flow oxygen with a continuous flow sfx.
    class ACM_NRBMask: ACE_ItemCore {
        scope = 2;
        author = "mavis";
        displayName = "Non-Rebreather Mask";
        descriptionShort = "High-flow oxygen mask (15 L/min, FiO2 ~0.9). Reusable. Apply on the patient's head.";
        picture = "\acm_extended\ui\items\nrbmask_ca.paa";
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 2;
        };
    };
    class ACM_HPMK: ACE_ItemCore {
        scope = 2;
        author = "mavis";
        displayName = "NAR HPMK";
        descriptionShort = "Hypothermia Prevention & Management Kit. Reusable warming blanket.";
        picture = "\acm_extended\ui\items\HPMK_ca.paa";
        nameSound = "";
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 35;
        };
    };
    // the EMMA mainstream capnograph. it attaches inline on a BVM, and the HUD reads out while ventilating.
    class ACM_EMMA: ACE_ItemCore {
        scope = 2;
        author = "mavis";
        displayName = "EMMA Capnograph";
        descriptionShort = "Mainstream end-tidal CO2 monitor. Attach inline on a BVM.";
        picture = "\acm_extended\ui\emma\emma_etco2_ca.paa";
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 1.3;
        };
    };
    // combat gauze, hemostatic packing for junctional hemorrhage.
    // it is stage 1 of the two-stage junctional treatment: pack the wound over 15 s, then secure it with a pressure
    // bandage over another 15 s. it is a proper ACE medical item, so it sits in the medical inventory.
    class ACM_CombatGauze: ACE_ItemCore {
        scope = 2;
        author = "mavis";
        model = "\z\ace\addons\medical_treatment\data\bandage.p3d";
        displayName = "Combat Gauze";
        descriptionShort = "Hemostatic gauze for packing junctional hemorrhage. Pack the wound, then secure with a pressure bandage.";
        picture = "\acm_extended\ui\items\combat_gauze_ca.paa";
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 0.5;
        };
    };
};
