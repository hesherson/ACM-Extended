class ACE_Medical_Injuries {
    class wounds {
        class ThermalBurn;
        class ChemicalBurn: ThermalBurn { // CBRN
            pain = 0.8;
        };
        class Burn1: ThermalBurn { bleeding = 0.002; pain = 0.45; };
        class Burn2: ThermalBurn { bleeding = 0.005; pain = 0.95; };
        class Burn3: ThermalBurn { bleeding = 0.003; pain = 0.70; };
    };

    class damageTypes {
        class slap {
            thresholds[] = {{0.05, 1}, {0.05, 0}};
            selectionSpecific = 1;
            class Contusion {
                weighting[] = {{0.35, 0}, {0.35, 1}};
            };
        };
        class incision {
            thresholds[] = {{0.1, 1}, {0.1, 0}};
            selectionSpecific = 1;
            class Cut {
                weighting[] = {{0.1, 1}, {0.1, 0}};
            };
        };
        class lewisiteburn { // CBRN
            thresholds[] = {{0, 1}};
            selectionSpecific = 0;
            noBlood = 1;
            class ChemicalBurn {
                weighting[] = {{0, 1}};
            };
        };
        class burn {
            thresholds[] = {{0, 1}};
            selectionSpecific = 0;
            noBlood = 1;
            class ThermalBurn { weighting[] = {{0, 0}}; };
            class Burn1 { weighting[] = {{0.30, 0}, {0.10, 1}}; };
            class Burn2 { weighting[] = {{0.80, 0}, {0.45, 1}, {0.12, 0}}; };
            class Burn3 { weighting[] = {{0.70, 1}, {0.40, 0}}; };
        };
    };
};
