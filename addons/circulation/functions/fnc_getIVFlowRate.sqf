// a compile-time CfgFunctions override of acm_circulation_fnc_getivflowrate. ACM compiles it final, so the previous
// runtime reassignment was silently ignored. it is a full de-macroed replacement of ACM's flow table plus the
// ACME rule that an 18g catheter, ACME gauge type 5, which is a smaller bore than a 16g, flows slower. re-pull
// from the ACM source if ACM changes the gauge multipliers.
// the base rate, iv_change_per_second, is 4.1667 ml/s, from ACE medical_engine.
// the ACM gauge types are 1 for 16g, 2 for 14g, 3 for io-ez and 4 for io-fast. ACME adds 5 for 18g and
// 6 for 20g.
// call it as [_patient, _partIndex, _iv, _accessSite] call acm_circulation_fnc_getivflowrate.
// Fifth argument: -2 = legacy site cache, -1 = physical wide-open access,
// >=0 = the exact bag's requested mL/s. Native four-argument calls stay compatible.
// Sixth argument is the physical bag identity; unspecific native queries have no cuff boost.
params ["_patient", "_partIndex", "_iv", "_accessSite", ["_bagClamp", -2], ["_bagId", ""]];
if (_partIndex < 0 || {_partIndex > 5} || {_iv && {!(_accessSite in [0,1,2])}}) exitWith {0};
private _acmeBinding = "NA4:getIVFlowRate";
if ([_patient, _partIndex] call ACME_fnc_aajtOccludes) exitWith {0};

// A conventional tourniquet also removes usable venous return from an access distal to it. IVs are always
// tourniquet-blocked on their limb. Tibial IOs (left/right leg) are likewise blocked: bone access does not make
// fluid bypass the limb's occluded venous return. Humeral IO remains independent because it is proximal to the
// ordinary arm-tourniquet model used here.
private _tqs = _patient getVariable ["ace_medical_tourniquets", [0,0,0,0,0,0]];
private _tqOnPart = (_tqs param [_partIndex,0,[0]]) > 0;
if (_tqOnPart && {_iv || {_partIndex in [4,5]}}) exitWith {0};


// get_io and get_iv, de-macroed. the defaults are all-0 for io, and 6 parts of [0,0,0] for iv.
private _ioP = _patient getVariable ["ACM_circulation_IO_Placement", [0,0,0,0,0,0]];
private _ivP = _patient getVariable ["ACM_circulation_IV_Placement", [[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0]]];
private _type = if (_iv) then {(_ivP select _partIndex) select _accessSite} else {_ioP select _partIndex};

if (_type <= 0) exitWith {0};

// the constricting band. a band tight enough to raise a vein is tight enough to stop the line running into it,
// so nothing flows until it comes off. it applies to a real iv only, because an io goes into bone below the
// band and is not occluded by it.
// fn_ivminigamebandflag publishes this per body part when the band goes on and off.
if (_iv && {_patient getVariable [format ["ACME_IV_BandOnPart_%1", _partIndex], false]}) exitWith { 0 };

private _base = 4.1667;  // iv_change_per_second, in ml/s.

private _rate = switch (_type) do {
    case 2: {_base * 1.5};  // 14g, from acm_iv_14g_m.
    case 4: {_base * 0.65};  // io-fast, from ACM_IO_FAST1_M.
    case 3: {_base * 0.55};  // io-ez, from ACM_IO_EZ_M.
    // the ACME 18g: a smaller bore than a 16g, so a scaled-down flow. it is tunable and defaults to 0.55.
    case 5: {_base * (missionNamespace getVariable ["ACME_iv18gFlowFactor", 0.55])};
    // the ACME 20g: smaller again. a 20g runs at roughly a third of a 16g in real cannula flow tables, so the
    // default is 0.35. it is tunable for the same reason the 18g is.
    case 6: {_base * (missionNamespace getVariable ["ACME_iv20gFlowFactor", 0.35])};
    default {_base};  // 16g, or unknown.
};

// the hang bag: holding the bag aloft raises the hydrostatic column, which gives a gravity-assisted higher flow.
// ACME_hang_flowMult is set on the patient while a medic holds the bag up, and it defaults to 1, meaning no
// change.
// the roller-clamp throttle. the clamp sets an absolute flow rate in ml/s for this access site now, rather than a
// fraction of the very fast gravity rate, which is about 4.17 ml/s, or 250 ml/min. so the bag drains at exactly
// the dialled drops per minute instead of about 10 times faster. handleinfusions publishes
// ACME_clampRate_<part>_<iv>_<site>, and we clamp it to the physical maximum of the gauge and apply the hang, or
// gravity, boost, which only raises the ceiling, so a titrated drip below the cap is unaffected. with no tracked
// infusion here, where the rate is below 0, it is wide open.
// ACM stays the single writer of the bag volume, so the displayed amount does not ping-pong.
private _hang = _patient getVariable ["ACME_hang_flowMult", 1];
private _pressure = 1;
private _cuff = (_patient getVariable ["ACME_piCuffs", createHashMap]) getOrDefault [_bagId, []];
if (_bagId != "" && {!(_cuff isEqualTo [])}) then {
    _cuff params [["_at", 0], ["_p0", 1]];
    private _half = (missionNamespace getVariable ["ACME_pi_bleedHalfLifeSec", 150]) max 0.1;
    private _p = (_p0 * (2 ^ (-((CBA_missionTime - _at) max 0) / _half))) max 0 min 1;
    if (_p >= 0.08) then {_pressure = 1 + ((missionNamespace getVariable ["ACME_pressureInfuser_boost", 2.5]) - 1) * _p;};
};
private _baseCeil = _rate * _hang;  // the gauge, gravity and hand-squeeze ceiling, before the pressure infuser.
private _clampRate = if (_bagClamp == -2) then {
    _patient getVariable [format ["ACME_clampRate_%1_%2_%3", _partIndex, _iv, _accessSite], -1]
} else {_bagClamp};
// the pressure infuser, the rapid transfuser, forces fluid in faster than gravity allows, so it multiplies the
// delivered rate rather than only the ceiling. previously it only raised a ceiling the roller clamp already sat
// under, so min(clamp, boostedceil) just returned the clamp and the cuff did nothing on any throttled line, which
// is why it felt like it had no purpose. now the dialled rate, or a wide-open line, is forced in _pressure times
// faster while the cuff is on.
// this also means the volume, and therefore the citrate and hypocalcemia load and the cold-blood cooling, arrives
// faster: it is a real rapid-resuscitation tool with a cost rather than free speed. remove the cuff to return to
// the dialled rate.
private _flow = if (_clampRate >= 0) then { _clampRate min _baseCeil } else { _baseCeil };
_flow * _pressure
