class CfgWeapons {
    class ACE_ItemCore;
    class CBA_MiscItem_ItemInfo;

    class ACME_EyeCover: ACE_ItemCore {
        dlc = "ACM_Extended";
        scope = 2;
        author = "mavis";
        authors[] = {"MrAdrianPL", "Inferno"};
        displayName = CSTRING(EyeCover_Item);
        picture = QPATHTOF(ui\icon_eyeshield.paa);
        model = QPATHTOF(models\eyecovers\kat_eyecovers.p3d);
        descriptionShort = CSTRING(EyeCover_Desc);
        ACE_isMedicalItem = 1;
        class ItemInfo: CBA_MiscItem_ItemInfo {
            mass = 0.2;
        };
    };

    class NVGoggles;
    class ACME_EyeCover_Right: NVGoggles {
        dlc = "ACM_Extended";
        author = "mavis";
        authors[] = {"MrAdrianPL", "Inferno"};
        displayName = CSTRING(EyeCover_Right);
        scope = 2;
        scopeArsenal = 0;
        ace_nightvision_border = QPATHTOF(ui\RightEyeNVG.paa);
        modelOptics = "\A3\Weapons_F\empty.p3d";

        picture = QPATHTOF(ui\icon_eyeshield.paa);
        hiddenSelections[] = {"eye_l","eye_r"};
        hiddenSelectionsTextures[] = {"",QPATHTOF(models\eyecovers\camo1_ca.paa)};
        visionMode[] = {};
        class ItemInfo {
            type = 616;
            hiddenSelections[] = {"eye_l","eye_r"};
            uniformModel = QPATHTOF(models\eyecovers\kat_eyecovers.p3d);
            modelOff = QPATHTOF(models\eyecovers\kat_eyecovers.p3d);
            mass = 0.1;
        };
    };
    class ACME_EyeCover_Left: ACME_EyeCover_Right {
        displayName = CSTRING(EyeCover_Left);
        ace_nightvision_border = QPATHTOF(ui\LeftEyeNVG.paa);
        modelOptics = "\A3\Weapons_F\empty.p3d";
        hiddenSelections[] = {"eye_l","eye_r"};
        hiddenSelectionsTextures[] = {QPATHTOF(models\eyecovers\camo1_ca.paa),""};
    };
};
