// Sustain custom-rhythm symptoms on the patient owner. updateHeartRate consumes the separate rhythm target;
// this tick never pins native rhythm state or directly forces HR. A real native deterioration releases the
// overlay. A fast supraventricular rate alone does not change its electrical origin.
// Release removes Extended contributions and ends its temporary obtundation without overwriting native state.
if !(missionNamespace getVariable ["ACME_sys_rhythm", true]) exitWith {};
private _fnc_release = {params ["_u"]; [_u] call ACME_fnc_rhythmRelease;};

{
    private _u = _x;
    private _code = _u getVariable ["ACME_rhythm_active", 0];

    // physiology takes over, so let the rhythm change. if the patient has entered cardiac arrest, or ACM's own sim
    // has moved the display rhythm to an arrest or CPR rhythm, meaning asystole, vf, pulseless vt, PEA or CPR, or
    // the heart rate has cratered, we stop forcing and hand the monitor back to ACM. this both honors a real
    // deterioration, such as a hypoxic arrest while AFib-RVR is induced, and avoids drawing an organized forced
    // rhythm at hr 0, which makes ACM divide 60 by hr and gives the zero divisor crash in displayaedmonitor and
    // genekg.
    private _curRhythm = [_u] call ACME_fnc_rhythmNative;
    private _dt = [_u, "rhythm", 0.5, 5] call ACME_fnc_clinicalTickDelta;
    private _hrNow = _u getVariable ["ace_medical_heartRate", 80];

    // Torsades is a conversion into a nonperfusing ventricular rhythm, not a permanently perfusing tachycardia.
    // Use the exact same time window as the monitor morph and continuously publish the remaining mechanical
    // perfusion fraction. Manual pulse assessment reads that fraction so the pulse becomes weaker/slower throughout
    // the entry strip and is completely absent when the waveform is fully converted.
    private _torsadesNonPerf = _code == 102 && {_u getVariable ["ACME_rhythm_torsadesNonPerfusing", false]};
    private _torsadesPerfusion = if (_code == 102) then {_u getVariable ["ACME_rhythm_torsadesPerfusion",1]} else {1};
    if (_code == 102) then {
        private _startAt = _u getVariable ["ACME_rhythm_torsadesStart", -1];
        private _entryMinSec = missionNamespace getVariable ["ACME_rhythm_torsadesEntryMinSec", 6];
        private _entrySweeps = missionNamespace getVariable ["ACME_rhythm_torsadesEntrySweeps", 3];
        private _entryWindow = _entryMinSec max (_entrySweeps * 176 * 0.03);
        private _elapsed = if (_startAt >= 0) then {(CBA_missionTime - _startAt) max 0} else {0};
        private _rawProgress = (_elapsed / (_entryWindow max 0.1)) max 0 min 1;
        private _progress = _rawProgress * _rawProgress * (3 - (2 * _rawProgress));
        _torsadesPerfusion = (1 - _progress) max 0 min 1;
        if (abs ((_u getVariable ["ACME_rhythm_torsadesPerfusion",1]) - _torsadesPerfusion) >= 0.015 || {_rawProgress >= 1}) then {
            [_u, "ACME_rhythm_torsadesPerfusion", _torsadesPerfusion] call ACME_fnc_setVarNet;
        };

        if (_rawProgress >= 1) then {
            if (!_torsadesNonPerf) then {
                [_u, "ACME_rhythm_torsadesNonPerfusing", true] call ACME_fnc_setVarNet;
                _torsadesNonPerf = true;
            };

            // Keep requesting the native arrest transition until ACE confirms it. The old code made one request and
            // then latched NonPerfusing=true; if that one state-machine event was missed/delayed, torsades could stay
            // electrically mature while still having a pulse forever.
            if !(_u getVariable ["ace_medical_inCardiacArrest", false]) then {
                private _lastReq = _u getVariable ["ACME_rhythm_torsadesArrestRequestAt", -1];
                if (_lastReq < 0 || {(CBA_missionTime - _lastReq) >= 0.75}) then {
                    _u setVariable ["ACME_rhythm_torsadesArrestRequestAt", CBA_missionTime, false];
                    [_u, 3, [_u] call ACME_fnc_clinicalEpoch] call ACME_fnc_arrestLocal;
                };
            };

            if (_u getVariable ["ace_medical_inCardiacArrest", false]) then {
                // Mature torsades is native PVT mechanically. If ACM initially routes a low-output arrest through its
                // reversible/PEA worker, explicitly hand it back to the normal PVT arrest worker.  This gives mature
                // torsades the same no-pulse/deterioration/AED lifecycle as native pulseless VT while 102 remains only
                // the monitor morphology.
                if (([_u] call ACME_fnc_rhythmNative) != 3) then {
                    _u setVariable ["ACME_nativeRequestedRhythm",3,false];
                    [_u,3] call ACM_circulation_fnc_setCardiacArrestTargetRhythm;
                    [_u] call ACM_circulation_fnc_handleCardiacArrest;
                    _u setVariable ["ACME_nativeRequestedRhythm",nil,false];
                    if (([_u] call ACME_fnc_rhythmNative) != 3) then {
                        [_u, [["cardiacRhythmState", 3]], true] call ACM_circulation_fnc_setRuntimeState;
                    };
                };
                _curRhythm = 3;
            };
        };
    };

    // Every other perfusing custom rhythm yields immediately when native ACM enters a true critical/arrest rhythm.
    // Mature torsades is the intentional exception: native PVT owns physiology while 102 owns morphology.
    private _torsadesOwnsPVT = _code == 102
        && {_torsadesNonPerf}
        && {_u getVariable ["ace_medical_inCardiacArrest", false]}
        && {_curRhythm == 3};
    private _hrReleases = (_hrNow < (missionNamespace getVariable ["ACME_rhythmACMFatalLowHR", 40]))
        || {_hrNow > (missionNamespace getVariable ["ACME_rhythmACMFatalHighHR", 220])};
    private _physiologyTookOver = !(_torsadesOwnsPVT) && {
        (_u getVariable ["ace_medical_inCardiacArrest", false])
        || {_curRhythm in [-1,1,2,3,4,5]}
        || _hrReleases
    };

    if (_physiologyTookOver) then {
        [_u, false] call _fnc_release;
    } else {
        // the hemodynamic profile: each rhythm presents with its real-life perfusion picture.
        // bpoffset drops MAP, which cascades everywhere downstream: a low NIBP on the cuff, a prolonged capillary refill,
        // because ACM's crt is a function of MAP and blood volume, the obtunded auto-band, and a low CPP on a TBI brain.
        // a poorly perfusing rhythm therefore reads as one without us touching each vital by hand. spo2floor adds
        // peripheral desaturation for the unstable rhythms, and it is skipped while an NRB is feeding o2.
        private _bpOff = if (_torsadesOwnsPVT) then {0} else {switch (_code) do {
            case 100: { missionNamespace getVariable ["ACME_rhythm_bpDropRVR", -28] };  // AFib-RVR: unstable and poorly perfusing.
            case 101: { missionNamespace getVariable ["ACME_rhythm_bpDropAtrialTach", -12] };  // atrial tach: mild instability.
            case 102: {
                // Mechanical output collapses in step with the visible torsades conversion. Start symptomatic but
                // still perfusing, then drive toward profound hypotension as the pulse fraction approaches zero.
                private _baseDrop = missionNamespace getVariable ["ACME_rhythm_bpDropTorsades", -30];
                linearConversion [0,1,(1 - _torsadesPerfusion),(_baseDrop * 0.35),(_baseDrop * 1.65),true]
            };
            case 103: { missionNamespace getVariable ["ACME_rhythm_bpDropAFib", 0] };  // controlled AFib: it perfuses fine.
            case 104: { missionNamespace getVariable ["ACME_rhythm_bpDropSVT", -18] };  // SVT: symptomatic and cardiovertible.
            default  { 0 };
        }};
        if ((_u getVariable ["ACME_rhythm_bpOffset", 0]) != _bpOff) then { [_u, "ACME_rhythm_bpOffset", _bpOff] call ACME_fnc_setVarNet; };

        private _spo2Floor = if (_torsadesOwnsPVT) then {100} else {switch (_code) do {
            case 100: { 90 }; case 102: { 88 }; case 104: { 93 }; case 101: { 95 }; default { 100 };
        }};
        if (_spo2Floor < 100 && {!(_u getVariable ["ACME_nrb_delivering", false])}) then {
            private _spo2 = _u getVariable ["ace_medical_spo2", 97];
            if (_spo2 > _spo2Floor) then { [_u, [["spo2", ((_spo2 - (1.2 * _dt)) max _spo2Floor), true, true]]] call ACM_core_fnc_setAceMedicalState; };
        };

        private _targetPain = switch (_code) do {
            case 100: {missionNamespace getVariable ["ACME_rhythm_painRVR", 0.50]};
            case 101: {missionNamespace getVariable ["ACME_rhythm_painAtrialTach", 0.35]};
            case 103: {missionNamespace getVariable ["ACME_rhythm_painAFib", 0.35]};
            case 104: {missionNamespace getVariable ["ACME_rhythm_painSVT", 0.45]};
            default {0};
        };
        // Separate perceived discomfort. Native wounds and analgesic history remain untouched.
        private _cur = _u getVariable ["ACME_rhythm_painContribution", 0];
        private _step = (missionNamespace getVariable ["ACME_rhythm_painStepPerSec", 0.12]) * _dt;
        if (_u getVariable ["ACE_isUnconscious", false]) then {_targetPain = 0;};
        [_u, "ACME_rhythm_painContribution", _cur + (((_targetPain - _cur) max (-_step)) min _step), 0.01, 1] call ACME_fnc_setVarNetApprox;
        if (_code != 102) then {
            // an obtundation episode: a chance per tick to drop into the lying state, player-only, because obtundedset wakes
            // an unconscious patient into it. it uses a manual flag, so the vitals-driven auto-evaluator leaves it alone,
            // and we end it on our own timer.
            if (isPlayer _u) then {
                if (!(_u getVariable ["ACME_obtunded", false])) then {
                    if (random 1 < (1 - ((1 - (missionNamespace getVariable ["ACME_rhythm_obtundChancePerTick", 0.015])) ^ (_dt / 0.5)))) then {
                        private _lo = missionNamespace getVariable ["ACME_rhythm_obtundMinSec", 12];
                        private _hi = missionNamespace getVariable ["ACME_rhythm_obtundMaxSec", 30];
                        [_u, "ACME_rhythm_obtundUntil", (CBA_missionTime + _lo + random (_hi - _lo))] call ACME_fnc_setVarNet;
                        [_u, true, true] call ACME_fnc_obtundedSet;
                    };
                } else {
                    // end the episode when its timer runs out, and only if we started it.
                    private _until = _u getVariable ["ACME_rhythm_obtundUntil", -1];
                    if (_until > 0 && {CBA_missionTime >= _until}) then {
                        [_u, "ACME_rhythm_obtundUntil", -1] call ACME_fnc_setVarNet;
                        [_u, false, false] call ACME_fnc_obtundedSet;
                    };
                };
            };
        };


    };
} forEach ((missionNamespace getVariable ["ACME_rhythm_activePatients", []]) select {
    !isNull _x && {local _x} && {alive _x} && {(_x getVariable ["ACME_rhythm_active", 0]) >= 100}
});
ACME_rhythm_activePatients = (missionNamespace getVariable ["ACME_rhythm_activePatients", []]) select {
    !isNull _x && {local _x} && {alive _x} && {(_x getVariable ["ACME_rhythm_active", 0]) >= 100}
};
