class CfgWeapons {
    class ACE_ItemCore;
    class CBA_MiscItem_ItemInfo;

    class ACME_ChestSeal: ACE_ItemCore {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        picture = QPATHTOF(ui\chestseal_ca.paa);
        displayName = CSTRING(ChestSeal);
        descriptionShort = CSTRING(ChestSeal_Desc);
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 0.856;
        };
    };

    class ACME_PulseOximeter: ACME_ChestSeal {
        picture = QPATHTOF(ui\pulseoximeter_ca.paa);
        displayName = CSTRING(PulseOximeter);
        descriptionShort = CSTRING(PulseOximeter_Desc);
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 1.6;
        };
    };

    class ACME_Stethoscope: ACME_ChestSeal {
        picture = QPATHTOF(ui\stethoscope_ca.paa);
        displayName = CSTRING(Stethoscope);
        descriptionShort = CSTRING(Stethoscope_Desc);
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 3.125;
        };
    };

    class ACME_NCDKit: ACME_ChestSeal {
        picture = QPATHTOF(ui\ncdkit_ca.paa);
        displayName = CSTRING(NCDKit);
        descriptionShort = CSTRING(NCDKit_Desc);
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 0.625;
        };
    };

    class ACME_ChestTubeKit: ACME_ChestSeal {
        picture = QPATHTOF(ui\chestTubeKit_ca.paa);
        displayName = CSTRING(ChestTubeKit);
        descriptionShort = CSTRING(ChestTubeKit_Desc);
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 6.125;
        };
    };

    class ACME_ThoracostomyKit: ACME_ChestSeal {
        picture = QPATHTOF(ui\thoracostomyKit_ca.paa);
        displayName = CSTRING(ThoracostomyKit);
        descriptionShort = CSTRING(ThoracostomyKit_Desc);
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 3.3;
        };
    };

    class ACME_PocketBVM: ACME_ChestSeal {
        picture = QPATHTOF(ui\pocketBVM_ca.paa);
        displayName = CSTRING(PocketBVM);
        descriptionShort = CSTRING(PocketBVM_Desc);
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 10.1125;
        };
    };

    /*class ACM_PocketBVM_Packed: ACME_PocketBVM {
        picture = QPATHTOF(ui\pocketbvm_p_ca.paa);
        displayName = "Pocket BVM (Packaged)";
        descriptionShort = "desc short";
        descriptionUse = "desc use";
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 2.5;
        };
    };*/

    class ACME_BVM: ACME_PocketBVM {
        picture = QPATHTOF(ui\bvm_ca.paa);
        displayName = CSTRING(BVM);
        descriptionShort = CSTRING(BVM_Desc);
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 12;
        };
    };

    class ACME_OxygenTank_425_Empty: ACME_ChestSeal {
        scope = 1;
        picture = QPATHTOF(ui\oxygentank_ca.paa);
        displayName = CSTRING(OxygenTank_425_Empty);
        descriptionShort = CSTRING(OxygenTank_425_Desc);
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 85;
        };
    };
};
