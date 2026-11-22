class CfgWeapons {
    class ACE_ItemCore;
    class CBA_MiscItem_ItemInfo;

    class ACME_OPA: ACE_ItemCore {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        picture = QPATHTOF(ui\opa_ca.paa);
        displayName = CSTRING(OPA);
        descriptionShort = CSTRING(OPA_Desc);
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 0.3;
        };
    };

    class ACME_IGel: ACME_OPA {
        picture = QPATHTOF(ui\igel_ca.paa);
        displayName = CSTRING(IGel);
        descriptionShort = CSTRING(IGel_Desc);
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 2;
        };
    };

    class ACME_NPA: ACME_OPA {
        picture = QPATHTOF(ui\npa_ca.paa);
        displayName = CSTRING(NPA);
        descriptionShort = CSTRING(NPA_Desc);
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 0.3125;
        };
    };

    class ACME_SuctionBag: ACME_OPA {
        picture = QPATHTOF(ui\suctionbag_ca.paa);
        displayName = CSTRING(SuctionBag);
        descriptionShort = CSTRING(SuctionBag_Desc);
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 4.5;
        };
    };

    class ACME_ACCUVAC: ACME_SuctionBag {
        picture = QPATHTOF(ui\accuvac_ca.paa);
        displayName = CSTRING(ACCUVAC);
        descriptionShort = CSTRING(ACCUVAC_Desc);
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 94.8;
        };
    };

    class ACME_CricKit: ACME_OPA {
        picture = QPATHTOF(ui\crickit_ca.paa);
        displayName = CSTRING(CricKit);
        descriptionShort = CSTRING(CricKit_Desc);
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 2.3125;
        };
    };
};
