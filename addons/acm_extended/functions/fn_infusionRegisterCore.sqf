params ["_context", "_medication", "_doseMg", "_durationSeconds", "_dropSet", "_dropsPerMinute", "_clampPosition", "_uid", "_bagUid", "_epoch", ["_solutionMl", 0], ["_deferPublish", false]];
_context params ["_patient", "_bodyPart", "_bagIndex", "_type", "_accessType", "_bagAccessSite", "_bagIV", "_bloodType", "_volume", "_freshBloodID", "_remainingVolume"];

if (!local _patient || {_epoch != ([_patient] call ACME_fnc_clinicalEpoch)}) exitWith {""};
if (((_patient getVariable ["ACME_infusion_BagMedications", []]) findIf {(_x select 0) == _uid}) >= 0) exitWith {_uid};
if !([_context] call ACME_fnc_canMedicateBagContext) exitWith {
    ""
};

private _found = [_patient, _bodyPart, _bagIndex, _type, _bagAccessSite, _bagIV, _bloodType, _volume, _freshBloodID, _remainingVolume, _bagUid] call ACME_fnc_findTrackedBag;
if (_found isEqualTo []) exitWith { ""};
private _foundBag = _found select 2;
if !(_found isEqualTo []) then {
    _found params ["_foundBodyPart", "_foundIndex"];
    _bodyPart = _foundBodyPart;
    _bagIndex = _foundIndex;
    _remainingVolume = _foundBag param [1, 0];
    _bagUid = [_patient, _bodyPart, _bagIndex] call ACME_fnc_bagIdentity;
    _bagAccessSite = _foundBag param [3, _bagAccessSite]; _bagIV = _foundBag param [4, _bagIV];
};

// the delivered medication classname. it defaults to "<Med>_IV", and some drugs are delivered as another class so
// the recorded medication is the intended one: ceftriaxone remains Ceftriaxone_IV, for the evac credit and the
// effect, and calcium gluconate becomes CalciumChloride_IV, for the calcium count. see
// ACME_infusion_deliveryClassOverride.
private _existing = (_patient getVariable ["ACME_infusion_BagMedications", []]) select {(_x param [23, ""]) == _bagUid};
if (_solutionMl < 0 || {!finite _solutionMl}) exitWith {""};
if (_doseMg <= 0 || {!finite _doseMg} || {_remainingVolume <= 0}) exitWith {""};
private _actualContext = [_patient, _bodyPart, _bagIndex, _foundBag param [0, _type], _foundBag param [2, _accessType], _bagAccessSite, _bagIV, _bloodType, _volume, _freshBloodID, _remainingVolume];
if !([_actualContext] call ACME_fnc_canMedicateBagContext) exitWith {""};
private _classIV = (missionNamespace getVariable ["ACME_infusion_deliveryClassOverride", createHashMap]) getOrDefault [_medication, format ["%1_IV", _medication]];

if (_durationSeconds <= 0) then {
    _durationSeconds = (ACME_infusion_defaultDurationSeconds getOrDefault [_medication, 600]) max 1;
};
if (_dropSet <= 0) then {_dropSet = ACME_infusion_defaultDropSet};
if (_clampPosition < 0) then {
    if (_dropsPerMinute > 0) then {
        _clampPosition = [_dropsPerMinute] call ACME_fnc_dropsToClampPosition;
    } else {
        _clampPosition = missionNamespace getVariable ["ACME_infusion_defaultClampPosition", 1];
    };
};

_clampPosition = (_clampPosition max 0) min 1;
_dropsPerMinute = [_clampPosition] call ACME_fnc_clampPositionToDrops;

private _entries = _patient getVariable ["ACME_infusion_BagMedications", []];
private _newVolume = _remainingVolume + _solutionMl;
private _original = (_foundBag param [6, _remainingVolume]) + _solutionMl;
// All components share the one physical valve. A later injection must not reset it.
if !(_existing isEqualTo []) then {
    _dropSet = (_existing select 0) select 20;
    _dropsPerMinute = (_existing select 0) select 21;
    _clampPosition = (_existing select 0) select 22;
};
{
    if ((_x param [23, ""]) == _bagUid) then {
        _x set [7, _original];
        _x set [9, _original];
        _x set [10, _newVolume];
        _x set [26, (_x select 14) / _newVolume];
        _x set [20, _dropSet]; _x set [21, _dropsPerMinute]; _x set [22, _clampPosition];
    };
} forEach _entries;
private _same = _entries findIf {(_x param [23, ""]) == _bagUid && {(_x select 11) == _medication}};
private _resultId = _uid;
if (_same >= 0) then {
    private _e = _entries select _same;
    _e set [13, (_e select 13) + _doseMg];
    _e set [14, (_e select 14) + _doseMg];
    _e set [26, (_e select 14) / _newVolume];
    _e set [27, (_e param [27, 1]) + 1];
    _resultId = _e select 0;
} else {
    _entries pushBack [_uid, _bodyPart, _bagIndex, _type, _bagAccessSite, _bagIV,
        _bloodType, _original, _freshBloodID, _original, _newVolume, _medication,
        _classIV, _doseMg, _doseMg, 0, CBA_missionTime, 0, CBA_missionTime,
        _durationSeconds, _dropSet, _dropsPerMinute, _clampPosition, _bagUid,
        0, 0, _doseMg / _newVolume, 1];
};
if (_solutionMl > 0) then {
    private _map = _patient getVariable ["ACM_circulation_IV_Bags", createHashMap];
    private _bags = _map getOrDefault [_bodyPart, []];
    _foundBag set [1, _newVolume]; _foundBag set [6, _original];
    _bags set [_bagIndex, _foundBag]; _map set [_bodyPart, _bags];
    [_patient, _map, !_deferPublish] call ACME_fnc_ivBagsCommit;
};
[_patient, _entries, !_deferPublish] call ACME_fnc_infusionMedicationStateCommit;
if (!_deferPublish) then {
    [_patient, _entries select (if (_same >= 0) then {_same} else {(count _entries) - 1})] call ACME_fnc_infusionFlow;
    ACME_infusion_activePatients pushBackUnique _patient;
};

// a distal epinephrine drip gives a catecholamine-driven atrial tachyarrhythmia.
// there is no instant rhythm flip on a bag hang. the circ handler waits for the drip to actually run long enough for
// an epinephrine effect envelope to develop, then applies a per-minute hazard while the distal drip is active.
if (!_deferPublish && {_medication == "Epinephrine"}
    && {_bagIV}
    && {_bagAccessSite >= 1}
    && {_bodyPart in ["leftarm", "rightarm", "leftleg", "rightleg"]}
) then {
    _patient setVariable ["ACME_rhythm_epiDripEarliest", CBA_missionTime + (missionNamespace getVariable ["ACME_infusion_epiArrhythmiaOnsetSec", 60]), true];
};

// premixed bag pharmacodynamics.
// esmolol and magnesium no longer act on registration. handleinfusions delivers their dose into the native
// medicationlocal path of ACM, and fn_circhandle reads the resulting ACM medication effect curve before converting
// AFib-RVR or terminating and suppressing torsades. this preserves the onset, the plateau and the washout after the
// bag stops.

_resultId
