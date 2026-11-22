class CfgWeapons {
    class ACE_ItemCore;
    class CBA_MiscItem_ItemInfo;

    class ACME_PressureBandage: ACE_ItemCore {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        model = QACEPATHTOF(medical_treatment,data\bandage.p3d);
        picture = QPATHTOF(ui\pressurebandage.paa);
        displayName = CSTRING(PressureBandage);
        descriptionShort = CSTRING(PressureBandage_Desc);
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 0.6;
        };
    };
    class ACME_EmergencyTraumaDressing: ACME_PressureBandage {
        picture = QPATHTOF(ui\etd.paa);
        displayName = CSTRING(EmergencyTraumaDressing);
        descriptionShort = CSTRING(EmergencyTraumaDressing_Desc);
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 2;
        };
    };
    class ACME_ElasticWrap: ACME_PressureBandage {
        picture = QACEPATHTOF(medical_treatment,ui\elasticbandage_ca.paa);
        displayName = CSTRING(ElasticWrap);
        descriptionShort = CSTRING(ElasticWrap_Desc);
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 0.3;
        };
    };
};
