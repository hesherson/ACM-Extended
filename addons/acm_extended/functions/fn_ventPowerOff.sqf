// Input cannot outlive its captured patient/device panel.
if !([] call ACME_fnc_ventPanelContext) exitWith {};
// power the ventilator down. it is a held MMB for 4 seconds, exactly like the real device.
// a ventilator does not have an off button. powering one down while a patient is on it
// kills them, so every real machine makes it a held action: long enough that you cannot do it by accident, and
// long enough that you have time to change your mind while the bar fills.
// so the mod does the same, and it makes the consequence real: powering off a patient who is dependent on the vent
// stops their ventilation, and they will start dying, and the machine will not save you from yourself. it warns
// you loudly, and then it does what you told it to.
// this function no longer powers the vent off. it starts the shutdown sequence, which is the same boot screen the
// device shows on the way up, a white window with the logo, at half the duration and with POWERING OFF... across
// the top. the machine actually stops in fn_ventpowerdown, when the sequence completes.
// doing it this way rather than simply fading out matters: a device that takes visible time to shut down is a
// device that is telling you it is shutting down. it is the last chance to see what you have done.
if (!hasInterface) exitWith {};

private _tgt = uiNamespace getVariable ["ACME_vent_target", objNull];
if (isNull _tgt) exitWith {};

private _dur = (uiNamespace getVariable ["ACME_vent_bootDur", 2.4]) * 0.5;  // half the boot, per the brief.
uiNamespace setVariable ["ACME_vent_shutT0", diag_tickTime];
uiNamespace setVariable ["ACME_vent_shutDur", _dur];
playSound "ACME_VentClick";
