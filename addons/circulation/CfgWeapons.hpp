class CfgWeapons {
    class ACE_ItemCore;
    class CBA_MiscItem_ItemInfo;

    class ACME_AED: ACE_ItemCore {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        picture = QPATHTOF(ui\AED_ca.paa);
        displayName = CSTRING(AED);
        descriptionShort = CSTRING(AED_Desc);
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 185;
        };
    };

    class ACME_PressureCuff: ACME_AED {
        picture = QPATHTOF(ui\pressureCuff_ca.paa);
        displayName = CSTRING(PressureCuff);
        descriptionShort = CSTRING(PressureCuff_Desc);
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 4;
        };
    };

    class ACME_IV_16g: ACE_ItemCore {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        picture = QPATHTOF(ui\iv_16g_ca.paa);
        displayName = CSTRING(IV_16g);
        descriptionShort = CSTRING(IV_16g_Desc);
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 0.2;
        };
    };

    class ACME_IV_14g: ACME_IV_16g {
        picture = QPATHTOF(ui\iv_14g_ca.paa);
        displayName = CSTRING(IV_14g);
        descriptionShort = CSTRING(IV_14g_Desc);
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 0.5;
        };
    };

    class ACME_IO_FAST: ACME_IV_16g {
        picture = QPATHTOF(ui\io_fast1_ca.paa);
        displayName = CSTRING(IO_FAST1);
        descriptionShort = CSTRING(IO_FAST1_Desc);
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 2.813;
        };
    };

    class ACME_IO_EZ: ACME_IV_16g {
        picture = QPATHTOF(ui\IO_EZ_ca.paa);
        displayName = CSTRING(IO_EZ);
        descriptionShort = CSTRING(IO_EZ_Desc);
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 0.6;
        };
    };

    class ACME_Syringe_10: ACE_ItemCore {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        picture = QPATHTOF(ui\syringe_10_ca.paa);
        displayName = __EVAL(call compile QUOTE(format [ARR_2(C_LLSTRING(Syringe_%1),10)]));
        descriptionShort = __EVAL(call compile QUOTE(format [ARR_2(C_LLSTRING(Syringe_Desc_%1),10)]));
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 2.6;
        };
    };
    class ACME_Syringe_5: ACME_Syringe_10 {
        picture = QPATHTOF(ui\syringe_5_ca.paa);
        displayName = __EVAL(call compile QUOTE(format [ARR_2(C_LLSTRING(Syringe_%1),5)]));
        descriptionShort = __EVAL(call compile QUOTE(format [ARR_2(C_LLSTRING(Syringe_Desc_%1),5)]));
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 1.7;
        };
    };
    class ACME_Syringe_3: ACME_Syringe_10 {
        picture = QPATHTOF(ui\syringe_3_ca.paa);
        displayName = __EVAL(call compile QUOTE(format [ARR_2(C_LLSTRING(Syringe_%1),3)]));
        descriptionShort = __EVAL(call compile QUOTE(format [ARR_2(C_LLSTRING(Syringe_Desc_%1),3)]));
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 1.2;
        };
    };
    class ACME_Syringe_1: ACME_Syringe_10 {
        picture = QPATHTOF(ui\syringe_1_ca.paa);
        displayName = __EVAL(call compile QUOTE(format [ARR_2(C_LLSTRING(Syringe_%1),1)]));
        descriptionShort = __EVAL(call compile QUOTE(format [ARR_2(C_LLSTRING(Syringe_Desc_%1),1)]));
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 1;
        };
    };

    class ACME_Vial_Epinephrine: ACE_ItemCore {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        picture = QPATHTOF(ui\vial_epinephrine_ca.paa);
        displayName = CSTRING(Vial_Epinephrine);
        descriptionShort = CSTRING(Vial_Epinephrine_Desc);
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 0.11;
        };
        ACM_isVial = 1;
    };

    class ACME_Vial_Adenosine: ACME_Vial_Epinephrine {
        picture = QPATHTOF(ui\vial_adenosine_ca.paa);
        displayName = CSTRING(Vial_Adenosine);
        descriptionShort = CSTRING(Vial_Adenosine_Desc);
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 0.11;
        };
    };

    class ACME_Vial_Morphine: ACME_Vial_Epinephrine {
        picture = QPATHTOF(ui\vial_morphine_ca.paa);
        displayName = CSTRING(Vial_Morphine);
        descriptionShort = CSTRING(Vial_Morphine_Desc);
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 0.11;
        };
    };

    class ACME_Vial_Ketamine: ACME_Vial_Epinephrine {
        picture = QPATHTOF(ui\vial_ketamine_ca.paa);
        displayName = CSTRING(Vial_Ketamine);
        descriptionShort = CSTRING(Vial_Ketamine_Desc);
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 0.5;
        };
    };

    class ACME_Vial_Lidocaine: ACME_Vial_Epinephrine {
        picture = QPATHTOF(ui\vial_lidocaine_ca.paa);
        displayName = CSTRING(Vial_Lidocaine);
        descriptionShort = CSTRING(Vial_Lidocaine_Desc);
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 0.3;
        };
    };

    class ACME_Vial_TXA: ACME_Vial_Epinephrine {
        picture = QPATHTOF(ui\vial_txa_ca.paa);
        displayName = CSTRING(Vial_TXA);
        descriptionShort = CSTRING(Vial_TXA_Desc);
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 0.5;
        };
    };

    class ACME_Vial_Amiodarone: ACME_Vial_Epinephrine {
        picture = QPATHTOF(ui\vial_amiodarone_ca.paa);
        displayName = CSTRING(Vial_Amiodarone);
        descriptionShort = CSTRING(Vial_Amiodarone_Desc);
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 0.3;
        };
    };

    class ACME_Vial_Atropine: ACME_Vial_Epinephrine {
        picture = QPATHTOF(ui\vial_atropine_ca.paa);
        displayName = CSTRING(Vial_Atropine);
        descriptionShort = CSTRING(Vial_Atropine_Desc);
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 0.11;
        };
    };

    class ACME_Vial_Fentanyl: ACME_Vial_Epinephrine {
        picture = QPATHTOF(ui\vial_fentanyl_ca.paa);
        displayName = CSTRING(Vial_Fentanyl);
        descriptionShort = CSTRING(Vial_Fentanyl_Desc);
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 0.5;
        };
    };

    class ACME_Vial_Ondansetron: ACME_Vial_Epinephrine {
        picture = QPATHTOF(ui\vial_ondansetron_ca.paa);
        displayName = CSTRING(Vial_Ondansetron);
        descriptionShort = CSTRING(Vial_Ondansetron_Desc);
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 0.11;
        };
    };

    class ACME_Vial_CalciumChloride: ACME_Vial_Epinephrine {
        picture = QPATHTOF(ui\vial_calciumchloride_ca.paa);
        displayName = CSTRING(Vial_CalciumChloride);
        descriptionShort = CSTRING(Vial_CalciumChloride_Desc);
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 0.5;
        };
    };

    class ACME_Vial_Ertapenem: ACME_Vial_Epinephrine {
        picture = QPATHTOF(ui\vial_ertapenem_ca.paa);
        displayName = CSTRING(Vial_Ertapenem);
        descriptionShort = CSTRING(Vial_Ertapenem_Desc);
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 0.3;
        };
    };

    class ACME_Vial_Esmolol: ACME_Vial_Epinephrine {
        picture = QPATHTOF(ui\vial_esmolol_ca.paa);
        displayName = CSTRING(Vial_Esmolol);
        descriptionShort = CSTRING(Vial_Esmolol_Desc);
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 0.5;
        };
    };

    class ACME_Spray_Naloxone: ACME_Vial_Epinephrine {
        picture = QPATHTOF(ui\spray_naloxone_ca.paa);
        displayName = CSTRING(Spray_Naloxone);
        descriptionShort = CSTRING(Spray_Naloxone_Desc);
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 0.5;
        };
        ACM_isVial = 0;
    };

    class ACME_Lozenge_Fentanyl: ACME_Vial_Epinephrine {
        picture = QPATHTOF(ui\lozenge_fentanyl_ca.paa);
        displayName = CSTRING(Lozenge_Fentanyl);
        descriptionShort = CSTRING(Lozenge_Fentanyl_Desc);
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 0.2;
        };
        ACM_isVial = 0;
    };

    class ACME_Ampule_Dimercaprol: ACME_Vial_Epinephrine {
        picture = QPATHTOF(ui\ampule_dimercaprol_ca.paa);
        displayName = CSTRING(Ampule_Dimercaprol);
        descriptionShort = CSTRING(Ampule_Dimercaprol_Desc);
        scope = 1;
    };

    class ACME_Paracetamol_SinglePack: ACME_Spray_Naloxone {
        scope = 1;
        picture = QPATHTOF(ui\paracetamol_singlepack_ca.paa);
        displayName = CSTRING(Paracetamol_SinglePack);
        descriptionShort = CSTRING(Paracetamol_Desc);
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 0.03;
        };
    };

    class ACME_FieldBloodTransfusionKit_500: ACE_ItemCore {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        picture = QPATHTOF(ui\fieldBloodTransfusionKit_ca.paa);
        displayName = __EVAL(call compile QUOTE(format [ARR_2('%1 (500ml)',C_LLSTRING(FieldBloodTransfusionKit))]));
        shortName = __EVAL(call compile QUOTE(format [ARR_2('%1 (500ml)',C_LLSTRING(FieldBloodTransfusionKit_Short))]));
        descriptionShort = CSTRING(FieldBloodTransfusionKit_Desc);
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 12;
        };
    };

    class ACME_FieldBloodTransfusionKit_250: ACME_FieldBloodTransfusionKit_500 {
        displayName = __EVAL(call compile QUOTE(format [ARR_2('%1 (250ml)',C_LLSTRING(FieldBloodTransfusionKit))]));
        shortName = __EVAL(call compile QUOTE(format [ARR_2('%1 (250ml)',C_LLSTRING(FieldBloodTransfusionKit_Short))]));
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 9;
        };
    };

    class ACE_adenosine: ACE_ItemCore {
        scope = 1;
    };

    class ACE_morphine: ACE_ItemCore {
        picture = QPATHTOEF(core,ui\override\morphine_ca.paa);
    };

    #include "CfgWeapons_Blood.hpp"
};
