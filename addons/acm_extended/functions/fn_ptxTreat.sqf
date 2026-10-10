/* Owner-local management. No diagnostic/stability popups or hidden-state logs. */
params [["_patient",objNull,[objNull]],["_op","",[""]]];
if (isNull _patient || {!local _patient}) exitWith {};
private _s=[_patient] call ACME_fnc_ptxEnsure;
private _tension=_patient getVariable ["ACM_breathing_TensionPneumothorax_State",false];
private _relief=false;
private _hadPtx = (_s select 1) > 0 || {(_s select 2) > 0} || {_tension};
switch (_op) do {
    case "seal": {
        if (count (_patient getVariable ["ACME_CS_holeData",[]])==0 || {!(missionNamespace getVariable ["ACME_sys_chestSeal",true])}) then {
            [_patient,"ACME_ptx_nativeSealCount",count (_patient getVariable ["ACME_CS_penetratingWounds",[]])] call ACME_fnc_setVarNet;
            [_patient,"ACME_ptx_nativeSealHoleCount",count (_patient getVariable ["ACME_CS_holeData",[]])] call ACME_fnc_setVarNet;
        };
        [_patient,"ACME_CS_sealOcclusion",0] call ACME_fnc_setVarNet;
        [_patient,"ACME_CS_sealVenting",1] call ACME_fnc_setVarNet;
    };
    case "thoraSeal": {
        // Covering a completed finger tract changes its outlet capacity only.
        // Placement preserves air, pressure, injury identity and earned recovery.
        // A fresh vented dressing starts patent under the existing shared-seal
        // model, just as an ordinary newly applied chest seal does.
        [_patient,"ACME_CS_sealOcclusion",0] call ACME_fnc_setVarNet;
        [_patient,"ACME_CS_sealVenting",1] call ACME_fnc_setVarNet;
    };
    case "peel": {
        [_patient,"ACME_ptx_nativeSealCount",-1] call ACME_fnc_setVarNet;
        [_patient,"ACME_ptx_nativeSealHoleCount",-1] call ACME_fnc_setVarNet;
    };
    case "ncd": {_s set [5,1];_relief=true;};
    case "burp": {
        private _context=[_patient] call ACME_fnc_ptxContext;
        _relief=_context select 6;
        [_patient,"ACME_CS_sealOcclusion",0] call ACME_fnc_setVarNet;
        [_patient,"ACME_CS_sealVenting",1] call ACME_fnc_setVarNet;
    };
    case "thora";
    case "tube": {_relief=true;};
    case "thoraAftercare": {_relief=true;};
    // Closing does not heal the leak; remaining actual outlets govern next tick.
    case "close": {_s set [3,0];};
    case "tubeRemoved": {
        // The last tube was actually removed, not just clamped. Once there is no
        // remaining outlet, residual air can reappear from a still-open leak.
        // Do not invent a new PTX after a fully healed injury.
        private _context = [_patient] call ACME_fnc_ptxContext;
        if (!(_context select 5) && {(_s select 2) > 0.000001}) then {
            _s set [8, (_s select 8) max 0.75];
            _s set [1, (_s select 1) max (_s select 8)];
            _s set [3, 0];
        };
    };
};
if (_relief) then {
    _s set [8,(_s select 8) min 0.5];
    _s set [1,(_s select 1) min 1];
    _s set [4,0];
    if !(_op in ["burp", "thoraAftercare"]) then {_s set [3,0];};
    _tension=false;
};
if (_op=="ncd" && {_hadPtx}) then {
    // NCD is temporary needle venting, not definitive finger/thoracostomy
    // drainage. Its residual PTX must remain greater than the 0.5 floor of
    // a patent finger tract, even if both have a separate wound chest seal.
    _s set [8, (_s select 8) max 0.85];
    _s set [1, (_s select 1) max (_s select 8)];
};
if (_op=="tube") then {_s set [8,0];_s set [1,(_s select 1) min 0.25];};
[_patient,_s,_tension] call ACME_fnc_ptxPublish;
private _patients=missionNamespace getVariable ["ACME_clinical_activePatients",[]];
_patients pushBackUnique _patient;
missionNamespace setVariable ["ACME_clinical_activePatients",_patients];
