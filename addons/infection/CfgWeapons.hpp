class CfgWeapons {
    class ACE_ItemCore;
    class CBA_MiscItem_ItemInfo;

    class ACME_Moxifloxacin_SinglePack: ACE_ItemCore {
        dlc = "ACM_Extended";
        author = "mavis";
        authors[] = {"mavis", "Inferno"};
        scope = 1;
        picture = QPATHTOF(ui\moxiflox.paa);
        displayName = CSTRING(Moxifloxacin_SinglePack);
        descriptionShort = CSTRING(Moxifloxacin_Desc);
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 0.03;
        };
    };
};
