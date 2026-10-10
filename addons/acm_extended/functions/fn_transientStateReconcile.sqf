/* Owner-local repair of transient multiplayer state.
 *
 * Durable clinical state is never guessed or erased here. This only repairs
 * provider reservations, temporary treatment state, malformed flow caches,
 * ghost IV-band flags, and expired animation/procedure leases.
 */
params [["_patient", objNull, [objNull]]];
if (isNull _patient || {!local _patient}) exitWith {0};

private _now = CBA_missionTime;
private _netNow = serverTime;
private _repairs = [];

private _mark = {
    params [["_name", "", [""]]];
    if (_name != "") then {_repairs pushBackUnique _name;};
};

private _debouncedInvalid = {
    params [["_key", "", [""]], ["_invalid", false, [false]], ["_grace", 2, [0]]];
    if (_key == "") exitWith {false};
    if (!_invalid) exitWith {
        _patient setVariable [_key, nil, false];
        false
    };
    private _at = _patient getVariable [_key, -1];
    if !(_at isEqualType 0 && {finite _at}) then {_at = -1;};
    if (_at < 0) exitWith {
        _patient setVariable [_key, _now, false];
        false
    };
    (_now - _at) >= (_grace max 0)
};

// BVM reservation.
if (!isNil "ACM_breathing_fnc_bvmSessionValid" && {!isNil "ACM_breathing_fnc_bvmRelease"}) then {
    private _medic = _patient getVariable ["ACM_breathing_BVM_Medic", objNull];
    private _provider = _patient getVariable ["ACM_breathing_BVM_provider", objNull];
    private _session = _patient getVariable ["ACM_breathing_BVM_session", []];
    private _invalid = if (!isNull _medic) then {
        !([_medic, _patient] call ACM_breathing_fnc_bvmSessionValid)
    } else {
        !isNull _provider || {!(_session isEqualTo [])}
    };

    if (["ACME_reconcileInvalidBVMAt", _invalid, 3] call _debouncedInvalid) then {
        private _released = false;
        if (!isNull _medic && {_session isEqualType []} && {count _session == 2}
            && {(_session select 0) isEqualTo _medic}) then {
            _released = [_medic, _patient, _session select 1] call ACM_breathing_fnc_bvmRelease;
        };
        if (!_released) then {
            [_patient, [
                ["bvmProvider", objNull],
                ["bvmMedic", objNull],
                ["bvmConnectedOxygen", false],
                ["bvmSession", []]
            ], true] call ACM_breathing_fnc_setRuntimeState;
            if (!isNull _medic && {(_medic getVariable ["ACM_breathing_BVM_patient", objNull]) isEqualTo _patient}) then {
                [_medic, [
                    ["bvmUsing", false],
                    ["bvmPatient", objNull],
                    ["bvmEpoch", -1]
                ], true] call ACM_breathing_fnc_setRuntimeState;
            };
        };
        "BVM reservation" call _mark;
    };
};

// CPR reservation.
if (!isNil "ACM_circulation_fnc_cprSessionValid" && {!isNil "ACM_circulation_fnc_cprRelease"}) then {
    private _medic = _patient getVariable ["ACM_circulation_CPR_Medic", objNull];
    private _provider = _patient getVariable ["ace_medical_CPR_provider", objNull];
    private _session = _patient getVariable ["ACM_circulation_CPR_session", []];
    private _invalid = if (!isNull _medic) then {
        !([_medic, _patient] call ACM_circulation_fnc_cprSessionValid)
    } else {
        !isNull _provider || {!(_session isEqualTo [])}
    };

    if (["ACME_reconcileInvalidCPRAt", _invalid, 3] call _debouncedInvalid) then {
        private _released = false;
        if (!isNull _medic && {_session isEqualType []} && {count _session == 2}
            && {(_session select 0) isEqualTo _medic}) then {
            _released = [_medic, _patient, _session select 1] call ACM_circulation_fnc_cprRelease;
        };
        if (!_released) then {
            [_patient, [["cprProvider", objNull], ["cprMedic", objNull], ["cprSession", []]], true] call ACM_circulation_fnc_setRuntimeState;
        };
        "CPR reservation" call _mark;
    };
};

// Hang Bag claim.
private _hangMedic = _patient getVariable ["ACME_hang_Medic", objNull];
private _hangLease = _patient getVariable ["ACME_hang_LeaseUntil", -1];
private _hangInvalid = !isNull _hangMedic && {
    if (_hangLease >= 0) then {
        !alive _hangMedic || {_hangMedic getVariable ["ACE_isUnconscious", false]}
        || {_netNow >= _hangLease}
        || {(_patient getVariable ["ACME_hang_LeaseEpoch", -1]) != ([_patient] call ACME_fnc_clinicalEpoch)}
    } else {
        !alive _hangMedic || {!(_hangMedic getVariable ["ACME_hang_Active", false])}
        || {!((_hangMedic getVariable ["ACME_hang_Patient", objNull]) isEqualTo _patient)}
        || {_hangMedic getVariable ["ACE_isUnconscious", false]}
    }
};
if (["ACME_reconcileInvalidHangAt", _hangInvalid, 2] call _debouncedInvalid) then {
    if ((_patient getVariable ["ACME_hang_Medic", objNull]) isEqualTo _hangMedic) then {
        [_patient, "hangBagRelease", [_hangMedic, _patient getVariable ["ACME_hang_Episode", -1]]] call ACME_fnc_ownerDispatch;
        "Hang Bag claim" call _mark;
    };
};

// Direct Pressure claims and clinical markers. Claims are the atomic site reservation; the marker may disappear
// temporarily while that provider yields to CPR/BVM/another treatment and therefore must not be treated as the claim.
{
    private _part = _x;
    private _key = format ["ACME_DP_press_%1", _part];
    private _claimKey = format ["ACME_DP_claim_%1", _part];
    private _claim = _patient getVariable [_claimKey, []];
    private _claimMedic = _claim param [0, objNull, [objNull]];
    private _claimEpoch = _claim param [2, -1, [0]];
    private _claimOwner = _claim param [3, -1, [0]];
    private _claimAt = _claim param [4, -1, [0]];
    private _claimOwnerValid = !isNull _claimMedic
        && {_claimOwner > 0 || {_claimOwner == 0 && {!isMultiplayer} && {local _claimMedic}}}
        && {if (local _claimMedic) then {_claimOwner == clientOwner} else {
            isMultiplayer && {!isServer || {_claimOwner == owner _claimMedic}}
        }};
    private _claimActive = !isNull _claimMedic
        && {_claimOwnerValid}
        && {_claimMedic getVariable ["ACME_DP_Active", false]}
        && {(_claimMedic getVariable ["ACME_DP_ClaimToken", ""]) == (_claim param [1, ""])}
        && {(_claimMedic getVariable ["ACME_DP_ClaimEpoch", -1]) == _claimEpoch}
        && {(_claimMedic getVariable ["ACME_DP_Patient", objNull]) isEqualTo _patient}
        && {toLowerANSI (_claimMedic getVariable ["ACME_DP_Part", ""]) == _part};
    private _claimPending = !isNull _claimMedic && {_claimAt >= 0}
        && {(_netNow - _claimAt) <= 3}
        && {_claimOwnerValid};
    private _claimInvalid = !(_claim isEqualTo []) && {
        !(_claim isEqualType [] && {count _claim >= 5})
        || {isNull _claimMedic}
        || {!alive _claimMedic}
        || {_claimMedic getVariable ["ACE_isUnconscious", false]}
        || {_claimEpoch != ([_patient] call ACME_fnc_clinicalEpoch)}
        || {!(_claimActive || {_claimPending})}
    };
    if ([format ["ACME_reconcileInvalidDPClaim_%1", _part], _claimInvalid, 2] call _debouncedInvalid) then {
        _patient setVariable [_claimKey, [], true];
        if ((_patient getVariable [_key, objNull]) isEqualTo _claimMedic) then {
            _patient setVariable [_key, objNull, true];
        };
        if ((_patient getVariable ["ACME_DP_TorsoMedic", objNull]) isEqualTo _claimMedic) then {
            _patient setVariable ["ACME_DP_TorsoMedic", objNull, true];
        };
        if ((_patient getVariable ["ACME_DP_LimbMedic", objNull]) isEqualTo _claimMedic) then {
            _patient setVariable ["ACME_DP_LimbMedic", objNull, true];
        };
        format ["Direct Pressure claim %1", _part] call _mark;
    };

    private _medic = _patient getVariable [_key, objNull];
    private _invalid = !isNull _medic && {
        !alive _medic
        || {!(_medic getVariable ["ACME_DP_Active", false])}
        || {(_medic getVariable ["ACME_DP_Paused", false])}
        || {!((_medic getVariable ["ACME_DP_Patient", objNull]) isEqualTo _patient)}
        || {toLowerANSI (_medic getVariable ["ACME_DP_Part", ""]) != _part}
    };
    if ([format ["ACME_reconcileInvalidDP_%1", _part], _invalid, 2] call _debouncedInvalid) then {
        if ((_patient getVariable [_key, objNull]) isEqualTo _medic) then {
            _patient setVariable [_key, objNull, true];
            if ((_patient getVariable ["ACME_DP_TorsoMedic", objNull]) isEqualTo _medic) then {
                _patient setVariable ["ACME_DP_TorsoMedic", objNull, true];
            };
            if ((_patient getVariable ["ACME_DP_LimbMedic", objNull]) isEqualTo _medic) then {
                _patient setVariable ["ACME_DP_LimbMedic", objNull, true];
            };
            format ["Direct Pressure %1", _part] call _mark;
        };
    };
} forEach ["head", "body", "leftarm", "rightarm", "leftleg", "rightleg"];

// Progressive bandage records.
private _progress = _patient getVariable ["ACM_damage_BandageProgress", createHashMap];
if !(_progress isEqualType createHashMap) then {
    _progress = createHashMap;
    [_patient, [["bandageProgress", _progress]], true] call ACM_damage_fnc_setWoundState;
    "Bandage progress shape" call _mark;
};
private _progressChanged = false;
{
    private _row = _progress get _x;
    private _expired = true;
    if (_row isEqualType [] && {count _row >= 5}) then {
        private _started = _row param [2, -1];
        private _duration = _row param [3, 0];
        _expired = !(_started isEqualType 0 && {finite _started})
            || {!(_duration isEqualType 0 && {finite _duration})}
            || {_started > _netNow + 5}
            || {_netNow - _started > ((_duration max 0) + 3)};
    };
    if (_expired) then {
        _progress deleteAt _x;
        _progressChanged = true;
    };
} forEach +(keys _progress);
if (_progressChanged) then {
    [_patient, [["bandageProgress", _progress]], true] call ACM_damage_fnc_setWoundState;
    if (!isNil "ace_medical_status_fnc_updateWoundBloodLoss") then {
        [_patient] call ace_medical_status_fnc_updateWoundBloodLoss;
    };
    "Expired bandage progress" call _mark;
};

// Junctional packing must agree with an active packing treatment.
{
    private _part = _x;
    private _state = toLowerANSI (_patient getVariable [format ["ACME_Junc_%1", _part], ""]);
    private _packing = _patient getVariable [format ["ACME_Junc_Packing_%1", _part], false];
    private _hasLivePack = false;
    if (_state == "open") then {
        {
            _y params [["_bp", ""], "", ["_started", -1], ["_duration", 0], ["_class", ""]];
            if (_class == "ACME_PackJunctional" && {_bp == _part}
                && {_started isEqualType 0} && {finite _started}
                && {_started <= _netNow + 2}
                && {_netNow - _started <= ((_duration max 0) + 2)}) exitWith {
                _hasLivePack = true;
            };
        } forEach _progress;
    };
    private _invalid = _packing && {_state != "open" || {!_hasLivePack}};
    if ([format ["ACME_reconcileInvalidPacking_%1", _part], _invalid, 2] call _debouncedInvalid) then {
        _patient setVariable [format ["ACME_Junc_Packing_%1", _part], false, true];
        _patient setVariable [format ["ACME_Junc_PackStamp_%1", _part], -1, false];
        format ["Junctional packing %1", _part] call _mark;
    };
} forEach ["leftarm", "rightarm", "leftleg", "rightleg"];

// AAJT-S application marker only. Persistent AAJT-S placement is untouched.
private _aajtApplying = _patient getVariable ["ACME_Junc_AAJTApplying", []];
private _badAAJTApplying = false;
if (_aajtApplying isEqualType []) then {
    if !(_aajtApplying isEqualTo []) then {
        private _stamp = _aajtApplying param [0, -1];
        private _part = toLowerANSI (_aajtApplying param [1, ""]);
        _badAAJTApplying = !(_stamp isEqualType 0 && {finite _stamp})
            || {!(_part in ["body","leftarm","rightarm","leftleg","rightleg"])}
            || {_stamp > _netNow + 5}
            || {_netNow - _stamp >= 25};
    };
} else {
    _badAAJTApplying = true;
};
if (_badAAJTApplying) then {
    _patient setVariable ["ACME_Junc_AAJTApplying", [], true];
    "AAJT-S applying marker" call _mark;
};

// IV_Bags_Active must follow the real authoritative bag map.
private _bags = _patient getVariable ["ACM_circulation_IV_Bags", createHashMap];
private _hasBags = (_bags isEqualType createHashMap) && {count _bags > 0};
private _bagsActive = _patient getVariable ["ACM_circulation_IV_Bags_Active", false];
if (_bagsActive isNotEqualTo _hasBags) then {
    [_patient, [["ivBagsActive", _hasBags]], true] call ACM_circulation_fnc_setRuntimeState;
    "IV_Bags_Active" call _mark;
};

// Repair malformed matrices only. Valid zero flow values remain intentional STOP states.
private _fixIVMatrix = {
    params ["_name"];
    private _src = _patient getVariable [_name, []];
    private _changed = !(_src isEqualType []);
    if !(_src isEqualType []) then {_src = [];};
    private _out = [];
    for "_i" from 0 to 5 do {
        private _row = _src param [_i, []];
        if !(_row isEqualType []) then {_row = []; _changed = true;};
        private _fixed = [];
        for "_j" from 0 to 2 do {
            private _v = _row param [_j, 1];
            if !(_v isEqualType 0 && {finite _v}) then {_v = 1; _changed = true;};
            _fixed pushBack _v;
        };
        if (count _row != 3) then {_changed = true;};
        _out pushBack _fixed;
    };
    if (count _src != 6) then {_changed = true;};
    if (_changed) then {
        _patient setVariable [_name, _out, true];
        format ["%1 shape", _name] call _mark;
    };
};
private _fixIOArray = {
    params ["_name"];
    private _src = _patient getVariable [_name, []];
    private _changed = !(_src isEqualType []);
    if !(_src isEqualType []) then {_src = [];};
    private _out = [];
    for "_i" from 0 to 5 do {
        private _v = _src param [_i, 1];
        if !(_v isEqualType 0 && {finite _v}) then {_v = 1; _changed = true;};
        _out pushBack _v;
    };
    if (count _src != 6) then {_changed = true;};
    if (_changed) then {
        _patient setVariable [_name, _out, true];
        format ["%1 shape", _name] call _mark;
    };
};

"ACM_circulation_FluidBagsFlow_IV" call _fixIVMatrix;
"ACM_circulation_ActiveFluidBags_IV" call _fixIVMatrix;
"ACM_circulation_FluidBagsFlow_IO" call _fixIOArray;
"ACM_circulation_ActiveFluidBags_IO" call _fixIOArray;

if (_hasBags && {!isNil "ACM_circulation_fnc_updateActiveFluidBags"}) then {
    {
        if (_y isEqualType [] && {count _y > 0}) then {
            [_patient, _x] call ACM_circulation_fnc_updateActiveFluidBags;
        };
    } forEach _bags;
};

// Repair only ghost IV constriction-band state. A coherent deliberate band remains applied.
private _siteRows = _patient getVariable ["ACME_IV_SiteState", []];
if !(_siteRows isEqualType []) then {_siteRows = [];};
private _parts = ["head","body","leftarm","rightarm","leftleg","rightleg"];
for "_i" from 2 to 5 do {
    private _flagRaw = _patient getVariable [format ["ACME_IV_BandOnPart_%1", _i], false];
    private _flag = (_flagRaw isEqualType true) && {_flagRaw};

    private _state = _patient getVariable [format ["ACME_IV_BandState_%1", _i], []];
    private _stateFlag = if (_state isEqualType [] && {count _state == 4}) then {
        _state param [1, false]
    } else {
        false
    };
    private _stateOn = (_stateFlag isEqualType true) && {_stateFlag};

    private _view = if (_stateOn) then {_state param [2, ""]} else {""};
    if !(_view isEqualType "") then {_view = "";};

    private _band = if (_stateOn) then {_state param [3, []]} else {[]};
    if !(_band isEqualType []) then {_band = [];};

    private _bandFlag = if (count _band == 6) then {_band param [0, false]} else {false};
    private _bandOn = (_bandFlag isEqualType true) && {_bandFlag};
    private _stateValid = _stateOn && {_view != ""} && {count _band == 6} && {_bandOn};

    private _rowValid = false;
    if (_stateValid) then {
        private _key = format ["%1|%2", _parts select _i, _view];

        // B184: this is a boolean existence test, not an index lookup. Older builds used findIf and then compared
        // its result numerically. A corrupted/foreign return value could therefore reach ">= 0" as a BOOL and throw
        // "Type Bool, expected Number". Walk the rows directly so the invariant itself is boolean end-to-end.
        {
            private _row = _x;
            if (_row isEqualType [] && {count _row == 4} && {(_row param [0, ""]) == _key}) then {
                private _rb = _row param [1, []];
                if (_rb isEqualType [] && {count _rb == 6}) then {
                    private _rbFlag = _rb param [0, false];
                    if (_rbFlag isEqualType true && {_rbFlag}) exitWith {
                        _rowValid = true;
                    };
                };
            };
        } forEach _siteRows;
    };

    private _ghost = (_flag && {!(_stateValid && {_rowValid})}) || {!_flag && {_stateOn}};
    if ([format ["ACME_reconcileGhostBand_%1", _i], _ghost, 2] call _debouncedInvalid) then {
        if (!isNil "ACME_fnc_ivStateLocal") then {
            [_patient, "band", [_i, false, _view, _band], [_patient] call ACME_fnc_clinicalEpoch]
                call ACME_fnc_ivStateLocal;
        } else {
            _patient setVariable [format ["ACME_IV_BandOnPart_%1", _i], false, true];
            _patient setVariable [format ["ACME_IV_BandState_%1", _i], [], true];
        };
        format ["Ghost IV band %1", _i] call _mark;
    };
};

// Surgical-airway lifetime belongs to ACM's live continuous-action dialog.
// Do not clear SurgicalAirway_InProgress from replicated session metadata: internal cric clicks and UI actions
// are presentation/input, not a treatment-lifetime change. Base ACM keeps this state until the dialog/controller ends.

// Expired patient animation lease.
private _animLock = _patient getVariable ["ACME_patientAnimLock", []];
if ((_animLock isEqualType []) && {count _animLock >= 5}) then {
    private _expires = _animLock param [4, -1];
    if !(_expires isEqualType 0 && {finite _expires} && {_expires > _netNow}) then {
        // B250: never erase an expired animation lease without releasing its owner-scoped
        // speed and collision state. The helper is token-checked and cannot retire a
        // newer animation that replaced this snapshot.
        private _token = _animLock param [0, "", [""]];
        if (_token != "") then {
            [_patient, _token, false] call ACME_fnc_patientAnimRelease;
        } else {
            _patient setVariable ["ACME_patientAnimLock", [], true];
        };
        // A malformed/legacy record can have an unrelated orphan speed token.
        // Retire it only if no newer animation lease is present.
        private _speedToken = _patient getVariable ["ACME_patientAnimSpeedToken", ""];
        if (_speedToken != "" && {(_patient getVariable ["ACME_patientAnimLock", []]) isEqualTo []}) then {
            [_patient, _speedToken, false] call ACME_fnc_patientAnimRelease;
        };
        "Patient animation lease" call _mark;
    };
};

if !(_repairs isEqualTo []) then {
    _patient setVariable ["ACME_transientRepairCount",
        (_patient getVariable ["ACME_transientRepairCount", 0]) + count _repairs, false];
    _patient setVariable ["ACME_transientRepairLast", [_netNow, +_repairs], false];
    diag_log format ["[ACME STATE RECONCILE] %1 repaired: %2", netId _patient, _repairs joinString " | "];
};

count _repairs
