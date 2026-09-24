// the local per-frame driver for the EMMA capnograph HUD.
// it supports two routes.
// 1. a medic-owned EMMA attached to the medic's own BVM, visible while that medic bags.
// 2. a patient-side EMMA attached to an i-gel or ET tube, visible to players within 5 m who last made patient contact.

// the system toggle, read live, so unticking capnography in addon options stops this system immediately and
// completely with no mission restart.
if !(missionNamespace getVariable ["ACME_sys_emma", true]) exitWith {};

private _player = ACE_player;
if (isNull _player) exitWith {};

private _layer = "ACME_EMMA" call BIS_fnc_rscLayer;
private _dlg = uiNamespace getVariable ["ACME_EMMA_DLG", displayNull];

private _hasOwnEmma = (([_player, "ACM_EMMA"] call ACME_fnc_itemCount) > 0);

// the BVM route stays tied to the medic's own inventory and device.
private _bvmAttached = _player getVariable ["ACME_emma_bvmAttached", false];
if (_bvmAttached && {!_hasOwnEmma}) then {
    _bvmAttached = false;
    [_player, "ACME_emma_bvmAttached", false] call ACME_fnc_setVarNet;
    _player setVariable ["ACME_emma_lastPatient", objNull];
    _player setVariable ["ACME_emma_lastBag", -1e9];
    _player setVariable ["ACME_emma_capPatient", objNull];
    _player setVariable ["ACME_emma_route", "none"];
};

// The shared patient-side i-gel / ETT route. last contact wins, so overlapping casualties cannot fight over the display.
private _igelPatient = objNull;
private _range = missionNamespace getVariable ["ACME_emma_igelRange", 5];
private _lastContact = _player getVariable ["ACME_emma_lastContactPatient", objNull];
// the same vehicle means in reach, and a full stop. do not measure a distance you cannot trust.
// two units riding in the same airframe have their world positions interpolated independently, so at 55 m/s the
// distance between them jitters by meters from frame to frame even though neither has moved an inch relative to
// the other. that was tripping the 5 m range gate on and off every few frames, which cut and re-raised the HUD
// layer, and that is the flashing you saw in flight. if you are both in the same vehicle, you are next to the
// patient, and there is nothing to measure.
private _sameVeh = {
    params ["_a", "_b"];
    private _va = vehicle _a;
    (!(_va isEqualTo _a)) && {_va isEqualTo (vehicle _b)}
};
if (!isNull _lastContact &&
    {([_player, _lastContact] call _sameVeh) || {(_player distance _lastContact) <= _range}} &&
    {_lastContact getVariable ["ACME_emma_igelAttached", false]} &&
    {([_lastContact] call ACME_fnc_emmaAirwayKind) != ""}) then {
    _igelPatient = _lastContact;
};

// the own-BVM route. it is only active if the player has attached their own EMMA to their own BVM.
private _bvmPatient = objNull;
if (_bvmAttached) then {
    // near the medic rather than the whole mission. see the note in fn_bvmventtick: bagging means being at the
    // casualty, so this is a superset of the old scan and costs a fraction of it at ten ticks a second.
    {
        if ((_x getVariable ["ACM_breathing_BVM_Medic", objNull]) isEqualTo _player) exitWith {
            _bvmPatient = _x;
        };
    } forEach (_player nearEntities ["CAManBase", 10]);

    // a fallback. if the per-patient bvm_medic scan missed, use the local current BVM target of the medic.
    if (isNull _bvmPatient) then {
        private _bt = missionNamespace getVariable ["ACM_breathing_BVMTarget", objNull];
        if (!isNull _bt &&
            {(_player getVariable ["ACM_breathing_isUsingBVM", false]) || {(_bt getVariable ["ACM_breathing_BVM_Medic", objNull]) isEqualTo _player}}) then {
            _bvmPatient = _bt;
        };
    };

    if (!isNull _bvmPatient) then {
        _player setVariable ["ACME_emma_lastPatient", _bvmPatient];
        _player setVariable ["ACME_emma_lastBag", CBA_missionTime];
    } else {
        private _hold = missionNamespace getVariable ["ACME_emma_holdSec", 2];
        private _lastPatient = _player getVariable ["ACME_emma_lastPatient", objNull];
        private _lastBag = _player getVariable ["ACME_emma_lastBag", -1e9];
        if (!isNull _lastPatient && {(CBA_missionTime - _lastBag) < _hold}) then {
            _bvmPatient = _lastPatient;
        };
    };
};

// route priority.
// if the medic has an EMMA attached to their own BVM, the HUD behaves exactly like the original BVM route, so it
// only shows while actively bagging or during the normal short BVM hold window.
// if the BVM route is not active, a patient-side i-gel EMMA can show for the last-contact patient.
private _patient = objNull;
private _route = "none";

if (_bvmAttached) then {
    if (!isNull _bvmPatient) then {
        _patient = _bvmPatient;
        _route = "bvm";
    };
} else {
    if (!isNull _igelPatient) then {
        _patient = _igelPatient;
        _route = "igel";
    };
};

if (missionNamespace getVariable ["ACME_debugEMMA", false]) then {
    private _lt = _player getVariable ["ACME_dbgEmmaT", 0];
    if ((diag_tickTime - _lt) > 2) then {
        _player setVariable ["ACME_dbgEmmaT", diag_tickTime];
    };
};

// no valid BVM EMMA and no patient-side i-gel EMMA target, so hide the HUD and reset the capture.
if (isNull _patient) exitWith {
    _player setVariable ["ACME_emma_capPatient", objNull];
    if (!isNull _dlg) then {
        _layer cutText ["", "PLAIN"];
        uiNamespace setVariable ["ACME_EMMA_DLG", displayNull];
    };
};

// bring the HUD up if it is not already loaded.
if (isNull _dlg) exitWith {
    _layer cutRsc ["ACME_EMMA_Display", "PLAIN", 1e11, false];
};

// readouts refresh every tick. a 1 hz throttle kept in uinamespace used to survive HUD rebuilds, so after any
// rebuild the freshly created controls sat on their "--" placeholder until the timer next fired, which is why
// the numbers mostly did not show. the values are already smoothed, so per-tick is stable and always
// current.
private _etco2raw = [_patient] call ACM_breathing_fnc_getEtCO2;
private _etco2val = if (_etco2raw isEqualType 0) then { _etco2raw } else { 0 };
// NA3: the shared getter already applies the ventilation model exactly once.
private _etco2 = round _etco2val;
private _rrRaw = _patient getVariable ["ACM_breathing_RespirationRate", 0];
private _rr = if (_rrRaw isEqualType 0) then { round _rrRaw } else { 0 };

// real-capnometer capture timing.
// a real EMMA must see exhalations before it can report. EtCO2 appears after the first detected breath and is
// then shown as a breath-to-breath average that refreshes on each breath. rr appears after the second breath,
// because an interval takes two breaths to measure, and refreshes each breath after. until those thresholds the
// fields read "--". breaths are detected by accumulating the breath phase from ACM's rr and counting a breath
// each time a full cycle elapses, so this tracks the real rate, the bagging rate included.
private _now = CBA_missionTime;
if ((_player getVariable ["ACME_emma_capPatient", objNull]) isNotEqualTo _patient) then {
    // a new patient under the EMMA of this medic restarts the capture from zero.
    _player setVariable ["ACME_emma_capPatient", _patient];
    _player setVariable ["ACME_emma_breaths", 0];
    _player setVariable ["ACME_emma_phase", 0];
    _player setVariable ["ACME_emma_etco2Hist", []];
    _player setVariable ["ACME_emma_etco2Disp", 0];
    _player setVariable ["ACME_emma_rrDisp", 0];
    _player setVariable ["ACME_emma_lastT", _now];
};

private _breaths = _player getVariable ["ACME_emma_breaths", 0];
private _phase   = _player getVariable ["ACME_emma_phase", 0];
private _hist    = _player getVariable ["ACME_emma_etco2Hist", []];
private _dt = ((_now - (_player getVariable ["ACME_emma_lastT", _now])) max 0) min 0.5;  // clamp lag spikes.
_player setVariable ["ACME_emma_lastT", _now];

private _capBreathing = (_rr >= 1) && {_etco2val > 0};  // the patient is actually exhaling CO2.
if (_capBreathing) then {
    private _period = 60 / ((_rr max 4) min 60);  // seconds per breath.
    _phase = _phase + (_dt / _period);
    if (_phase >= 1) then {  // a breath just completed.
        _phase = _phase - 1;
        _breaths = _breaths + 1;
        _hist pushBack _etco2val;
        if (count _hist > 8) then { _hist deleteAt 0; };  // a breath-to-breath trailing average.
        private _sum = 0; { _sum = _sum + _x } forEach _hist;
        _player setVariable ["ACME_emma_etco2Disp", _sum / ((count _hist) max 1)];
        _player setVariable ["ACME_emma_rrDisp", _rr];  // rr refreshes on the breath rather than per frame.

        // publish the bagged rate onto the patient rather than only onto the EMMA of the medic. other systems, the TBI
        // CO2 limb in particular, need to know that a patient is being actively ventilated by hand, at what rate, and
        // how recently. without this, an apneic or arrested patient being correctly bagged reads as zero ventilation
        // everywhere downstream, and the provider is charged with hypoventilation for doing exactly the right thing.
        if (!isNull _bvmPatient) then {
            // TBI/manual-ventilation telemetry is casualty-owned. The owner publishes a serverTime freshness stamp,
            // so a medic's local clock can never make bagging appear stale/future on another machine.
            [_bvmPatient, "bvmTelemetry", [_rr]] call ACME_fnc_ownerDispatch;
        };    };
};
_player setVariable ["ACME_emma_breaths", _breaths];
_player setVariable ["ACME_emma_phase", _phase];
_player setVariable ["ACME_emma_etco2Hist", _hist];

private _etco2Disp = _player getVariable ["ACME_emma_etco2Disp", 0];
private _rrDisp    = _player getVariable ["ACME_emma_rrDisp", 0];
(_dlg displayCtrl 71503) ctrlSetText (if (_breaths >= 1) then { str (round (_etco2Disp max 0)) } else { "--" });
(_dlg displayCtrl 71509) ctrlSetText (if (_breaths >= 2) then { str (round (_rrDisp max 0)) } else { "--" });

// the capnography waveform, drawn AED-style. a sweeper bar tracks across the strip at the pace of the monitor,
// refreshing the single column it passes, by erasing and redrawing, and leaving a short blank gap just ahead of
// it. each refreshed column samples the real-time capnograph value, so as the patient breathes the trace builds
// an actual EtCO2 square wave: a rise, an alveolar plateau at the ETCO2 level, a sharp drop and then the
// baseline. the plateau height tracks ETCO2 and the rate tracks rr.
private _geo = uiNamespace getVariable ["ACME_emma_geo", []];
if (count _geo < 6) exitWith {};
_geo params ["_wx", "_wy", "_ww", "_wh", "_colW", "_cols"];

// sweep timing. the default is about twice the full-pass time of the AED, so the bar travels about half as
// slowly. the per-column period is the sweeptime divided by the columns, and the cursor is time-anchored like
// the AED's.
private _sweepTime = missionNamespace getVariable ["ACME_emma_sweepTime", 10.5];
private _colPeriod = _sweepTime / _cols;
private _cursor = floor (CBA_missionTime / _colPeriod) mod _cols;

private _wave = uiNamespace getVariable ["ACME_emma_wave", []];
if (count _wave != _cols) then {
    _wave = []; for "_i" from 1 to _cols do { _wave pushBack 0 };
};
private _last = uiNamespace getVariable ["ACME_emma_lastCursor", -1];
if (_last < 0) then { _last = _cursor };

private _amp = (linearConversion [0, 50, _etco2, 0.12, 1, true]);  // the plateau height, 0 to 1, tracks ETCO2.
private _breathing = (_rr >= 1) && {_etco2 > 0};  // is the patient actually exhaling CO2?
private _breath = 60 / ((_rr max 4) min 60);  // seconds per breath, which gives the hump rate.

// the capnograph morphology over one breath phase, 0 to 1. the number tells you how much and the shape tells you
// why, and a medic who reads the shape has the diagnosis before the number has finished moving.
([_patient] call ACME_fnc_capnoMorph) params ["_capShape", "_capSev"];
private _fnc_cap = {
    params ["_p"];
    // normal: a fast upstroke, a near-flat alveolar plateau with a slight rise, a sharp downstroke, then the
    // baseline.
    private _v = switch (true) do {
        case (_p < 0.05): { _p / 0.05 };
        case (_p < 0.40): { 0.9 + 0.1 * ((_p - 0.05) / 0.35) };
        case (_p < 0.45): { 1 - ((_p - 0.40) / 0.05) };
        default { 0 };
    };

    switch (_capShape) do {
        // the shark fin, which is obstructive. the alveoli empty at different rates because the airways are narrowed, so
        // the upstroke never finishes: it slopes all the way to the end of expiration and there is no plateau to
        // measure. the severity blends between a normal trace and a full fin, so it degrades rather than switching
        // between two cartoons.
        case "shark": {
            private _f = switch (true) do {
                case (_p < 0.42): { (_p / 0.42) ^ 0.55 };
                case (_p < 0.47): { (1 - ((_p - 0.42) / 0.05)) * 0.95 };
                default { 0 };
            };
            (_v * (1 - _capSev)) + (_f * _capSev)
        };

        // the curare cleft. it is a notch bitten out of the plateau where the patient took a breath of their own against
        // the machine, and it is deeper and wider the harder they are fighting. this is the one that says somebody is
        // paralyzed and awake, or coming out of a block, and it has never been visible until now.
        case "cleft": {
            private _c = 0.26;
            private _w = 0.05 + (0.05 * _capSev);
            if (_p > (_c - _w) && {_p < (_c + _w)}) then {
                private _d = 1 - ((abs (_p - _c)) / _w);
                _v = _v * (1 - ((0.30 + (0.45 * _capSev)) * _d));
            };
            _v
        };

        // flat. there is no CO2 coming back at all. on an intubated casualty this is the single most important trace in
        // medicine, and it should look like nothing, because it is nothing.
        case "flat": { 0 };

        default { _v };
    };
};
private _fnc_sample = {
    params ["_t"];
    if (!_breathing) exitWith { 0 };  // apnea gives a flat baseline, a sliver only.
    private _ph = (_t / _breath) mod 1;
    (_ph call _fnc_cap) * _amp
};

// write every column the cursor advanced over this frame, which is robust to more than one column per tick,
// sampling the capnograph at the real time that column was swept.
private _steps = _cursor - _last; if (_steps < 0) then { _steps = _steps + _cols };
if (_steps == 0) then {
    _wave set [_cursor, (CBA_missionTime call _fnc_sample)];
} else {
    for "_s" from 1 to _steps do {
        private _ci = (_last + _s) mod _cols;
        private _t = CBA_missionTime - ((_steps - _s) * _colPeriod);
        _wave set [_ci, (_t call _fnc_sample)];
    };
};

uiNamespace setVariable ["ACME_emma_wave", _wave];
uiNamespace setVariable ["ACME_emma_lastCursor", _cursor];

// render the columns. the trace never drops to nothing: every column shows at least a thin baseline sliver, so
// an apneic patient reads as a flat green line between breaths rather than a blank screen.
private _base = missionNamespace getVariable ["ACME_emma_waveBaseline", 0.06];
{
    private _b = _dlg displayCtrl (71600 + _forEachIndex);
    if (!isNull _b) then {
        private _bh = ((_x max _base) min 1) * _wh;
        _b ctrlSetPosition [_wx + _forEachIndex * _colW, _wy + _wh - _bh, _colW * 0.92, _bh];
        _b ctrlCommit 0;
    };
} forEach _wave;
private _sb = _dlg displayCtrl 71599;
if (!isNull _sb) then {
    private _swW = _colW * (missionNamespace getVariable ["ACME_emma_sweepWidth", 3.4]);
    _sb ctrlSetPosition [(_wx + _cursor * _colW) - (_swW - _colW) / 2, _wy, _swW, _wh];
    _sb ctrlCommit 0;
};
