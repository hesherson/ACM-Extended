/* B121: persistent one-handed syringe worker. It owns flow independently of all displays. */
scopeName "ACME_HC_PUSH_TICK";
private _job = missionNamespace getVariable ["ACME_HCMedPushJob",createHashMap];
if !(_job isEqualType createHashMap && {count _job > 0}) exitWith {
    ["clear"] call ACME_fnc_hardcorePushOverlay;
    private _h = missionNamespace getVariable ["ACME_HCMedPushPFH",-1];
    if (_h >= 0) then {[_h] call CBA_fnc_removePerFrameHandler; missionNamespace setVariable ["ACME_HCMedPushPFH",-1];};
};
if !(_job getOrDefault ["flowing",false]) exitWith {call ACME_fnc_hardcorePushFinalize;};
if !(missionNamespace getVariable ["ACME_hcEff_medications",false]) exitWith {["hardcore-disabled"] call ACME_fnc_hardcorePushStop;};
private _medic = _job getOrDefault ["medic",objNull];
private _patient = _job getOrDefault ["patient",objNull];
if (isNull _medic || {isNull _patient} || {!local _medic} || {!alive _medic} || {_medic getVariable ["ACE_isUnconscious",false]}) exitWith {["provider"] call ACME_fnc_hardcorePushStop;};
// Exact ACM AED leash semantics: same objectParent plus configured distance, or the same vehicle.
private _leash = missionNamespace getVariable ["ACM_circulation_AEDDistanceLimit",5];
if (((objectParent _medic) isNotEqualTo (objectParent _patient)) || {(_patient distance _medic) > _leash}) exitWith {["leash"] call ACME_fnc_hardcorePushStop;};
private _body = _job getOrDefault ["bodyPart","body"];
private _site = _job getOrDefault ["site",-2];
private _identity = [_patient,_body,_site] call ACME_fnc_medicationLineIdentity;
if (_identity isEqualTo [] || {!(_identity isEqualTo (_job getOrDefault ["identity",[]]))}) exitWith {["access"] call ACME_fnc_hardcorePushStop;};
if ([_patient,_body,_site] call ACME_fnc_medicationLineBloodBusy) exitWith {["blood-line"] call ACME_fnc_hardcorePushStop;};
private _now = diag_tickTime;
private _last = _job getOrDefault ["lastTick",_now];
private _dt = ((_now - _last) max 0) min 0.25;
_job set ["lastTick",_now];
if (_dt <= 0) exitWith {[] call ACME_fnc_hardcorePushOverlay;};
private _carry = (_job getOrDefault ["carryMl",0]) + (_job getOrDefault ["rateMlSec",0]) * _dt;
private _targetLeft = ((_job getOrDefault ["targetMl",0]) - (_job getOrDefault ["pushedMl",0])) max 0;
private _step = (floor ((_carry + 0.000001) * 100)) / 100;
// A final fraction of a hundredth still owes its share of the selected duration.
// Only snap that endpoint after enough flow has accrued to move it.
if (_targetLeft <= 0.0101 && {_targetLeft > 0} && {_carry + 0.000001 >= _targetLeft}) then {_step = _targetLeft;};
_step = _step min _targetLeft;
if (_step > 0.000001) then {
    private _store = +(_medic getVariable ["ACME_narcStore",[]]);
    private _stable = _job getOrDefault ["stableId",""];
    private _idx = _store findIf {(_x param [11,"",[""]]) == _stable};
    if (_idx < 0) then {["syringe"] call ACME_fnc_hardcorePushStop; breakOut "ACME_HC_PUSH_TICK";};
    private _row = +(_store select _idx);
    private _drug = (_row param [2,0,[0]]) max 0;
    private _ns = (_row param [4,0,[0]]) max 0;
    private _total = _drug + _ns;
    if (_total <= 0.000001) then {["complete"] call ACME_fnc_hardcorePushStop; breakOut "ACME_HC_PUSH_TICK";};
    _step = _step min _total;
    private _frac = (_step / _total) max 0 min 1;
    private _dDrug = _drug * _frac;
    private _dNs = _ns * _frac;
    _row set [2,(_drug - _dDrug) max 0];
    _row set [4,(_ns - _dNs) max 0];
    private _parts = +(_row param [5,[],[[]]]);
    private _dParts = [];
    for "_i" from 0 to ((count _parts)-1) do {
        private _p = +(_parts select _i);
        private _source = _p param [0,"",[""]];
        private _v = (_p param [1,0,[0]]) max 0;
        private _dv = _v * _frac;
        _p set [1,(_v-_dv) max 0]; _parts set [_i,_p];
        _dParts pushBack [_i,_source,_dv];
    };
    _row set [5,_parts]; _store set [_idx,_row];
    _medic setVariable ["ACME_narcStore",_store,false];
    private _unsent = +(_job getOrDefault ["unsentDelta",[0,0,[]]]);
    _unsent set [0,(_unsent param [0,0]) + _dDrug];
    _unsent set [1,(_unsent param [1,0]) + _dNs];
    private _uc = +(_unsent param [2,[],[[]]]);
    {
        _x params ["_ci","_source","_dv"];
        private _uix = _uc findIf {(_x param [0,-1]) == _ci};
        if (_uix < 0) then {_uc pushBack [_ci,_source,_dv];} else {private _u=+(_uc select _uix);_u set [2,(_u param [2,0])+_dv];_uc set [_uix,_u];};
    } forEach _dParts;
    _unsent set [2,_uc];
    _job set ["unsentDelta",_unsent];
    _job set ["pushedMl",(_job getOrDefault ["pushedMl",0]) + _step];
    _carry = (_carry - _step) max 0;
};
_job set ["carryMl",_carry];
_job set ["batchElapsed",(_job getOrDefault ["batchElapsed",0]) + _dt];
missionNamespace setVariable ["ACME_HCMedPushJob",_job];

// Keep the open Narc Box plunger physically tied to the authoritative remaining syringe volume at tick rate.
// A full carousel repaint is intentionally throttled below, but the single plunger control is cheap enough to
// update every 50 ms and gives a visibly continuous push instead of appearing frozen between UI refreshes.
private _open = findDisplay 84000;
if (!isNull _open) then {
    private _stableUi = _job getOrDefault ["stableId",""];
    private _storeUi = +(_medic getVariable ["ACME_narcStore",[]]);
    private _idxUi = _storeUi findIf {(_x param [11,"",[""]]) == _stableUi};
    if (_idxUi >= 0) then {
        private _rowUi = _storeUi select _idxUi;
        private _sizeUi = _rowUi param [1,10,[0]];
        private _remainUi = ((_rowUi param [2,0,[0]]) + (_rowUi param [4,0,[0]])) max 0;
        private _fracUi = ((_remainUi / (_sizeUi max 0.01)) max 0) min 1;
        private _barUi = _open displayCtrl 84420;
        private _plUi = _open displayCtrl 84422;
        if (!isNull _barUi && {!isNull _plUi}) then {
            private _brUi = +(ctrlPosition _barUi);
            private _nativeUi = _open getVariable ["ACME_SK_CarouselNativeRect",[0,0,1,1]];
            private _travel10Ui = _open getVariable ["ACME_SK_CarouselTravel10",safeZoneH*0.17];
            private _ratioUi = switch (_sizeUi) do {case 1:{10.2/10.5};case 3:{9.83/10.5};case 5:{10.3/10.5};default{1};};
            private _yUi = (_brUi select 1) + (_travel10Ui * _ratioUi * _fracUi * ((_brUi select 3) / (((_nativeUi select 3) max 0.001))));
            _plUi ctrlSetPosition [_brUi select 0,_yUi,_brUi select 2,_brUi select 3];
            _plUi ctrlCommit 0;
        };
    };
};

[false] call ACME_fnc_hardcorePushSendBatch;
_job = missionNamespace getVariable ["ACME_HCMedPushJob",_job];
if ((_job getOrDefault ["pushedMl",0]) >= (_job getOrDefault ["targetMl",0]) - 0.0005) exitWith {
    _job set ["finishRequested",true]; missionNamespace setVariable ["ACME_HCMedPushJob",_job];
    ["complete"] call ACME_fnc_hardcorePushStop;
};
// UI repaint is throttled independently from flow. Null/closed displays are expected and never a stop condition.
if (!isNull (findDisplay 84000)) then {
    if (_now >= (_job getOrDefault ["nextUi",0])) then {
        _job set ["nextUi",_now+0.15]; missionNamespace setVariable ["ACME_HCMedPushJob",_job];
        [0] call ACME_fnc_skCarouselRender; call ACME_fnc_skBodyActionRender;
    };
} else {[] call ACME_fnc_hardcorePushOverlay;};
