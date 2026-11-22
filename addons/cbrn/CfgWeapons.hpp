class CfgWeapons {
	class GrenadeLauncher;
    class Throw: GrenadeLauncher {
        muzzles[] += {"ACM_Grenade_CS_Muzzle"};

        class ThrowMuzzle;
        class ACM_Grenade_CS_Muzzle: ThrowMuzzle {
            magazines[] = {"ACME_Grenade_CS"};
        };
    };

    class CannonCore;
    class mortar_82mm: CannonCore {
        magazines[] += {"ACME_Mortar_Shell_8Rnd_CS","ACME_Mortar_Shell_8Rnd_Chlorine","ACME_Mortar_Shell_8Rnd_Sarin","ACME_Mortar_Shell_8Rnd_Lewisite"};
    };

    class ACE_ItemCore;
    class CBA_MiscItem_ItemInfo;

    class ACME_GasMaskFilter: ACE_ItemCore {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        picture = QPATHTOF(ui\gasMaskFilter_ca.paa);
        displayName = CSTRING(GasMaskFilter);
        descriptionShort = CSTRING(GasMaskFilter_Desc);
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 3;
        };
    };

    class ACME_Autoinjector_ATNA: ACE_ItemCore {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        picture = QPATHTOF(ui\autoinjector_ATNA_ca.paa);
        displayName = CSTRING(Autoinjector_ATNA);
        descriptionShort = CSTRING(Autoinjector_ATNA_Desc);
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 1.8;
        };
    };

    class ACME_Autoinjector_Midazolam: ACME_Autoinjector_ATNA {
        picture = QPATHTOF(ui\autoinjector_midazolam_ca.paa);
        displayName = CSTRING(Autoinjector_Midazolam);
        descriptionShort = CSTRING(Autoinjector_Midazolam_Desc);
    };
};
