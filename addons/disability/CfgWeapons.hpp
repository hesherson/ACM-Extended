class CfgWeapons {
    class ACE_ItemCore;
    class CBA_MiscItem_ItemInfo;

    class ACE_splint: ACE_ItemCore {
        displayName = CSTRING(UniversalSplint);
        descriptionShort = CSTRING(UniversalSplint_Desc);
        scope = 1;
    };
    class ACME_SAMSplint: ACE_splint {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        picture = QPATHTOF(ui\samsplint.paa);
        displayName = CSTRING(SAMSplint);
        descriptionShort = CSTRING(SAMSplint_Desc);
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 0.5;
        };
    };
};
