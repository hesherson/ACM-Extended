/* B176: is this casualty independently upright so provider theatre should target a person in front of the medic?
   Ambulatory presentation applies to alive, conscious casualties who are independently STANDING or CROUCHED.
   PRONE deliberately falls back to the normal downed-target provider animation family, but patient animation
   remains excluded elsewhere because a conscious casualty still owns their own body. */
params [["_patient", objNull, [objNull]]];
if (isNull _patient || {!alive _patient} || {!(_patient isKindOf "CAManBase")}) exitWith {false};
if (_patient getVariable ["ACE_isUnconscious", false]) exitWith {false};
if (_patient getVariable ["ace_medical_unconscious", false]) exitWith {false};
if (!isNull objectParent _patient) exitWith {false};
if !((stance _patient) in ["STAND", "CROUCH"]) exitWith {false};
if (_patient getVariable ["ACME_headElevated", false]) exitWith {false};
if (_patient getVariable ["ACME_headElev_Suspended", false]) exitWith {false};

private _anim = toLowerANSI animationState _patient;
if ((_anim find "lying") >= 0
    || {(_anim find "unconscious") >= 0}
    || {(_anim find "acts_") == 0}
    || {(_anim find "ainvppne") == 0}
    || {(_anim find "amovppne") == 0}) exitWith {false};

true
