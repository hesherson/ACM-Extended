// how much colder the air actually feels to a casualty strapped in the back of an aircraft.
// it returns a temperature drop in degrees c, to be subtracted from the ambient. two things do it.
// altitude: the air genuinely is colder up there, about 6.5 c per 1000 m. climb to 3000 ft and you have taken
// roughly 6 c off the cabin before anything else happens.
// wind: this is the one that kills. a casualty in an open-door helicopter is not sitting in still cold air, they
// are being blasted with it. rotor downwash does it on the ground and forward airspeed does it far harder in
// flight. a stripped, wet, shocked patient loses heat to moving air at a rate that has nothing to do with the
// thermometer reading.
// this matters because hypothermia is the third leg of the lethal triad and we already model that: cold blood does
// not clot. so the flight itself, the thing that is supposed to save them, is actively killing their clotting
// cascade the whole way, and the fix is stupidly simple and constantly forgotten: wrap them. an HPMK on before
// you launch is worth more than most of what happens after.
// call it as [_unit] call ACME_fnc_flightChill, which returns a number, the degrees c to subtract from
// ambient.
params ["_unit"];
if (isNull _unit) exitWith {0};
if (!(missionNamespace getVariable ["ACME_sys_flight", true])
    || {!(missionNamespace getVariable ["ACME_flightChill_enable", true])}) exitWith {0};

private _veh = vehicle _unit;
if (_veh == _unit) exitWith {0};  // not in a vehicle, so the ordinary ambient applies.

private _drop = 0;

// wind: airflow over an exposed casualty.
// how open the cabin is comes from the actual door animations of the vehicle, through fn_vehicleopenness, rather
// than being assumed. the previous version simply treated every aircraft as open, which happened to be right for
// an mh-60 with the doors slid back and wrong for everything else: a buttoned-up ghost hawk should not be
// freezing anyone, and a doorless hummingbird should be freezing them whether it is moving or not.
// openness is a fraction, because it is not binary: one door back is not the same as a ramp down.
private _open = [_veh] call ACME_fnc_vehicleOpenness;

// turned out of a hatch, you are in the airstream whatever the doors are doing.
if (isTurnedOut _unit) then { _open = _open max 0.6; };

if (_open > 0.02) then {
    private _spd = abs (speed _veh);  // km/h.
    // rotor downwash alone, sitting on the deck with the engine running.
    private _rotor = if ((_veh isKindOf "Air") && {isEngineOn _veh}) then {
        missionNamespace getVariable ["ACME_flightChill_rotorC", 4]
    } else {0};
    // forward airspeed. windchill is steep at first and then flattens, like the real curve.
    private _wind = (sqrt (_spd / 200)) * (missionNamespace getVariable ["ACME_flightChill_windMaxC", 14]);
    _drop = _drop + ((_rotor max _wind) * _open);  // scaled by how open the cabin actually is.
};

// altitude: the air is simply colder up there.
// it only counts what has been gained over the ground, so a mission on a high plateau is not double-penalised,
// because the ambient model has already taken the terrain height into account.
private _lapse = missionNamespace getVariable ["ACME_ambient_lapsePer1000m", 6.5];
// ATL measures climb above terrain directly. Subtracting AGLS from ASL instead
// measures terrain elevation, suppressing flight cooling over sea-level ground.
private _agl = ((getPosATL _veh) select 2) max 0;
_drop = _drop + ((_agl / 1000) * _lapse);

// a wrapped casualty is protected, which is the entire point of wrapping them.
// note that this originally read a variable called acme_hpmk_wrapped, which nothing in the mod ever sets. it would
// have silently returned false forever, the HPMK would have protected nobody, and the one intervention this
// whole mechanic is trying to teach would have done nothing at all, while looking perfectly fine in the code.
// the real state lives in ACME_hpmk_on, which is whether it is applied, and ACME_hpmk_state, which is wrapped or
// exposed, so a casualty whose blanket has been opened up to work on them is correctly exposed to the cold
// again.
private _hpmkOn = _unit getVariable ["ACME_hpmk_on", false];
private _hpmkState = _unit getVariable ["ACME_hpmk_state", "wrapped"];
if (_hpmkOn && {_hpmkState == "wrapped"}) then {
    _drop = _drop * (missionNamespace getVariable ["ACME_flightChill_hpmkFactor", 0.15]);
};

_drop max 0
