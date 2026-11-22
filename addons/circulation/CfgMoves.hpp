class CfgMovesBasic {
    class Default;
};

class CfgMovesMaleSdr: CfgMovesBasic {
    class States {
        //class AinvPknlMstpSnonWnonDr_medic0;
        class AmovPknlMstpSnonWnonDnon;
        class ACM_CPR: Default {
            file = "a3\anims_f\data\anim\sdr\inj\healing\ainvpknlmstpsnonwnondr_medic0.rtm";
            speed = 0.11;
            looped = 1;
            disableWeapons = 1;
            disableWeaponsLong = 1;
            showWeaponAim = 0;
            canPullTrigger = 0;
            duty = 0.2;
            limitGunMovement = 0;
            aiming = "empty";
            aimingBody = "empty";
            ConnectFrom[] = {
                "ACM_CPR",
                0.1
            };
            //ConnectAs = "";
            ConnectTo[] = {
                "ACM_CPR", 0.1,
                "AinvPknlMstpSnonWnonDnon_medicEnd", 0.1,
                "AmovPknlMstpSnonWnonDnon", 0.1
            };
            forceAim = 1;
            //InterpolateFrom[] = {};
            //InterpolateWith[] = {};
            InterpolateTo[]=
            {
                "ACM_CPR", 0.1,
                "AinvPknlMstpSnonWnonDnon_medicEnd", 0.1,
                "AmovPknlMstpSnonWnonDnon", 0.1,
                "Unconscious",
                0.02
            };
        };
        // B373: authored chest compressions (side position). The provider kneels on both knees beside the
        // chest; the sternum is 0.733 m in front of the unit and 0.021 m to its right (fnc_cprSpot).
        // Every state is entered with switchMove by fnc_beginCPR, so the graph below is a courtesy.
        class ACME_CPR_Base: Default {
            disableWeapons = 1;
            disableWeaponsLong = 1;
            showWeaponAim = 0;
            canPullTrigger = 0;
            duty = 0.2;
            limitGunMovement = 0;
            aiming = "empty";
            aimingBody = "empty";
            forceAim = 1;
        };
        // Entry: unarmed kneel to both knees, hands to the sternum. 37 frames, 1.2 s.
        class ACME_CPR_In: ACME_CPR_Base {
            file = QPATHTO_T(anim\acme_cpr_in.rtm);
            speed = 0.83333;
            looped = 0;
            ConnectFrom[] = {"AmovPknlMstpSnonWnonDnon", 0.1};
            InterpolateFrom[] = {"AmovPknlMstpSnonWnonDnon", 0.1};
            ConnectTo[] = {"ACME_CPR", 0.02};
            InterpolateTo[] = {"ACME_CPR", 0.02, "Unconscious", 0.02};
        };
        class ACME_CPR_In_L: ACME_CPR_In {
            ConnectTo[] = {"ACME_CPR_L", 0.02};
            InterpolateTo[] = {"ACME_CPR_L", 0.02, "Unconscious", 0.02};
        };
        // Loop: 120 compressions in 67.0857 s (2461 frames). First frame = last frame.
        class ACME_CPR: ACME_CPR_Base {
            file = QPATHTO_T(anim\acme_cpr_loop.rtm);
            speed = 0.0149063;
            looped = 1;
            ConnectFrom[] = {"ACME_CPR_In", 0.02, "ACME_CPR_Hold", 0.02, "ACME_CPR", 0.02};
            InterpolateFrom[] = {"ACME_CPR_In", 0.02, "ACME_CPR_Hold", 0.02};
            ConnectTo[] = {"ACME_CPR", 0.02, "ACME_CPR_Hold", 0.02, "ACME_CPR_Out", 0.02};
            InterpolateTo[] = {"ACME_CPR_Hold", 0.02, "ACME_CPR_Out", 0.02, "Unconscious", 0.02};
        };
        // The same loop with the looks to the casualty's face to the right (head to the right of the provider).
        class ACME_CPR_L: ACME_CPR {
            file = QPATHTO_T(anim\acme_cpr_loop_l.rtm);
            ConnectFrom[] = {"ACME_CPR_In_L", 0.02, "ACME_CPR_Hold", 0.02, "ACME_CPR_L", 0.02};
            InterpolateFrom[] = {"ACME_CPR_In_L", 0.02, "ACME_CPR_Hold", 0.02};
            ConnectTo[] = {"ACME_CPR_L", 0.02, "ACME_CPR_Hold", 0.02, "ACME_CPR_Out", 0.02};
            InterpolateTo[] = {"ACME_CPR_Hold", 0.02, "ACME_CPR_Out", 0.02, "Unconscious", 0.02};
        };
        // Pause: frame 0 of the loop (hands on the sternum, full recoil), held by a speed of zero.
        class ACME_CPR_Hold: ACME_CPR {
            speed = 0;
            looped = 1;
            ConnectFrom[] = {"ACME_CPR", 0.02, "ACME_CPR_L", 0.02, "ACME_CPR_In", 0.02, "ACME_CPR_In_L", 0.02};
            InterpolateFrom[] = {"ACME_CPR", 0.02, "ACME_CPR_L", 0.02, "ACME_CPR_In", 0.02, "ACME_CPR_In_L", 0.02};
            ConnectTo[] = {"ACME_CPR", 0.02, "ACME_CPR_L", 0.02, "ACME_CPR_Out", 0.02};
            InterpolateTo[] = {"ACME_CPR", 0.02, "ACME_CPR_L", 0.02, "ACME_CPR_Out", 0.02, "Unconscious", 0.02};
        };
        // Exit: the entry in reverse. Ends on the unarmed kneel.
        class ACME_CPR_Out: ACME_CPR_Base {
            file = QPATHTO_T(anim\acme_cpr_out.rtm);
            speed = 0.83333;
            looped = 0;
            ConnectFrom[] = {"ACME_CPR", 0.02, "ACME_CPR_L", 0.02, "ACME_CPR_Hold", 0.02};
            InterpolateFrom[] = {"ACME_CPR", 0.02, "ACME_CPR_L", 0.02, "ACME_CPR_Hold", 0.02};
            ConnectTo[] = {"AmovPknlMstpSnonWnonDnon", 0.1};
            // Not the kneel: a queued kneel would blend in at once and the exit would never be seen (measured in game).
            InterpolateTo[] = {"Unconscious", 0.02};
        };
        // The same for a casualty on the Talon II, whose bed is 0.148 m up: the provider kneels more upright and the
        // hands are that much higher over the same place (tools/build_cpr_raised.py; fnc_cprSpot chooses these).
        // ("there needs to be a small adjusted version for doing CPR on the TALON II litter", 2026-11-21)
        class ACME_CPR_T_In: ACME_CPR_In {
            file = QPATHTO_T(anim\acme_cpr_in_t.rtm);
            ConnectTo[] = {"ACME_CPR_T", 0.02};
            InterpolateTo[] = {"ACME_CPR_T", 0.02, "Unconscious", 0.02};
        };
        class ACME_CPR_T_In_L: ACME_CPR_T_In {
            ConnectTo[] = {"ACME_CPR_T_L", 0.02};
            InterpolateTo[] = {"ACME_CPR_T_L", 0.02, "Unconscious", 0.02};
        };
        class ACME_CPR_T: ACME_CPR {
            file = QPATHTO_T(anim\acme_cpr_loop_t.rtm);
            ConnectFrom[] = {"ACME_CPR_T_In", 0.02, "ACME_CPR_T_Hold", 0.02, "ACME_CPR_T", 0.02};
            InterpolateFrom[] = {"ACME_CPR_T_In", 0.02, "ACME_CPR_T_Hold", 0.02};
            ConnectTo[] = {"ACME_CPR_T", 0.02, "ACME_CPR_T_Hold", 0.02, "ACME_CPR_T_Out", 0.02};
            InterpolateTo[] = {"ACME_CPR_T_Hold", 0.02, "ACME_CPR_T_Out", 0.02, "Unconscious", 0.02};
        };
        class ACME_CPR_T_L: ACME_CPR_T {
            file = QPATHTO_T(anim\acme_cpr_loop_l_t.rtm);
            ConnectFrom[] = {"ACME_CPR_T_In_L", 0.02, "ACME_CPR_T_Hold", 0.02, "ACME_CPR_T_L", 0.02};
            InterpolateFrom[] = {"ACME_CPR_T_In_L", 0.02, "ACME_CPR_T_Hold", 0.02};
            ConnectTo[] = {"ACME_CPR_T_L", 0.02, "ACME_CPR_T_Hold", 0.02, "ACME_CPR_T_Out", 0.02};
            InterpolateTo[] = {"ACME_CPR_T_Hold", 0.02, "ACME_CPR_T_Out", 0.02, "Unconscious", 0.02};
        };
        class ACME_CPR_T_Hold: ACME_CPR_T {
            speed = 0;
            looped = 1;
            ConnectFrom[] = {"ACME_CPR_T", 0.02, "ACME_CPR_T_L", 0.02, "ACME_CPR_T_In", 0.02, "ACME_CPR_T_In_L", 0.02};
            InterpolateFrom[] = {"ACME_CPR_T", 0.02, "ACME_CPR_T_L", 0.02, "ACME_CPR_T_In", 0.02, "ACME_CPR_T_In_L", 0.02};
            ConnectTo[] = {"ACME_CPR_T", 0.02, "ACME_CPR_T_L", 0.02, "ACME_CPR_T_Out", 0.02};
            InterpolateTo[] = {"ACME_CPR_T", 0.02, "ACME_CPR_T_L", 0.02, "ACME_CPR_T_Out", 0.02, "Unconscious", 0.02};
        };
        class ACME_CPR_T_Out: ACME_CPR_Out {
            file = QPATHTO_T(anim\acme_cpr_out_t.rtm);
            ConnectFrom[] = {"ACME_CPR_T", 0.02, "ACME_CPR_T_L", 0.02, "ACME_CPR_T_Hold", 0.02};
            InterpolateFrom[] = {"ACME_CPR_T", 0.02, "ACME_CPR_T_L", 0.02, "ACME_CPR_T_Hold", 0.02};
        };
        class ACM_CPR_Stop: Default {
            file = QPATHTO_T(anim\ACM_CPR_Stop.rtm);
            speed = -100;
            looped = 1;
            disableWeapons = 1;
            disableWeaponsLong = 1;
            showWeaponAim = 0;
            canPullTrigger = 0;
            duty = 0.2;
            limitGunMovement = 0;
            aiming = "empty";
            aimingBody = "empty";
            ConnectFrom[] = {
                "ACM_CPR",
                0.1
            };
            //ConnectAs = "";
            ConnectTo[] = {
                "ACM_CPR", 0.1,
                "AinvPknlMstpSnonWnonDnon_medicEnd", 0.1,
                "AmovPknlMstpSnonWnonDnon", 0.1
            };
            forceAim = 1;
            //InterpolateFrom[] = {};
            //InterpolateWith[] = {};
            InterpolateTo[]=
            {
                "ACM_CPR", 0.1,
                "AinvPknlMstpSnonWnonDnon_medicEnd", 0.1,
                "AmovPknlMstpSnonWnonDnon", 0.1,
                "Unconscious",
                0.02
            };
        };
    };
};
