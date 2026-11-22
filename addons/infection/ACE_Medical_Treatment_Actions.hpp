class ACEGVAR(medical_treatment,actions) {
    class CheckPulse;
    class Paracetamol;

    class Moxifloxacin: Paracetamol {
        displayName         = CSTRING(UseMoxifloxacin);
        displayNameProgress = CSTRING(UseMoxifloxacin_Progress);
        items[]             = {"ACME_Moxifloxacin_SinglePack","ACME_Moxifloxacin"};
        ACM_menuIcon        = "ACME_Paracetamol";
    };

    class CheckWound: CheckPulse {
        displayName         = CSTRING(CheckWound);
        displayNameProgress = CSTRING(CheckWound_Progress);
        category            = "examine";
        allowedSelections[] = {"Body","Head","LeftArm","RightArm","LeftLeg","RightLeg"};
        treatmentTime       = 5;
        medicRequired       = 1;
        condition           = QFUNC(canCheckWound);
        callbackSuccess     = QFUNC(checkWound);
    };
};
