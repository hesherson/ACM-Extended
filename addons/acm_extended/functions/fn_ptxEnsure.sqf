/* Adopt existing PTX without an injury or another worker.
State v1: [version,air,leak,stableSeconds,pressure,ncdPatency,injurySerial,lastNativeAir,residualAir]. */
params [["_patient",objNull,[objNull]]];
if (isNull _patient || {!local _patient}) exitWith {[]};
private _h=_patient getVariable ["ACM_breathing_Pneumothorax_PFH",-1];
if (_h>=0) then {[_h] call CBA_fnc_removePerFrameHandler;};
[_patient, [["pneumothoraxPFH", -1]], false] call ACM_breathing_fnc_setRuntimeState;
private _s=_patient getVariable ["ACME_ptx_state",[]];
if (_s isEqualType [] && {count _s==9} && {(_s select 0)==1}
    && {(_s findIf {!(_x isEqualType 0) || {!finite _x}})<0}) exitWith {
    _s=+_s;
    private _native=_patient getVariable ["ACM_breathing_Pneumothorax_State",0];
    if (!(_native isEqualType 0) || {!finite _native}) then {_native=_s select 7;};
    _native=_native max 0 min 4;
    private _tension=_patient getVariable ["ACM_breathing_TensionPneumothorax_State",false];
    // B271 observation is stricter than an older build's quiet-air timer. Adopt
    // old/save-restored episodes without granting their old observation credit.
    if !((_patient getVariable ["ACME_ptx_observationRevision", 0]) isEqualTo 1) then {
        _s set [3, 0];
        [_patient,"ACME_ptx_observationRevision",1] call ACME_fnc_setVarNet;
        [_patient,_s,_tension] call ACME_fnc_ptxPublish;
    };
    // Native Zeus or another injury source may deliberately set native severity.
    // Equal projection values (including save/load) never reseed a settled leak.
    if (_native!=(_s select 7)) then {
        if (_native>(_s select 7)) then {
            _s set [2,(_s select 2) max (_native*0.20)];
            _s set [6,(_s select 6)+1];
            if (_tension) then {_s set [4,1];};
        } else {
            if (_native==0 && {!_tension}) then {
                _s set [2,0];_s set [4,0];_s set [8,0];
                if !(_patient getVariable ["ACM_breathing_ChestInjury_State",false]) then {_s set [5,0];_s set [6,0];};
            };
        };
        _s set [1,_native];_s set [3,0];
        _s set [8,(_s select 8) min _native];
        [_patient,_s,_tension] call ACME_fnc_ptxPublish;
    };
    _s
};
private _air=_patient getVariable ["ACM_breathing_Pneumothorax_State",0];
if (!(_air isEqualType 0) || {!finite _air}) then {_air=0;};
_air=_air max 0 min 4;
private _tension=_patient getVariable ["ACM_breathing_TensionPneumothorax_State",false];
if (_tension) then {_air=4;};
private _leak=if (_air>0) then {(_air*0.20) min 0.8} else {0};
private _ncd=if (count (_patient getVariable ["ACME_CS_ncdPlacedSides",[]])>0) then {1} else {0};
_s=[1,_air,_leak,0,if (_tension) then {1} else {0},_ncd,if (_air>0) then {1} else {0},_air,_air min 1];
[_patient,"ACME_ptx_observationRevision",1] call ACME_fnc_setVarNet;
[_patient,_s,_tension] call ACME_fnc_ptxPublish;
_s
