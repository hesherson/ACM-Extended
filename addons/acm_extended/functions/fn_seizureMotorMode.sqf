/* Presentation only. An established arrest never acquires a fresh 20-second convulsion window
   on owner migration or when a monitor is opened. Non-arrest seizures retain ordinary convulsions. */
params ["_patient"];
if !(_patient getVariable ["ace_medical_inCardiacArrest", false]) exitWith {"full"};
private _onset = _patient getVariable ["ACME_seizure_arrestStartedAt", -1];
if (_onset isEqualType 0 && {_onset >= 0} && {(serverTime - _onset) < 20}) exitWith {"full"};
"jerks"
