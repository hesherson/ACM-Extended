// vomit dislodges an OPA.
// an oropharyngeal airway sits loose in the mouth, held only by the flange against the lips. it is not cuffed and
// it seals nothing. a casualty who vomits pushes it straight back out, which is exactly why an OPA does not
// protect an airway and an ETT does.
// ACM already encodes half of this: its vomit handler treats an SGA as keepAirwayIntact and leaves the airway
// alone, and an OPA gets no such protection, so the patient ends up obstructed with a useless piece of plastic
// still recorded as being in place.
// this watches the vomit obstruction level for any rise, whatever caused it, and drops the OPA when it happens. it
// is written as a watcher on the state rather than as a hook into the places that trigger vomiting, so it catches
// every source at once: our own gag-on-intubation, ACM's recurring vomit pfh, and anything added later. there is
// no way to trigger a vomit that this does not see.
// the i-gel is deliberately not removed. it is a supraglottic seal and ACM already treats it as protecting the
// airway through a vomit, so pulling it would contradict the parent mod. the NPA is left alone too, because it
// sits in the nose rather than in the path the vomit takes.
// call it as [_patient] call ACME_fnc_vomitDislodgeOPA.

params ["_patient"];
if (isNil "_patient" || {isNull _patient}) exitWith {};

// a tubed casualty cannot be obstructed at all, see the ETT branch in overrides/fn_getAirwayState, and in any case
// an OPA and an ETT can no longer coexist. there is nothing to do.
if (_patient getVariable ["ACME_ETT_Inserted", false]) exitWith {};

private _vomitNow  = _patient getVariable ["ACM_airway_AirwayObstructionVomit_State", 0];
private _vomitLast = _patient getVariable ["ACME_vomitOPA_lastState", -1];

// the first sight of this casualty: record where they are and do nothing. without this, a patient who is already
// obstructed when first seen would have an OPA torn out retroactively for a vomit that happened before we
// looked.
if (_vomitLast < 0) exitWith {
    _patient setVariable ["ACME_vomitOPA_lastState", _vomitNow, true];
};

if (_vomitNow <= _vomitLast) exitWith {
    // the level fell, from suctioning, or held. track it so the next genuine rise is detected from the new floor.
    if (_vomitNow != _vomitLast) then {
        _patient setVariable ["ACME_vomitOPA_lastState", _vomitNow, true];
    };
};

// a rise: the casualty just vomited.
_patient setVariable ["ACME_vomitOPA_lastState", _vomitNow, true];

if (((_patient getVariable ["ACM_airway_AirwayItem_Oral", ""]) isEqualTo "OPA")) then {
    [_patient, "", true] call ACM_airway_fnc_setOralAirwayItem;
    // hand the item back rather than deleting it. it is recoverable kit, and silently destroying a consumable of the
    // medic on an event they did not cause would be its own small injustice.
    private _near = _patient getVariable ["ACME_ETT_Medic", objNull];
    if (isNull _near) then { _near = _patient };
    if (local _near && {_near isKindOf "CAManBase"} && {alive _near}) then {
        [_near, "ACME_OPA"] call ace_common_fnc_addToInventory;
    };
    if (hasInterface && {!isNull ACE_player} && {(ACE_player distance _patient) < 12}) then {
        ["The OPA was expelled by the vomit.", 2] call ace_common_fnc_displayTextStructured;
    };
};
