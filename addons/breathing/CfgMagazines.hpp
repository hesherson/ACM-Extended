class CfgMagazines {
    class CA_Magazine;

    class ACM_OxygenTank_425: CA_Magazine {
        scope = 2;
        author = "Blue";
        picture = QPATHTOF(ui\oxygentank_ca.paa);
        displayName = CSTRING(OxygenTank_425);
        descriptionShort = CSTRING(OxygenTank_425_Desc);
        ACE_isMedicalItem = 1;
        ACE_asItem = 1;
        count = 283;
        // PR #35 sets empty cylinder tare to 85. Add ~0.608 kg for 425 L O2
        // (1.429 g/L at STP; one Arma mass unit is ~45.36 g).
        // Magazine ammo still represents oxygen charge, not physical item mass.
        mass = 98.4;
    };
};
