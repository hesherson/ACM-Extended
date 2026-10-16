/* B275: change one owner's exact line without toggling a stale UI snapshot. */
params [["_patient",objNull,[objNull]],["_part","",[""]],["_iv",true,[true]],["_site",-1,[0]],["_open",true,[true]]];
if (isNull _patient || {!local _patient}) exitWith {false};
_part = toLowerANSI _part;
private _pi = ACME_infusion_bodyParts find _part;
if (_pi < 0 || {!([_patient,_part,_iv,_site] call ACME_fnc_transfusionAccessValid)}) exitWith {false};
if (_iv) exitWith {
    private _flow = +(_patient getVariable ["ACM_circulation_FluidBagsFlow_IV", []]);
    private _row = +(_flow param [_pi, []]);
    if (_site < 0 || {_site >= count _row}) exitWith {false};
    _row set [_site, [0,1] select _open];
    _flow set [_pi,_row];
    [_patient,[["fluidBagsFlowIV",_flow]],true] call ACM_circulation_fnc_setRuntimeState;
    true
};
private _flow = +(_patient getVariable ["ACM_circulation_FluidBagsFlow_IO", []]);
if (_pi >= count _flow) exitWith {false};
_flow set [_pi,[0,1] select _open];
[_patient,[["fluidBagsFlowIO",_flow]],true] call ACM_circulation_fnc_setRuntimeState;
true
