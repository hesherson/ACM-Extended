// ACM Extended fork-native implementation of ACM_airway_fnc_getAirwayState.
// it is a faithful, de-macroed copy of ACM's original with one behavioral change for basic airway adjuncts: an
// NPA or OPA now protects only a mild airway collapse. once the collapse is moderate or severe, where
// ACM_airway_AirwayCollapse_State is 2 or above, the soft-tissue and tongue obstruction overwhelms the adjunct
// and it confers no benefit, so the airway scores as if no adjunct were fitted.
// secretions, meaning vomit and blood, still obstruct the airway whatever the adjunct, exactly as in ACM: an OPA
// or NPA does not manage secretions, which needs suction or a definitive airway. the SGA, the i-gel, the recovery
// position and the head-tilt keep ACM's stronger hold.
// in stock ACM an NPA or OPA only ever helped a patient with no collapse at all, so this makes the adjunct
// actually do its job on a developing mild collapse while staying useless once the airway is moderately or
// severely shut.
// _this is [_patient], and it returns the airway patency, 0 to 1.
params ["_patient"];

if (_patient getVariable ["ACM_airway_SurgicalAirway_State", false]) exitWith {
    [1, 0.75] select (_patient getVariable ["ACM_airway_SurgicalAirway_TubeUnSecure", false]);
};

// a cuffed ETT is a definitive airway, so it short-circuits everything below exactly as the surgical airway does.
// that is the entire clinical point of intubating someone: the inflated cuff sits below the cords and seals the
// trachea off from the pharynx, so vomit and secretions have nowhere to go. they pool above the cuff and get
// suctioned out, and they cannot reach the lungs and cannot obstruct the airway. a patient with a tube in can
// vomit as much as they like and still be ventilated, which is precisely why it is the airway you want on a
// casualty who cannot protect their own.
// ACM already grants this to the i-gel through its keepairwayintact rule, and to the cric on the line above. the
// ETT is our own addition, so nothing was granting it, and an intubated casualty could still be obstructed by
// vomit, blood or a collapse the tube physically holds open. fn_ettairwayprotect clears those states each tick,
// and that is reactive and leaves a window where the airway reads shut, so this closes the question outright.
// an unsecured tube scores lower rather than perfect, because the tube is in and not tied down, so it can migrate.
// this mirrors the unsecured handling of the surgical airway on the line above.
if (_patient getVariable ["ACME_ETT_Inserted", false]) exitWith {
    if (!(missionNamespace getVariable ["ACME_ett_protectsAirway", true])) then {
        1
    } else {
        [1, 0.9] select (_patient getVariable ["ACME_ETT_Unsecured", false]);
    };
};

if !(_patient getVariable ["ACE_isUnconscious", false]) exitWith { 1 };

private _state = 1;

private _airwayReflex = _patient getVariable ["ACM_airway_AirwayReflex_State", false];

if (((_patient getVariable ["ACM_airway_AirwayObstructionVomit_State", 0]) + (_patient getVariable ["ACM_airway_AirwayObstructionBlood_State", 0])) > 0) then {
    _state = 0;
} else {
    private _collapseRaw   = _patient getVariable ["ACM_airway_AirwayCollapse_State", 0];
    private _collapseState = 1 - (_collapseRaw / 3);
    private _airwayState    = [0.78, 0.88] select (_airwayReflex);

    private _airwayItemOral  = _patient getVariable ["ACM_airway_AirwayItem_Oral", ""];
    private _airwayItemNasal = _patient getVariable ["ACM_airway_AirwayItem_Nasal", ""];

    switch (true) do {
        case (_patient getVariable ["ACM_airway_RecoveryPosition_State", false]): {
            _state = _collapseState max 0.97;
        };
        case (_patient getVariable ["ACM_airway_HeadTilt_State", false]): {
            _state = _collapseState max 0.98;
        };
        case (_airwayItemOral == "SGA"): {
            _state = _collapseState max 0.99;
        };
        case (_airwayItemNasal == "NPA");
        case (_airwayItemOral == "OPA"): {
            // ACME: a basic adjunct only holds a mild collapse open. moderate or severe, at state 2 or above, defeats it.
            if (_collapseRaw <= 1) then {
                _state = _collapseState max 0.95;  // mild, or none: the adjunct keeps the airway patent.
            } else {
                _state = _airwayState min _collapseState;  // moderate or severe: the adjunct is overwhelmed and gives no benefit.
            };
        };
        default {
            _state = _airwayState min _collapseState;
        };
    };
};

// CBRN and burns own separate inflammation sources. Compose them here so neither subsystem
// can erase the other. A tracheal ETT/cric has already exited above and therefore bypasses this
// upper-airway edema; an i-gel remains supraglottic and does not.
private _airwayInflammation = (
    (_patient getVariable ["ACM_CBRN_AirwayInflammation", 0]) +
    (_patient getVariable ["ACM_burns_AirwayInflammation", 0])
) min 100;

if (_airwayInflammation > 10) then {
    if (_airwayInflammation >= 100) then {
        _state = 0;
    } else {
        _state = _state * (linearConversion [10, 100, _airwayInflammation, 1, 0.2, true]);
    };
};

_state
