class CfgMagazines {
    class CA_Magazine;

    class ACME_Moxifloxacin: CA_Magazine {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        authors[] = {"mavis", "Inferno"};
        picture = QPATHTOF(ui\moxiflox.paa);
        displayName = CSTRING(Moxifloxacin);
        descriptionShort = CSTRING(Moxifloxacin_Desc);
        ACE_isMedicalItem = 1;
        ACE_asItem = 1;
        count = 5;
        mass = 0.15;
    };
};
