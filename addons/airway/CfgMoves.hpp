class CfgMovesBasic {
    class Default;
};

class CfgMovesMaleSdr: CfgMovesBasic {
    class States {
        class DeadState;
        class ACM_RecoveryPosition: DeadState {
            aiming = "aimingNo";
            aimingBody = "aimingUpNo";
            head = "headNo";
            speed = 100;
            // B217: preserve the static RTM, but blend into it more slowly than Default (6).
            interpolationSpeed = 0.5;
            file = QPATHTO_T(anim\ACM_RecoveryPosition.rtm);
        };
    };
};
