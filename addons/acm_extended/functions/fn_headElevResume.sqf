// Restore the elevated animation after a temporary flat maneuver, provided elevation itself was not canceled.
// B122: the Semi-Fowler support carrier was never re-worn during suspension, so resume only re-seats that same
// prop. A backpack-supported temporary chest-access vest is restored separately after its final chest-access lease.
params ["_patient", ["_frontNormalized", false, [false]]];
if (isNull _patient) exitWith {};
if (!local _patient) exitWith {[_patient, "headElevResume", [_patient, _frontNormalized]] call ACME_fnc_ownerDispatch;};
if (!alive _patient) exitWith {[_patient] call ACME_fnc_headElevDeathRelease;};
if !(_patient getVariable ["ACME_headElevated", false]) exitWith {};
if !(_patient getVariable ["ACME_headElev_Suspended", false]) exitWith {};

// Semi-Fowler resume has the same hard invariant as initial placement: patient on their back first, animation second.
// If already anterior-up, nothing is replayed. If not, roll to front/supine and only then re-seat the support prop
// and run ACME_HeadElevPatientGrab/Hold.
private _actualBeforeResume = [_patient, _patient getVariable ["ACME_CS_facing","front"]]
    call ACME_fnc_chestSealActualSide;
private _needFrontFirst = !_frontNormalized && {_actualBeforeResume != "front"};

if (_needFrontFirst) exitWith {
    private _delay = 0.08;

    if ([_patient] call ACME_fnc_chestSealCanPhysicalRoll) then {
        [_patient,"front",false,objNull,true] call ACME_fnc_chestSealRoll;
        private _rollTime = missionNamespace getVariable ["ACME_CS_rollTime", 1.85 / (call ACME_fnc_choreographyRate)];
        if !(_rollTime isEqualType 0 && {finite _rollTime}) then {_rollTime = 1.85 / (call ACME_fnc_choreographyRate);};
        _delay = (_rollTime max 0.1) + 0.08;
    } else {
        private _faceUp = missionNamespace getVariable ["ACME_uncon_faceUp","ACM_LyingState"];
        _patient setVariable ["ACME_CS_facing","front",true];
        ["ace_common_switchMove",[_patient,_faceUp]] call CBA_fnc_globalEvent;
    };

    [{
        params ["_p"];
        if (!isNull _p && {local _p} && {alive _p}) then {
            _p setVariable ["ACME_CS_facing","front",true];
            [_p,true] call ACME_fnc_headElevResume;
        };
    }, [_patient], _delay] call CBA_fnc_waitAndExecute;
};

_patient setVariable ["ACME_CS_facing","front",true];

// If the elevated patient uses a backpack, a chest-access action may have temporarily parked the worn carrier.
// Restore it only when no chest-access owner still needs the chest clear. This is independent of the elevation
// support carrier, which remains removed for the entire logical Semi-Fowler placement when no backpack exists.
[_patient] call ACME_fnc_chestAccessVestRestore;

_patient setVariable ["ACME_headElev_suspendKeepVestOut", false, true];
_patient setVariable ["ACME_headElev_suspendVestLoadout", [], false];
_patient setVariable ["ACME_headElev_suspendReadyAt", -1, false];
_patient setVariable ["ACME_headElev_Suspended", false, true];
_patient setVariable ["ACME_headElev_basePosASL", getPosASL _patient, true];
_patient setVariable ["ACME_headElev_baseDir", getDir _patient, true];

// No-backpack Semi-Fowler: release the fixed chest-workspace park, then move the same support carrier
// back behind the upper back. Backpack Semi-Fowler has no head-elevation carrier prop.
private _headProp = _patient getVariable ["ACME_headElev_propObj", objNull];
if (!isNull _headProp) then {_headProp setVariable ["ACME_chestFixedPark", nil, false];};
[_patient] call ACME_fnc_headElevPropApply;
[_patient] call ACME_fnc_headElevApplyTilt;
