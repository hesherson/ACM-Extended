// One animation-only rate for preparation, carrier handling, rolls and their exits.
// Clinical timers and frozen hold durations remain wall-clock seconds.
private _rate = missionNamespace getVariable ["ACME_choreographyAnimSpeed", 1.5];
if !(_rate isEqualType 0 && {finite _rate} && {_rate >= 1} && {_rate <= 3}) then {_rate = 1.5;};
_rate
