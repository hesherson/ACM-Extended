// This config accepts both item type numbers and item class names
// Item type numbers need the prefix ItemType_, so for example ItemType_401
// Class names need no special prefix
class ACEGVAR(medical,replacementItems) {
    DOUBLES(ItemType,TYPE_FIRST_AID_KIT)[] = {
        {"ACME_PressureBandage", 2},
        {"ACE_tourniquet", 1},
        {"ACME_ChestSeal", 1},
        {"ACME_NPA", 1},
        {"ACME_Paracetamol",1}
    };
    DOUBLES(ItemType,TYPE_MEDIKIT)[] = {
        {"ACME_PressureBandage", 3},
        {"ACME_ElasticWrap", 5},
        {"ACME_Vial_Morphine", 1},
        {"ACME_Syringe_5", 1},
        {"ACE_salineIV_250", 1},
        {"ACE_tourniquet", 1},
        {"ACME_SAMSplint", 2},
        {"ACME_ChestSeal", 1},
        {"ACME_NPA", 1},
        {"ACME_NCDKit", 1},
        {"ACME_SuctionBag", 1},
        {"ACME_IV_16g", 1}
    };
};
