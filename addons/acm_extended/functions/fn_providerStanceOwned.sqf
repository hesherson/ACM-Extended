/* Return true when another live provider-side controller currently owns stance/animation.
 * This is used only by delayed cleanup callbacks. A callback from an ended action must never release setUnitPos
 * underneath a newer treatment, Direct Pressure hold, Hang Bag, CPR, medical-menu crouch or head-position sequence.
 * Clinical state is deliberately not inferred from life state; the provider being alive is checked by the caller. */
params [["_unit", objNull, [objNull]]];
if (isNull _unit) exitWith {false};

if ((_unit getVariable ["ACME_treatmentPoseState", []]) isNotEqualTo []) exitWith {true};
if (_unit getVariable ["ACME_treatmentPreflightActive", false]) exitWith {true};
if (_unit getVariable ["ACME_chestAccessPreflightActive", false]) exitWith {true};
if ((_unit getVariable ["ACME_chestAccessProvider", []]) isNotEqualTo []) exitWith {true};
if ((_unit getVariable ["ace_medical_treatment_endInAnim", ""]) != "") exitWith {true};
if (_unit getVariable ["ACME_rollProviderActive", false]) exitWith {true};
if (_unit getVariable ["ACME_headElev_seqActive", false]) exitWith {true};
if ((_unit getVariable ["ACME_menuPose", []]) isNotEqualTo []) exitWith {true};
if (_unit getVariable ["ACME_hang_Raising", false]) exitWith {true};
if (_unit getVariable ["ACME_hang_Active", false]) exitWith {true};
if (_unit getVariable ["ACME_DP_InPose", false]) exitWith {true};
if (_unit getVariable ["ACME_DP_TreatmentBusy", false]) exitWith {true};
if (_unit getVariable ["ACM_circulation_isPerformingCPR", false]) exitWith {true};

// Continuous actions are client-owned mission state (BVM, stethoscope, etc.), so only read it for the local player.
if (hasInterface && {!isNil "ACE_player"} && {_unit isEqualTo ACE_player}
    && {missionNamespace getVariable ["ACM_core_ContinuousAction_Active", false]}) exitWith {true};

false
