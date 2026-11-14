/* Native: append a tagged extension after field 11, preserving foreign tails.
 * Used record: field 10. Prepared carrier: field 12. Never overwrites a live clock. */
params ["_row",["_kind","native"],["_mode","start"],["_seconds",0],["_clock",[]]];
private _out=+_row;
private _index=switch (_kind) do {case "used":{10};case "prepared":{12};default {
    private _tail=if (count _out>12) then {_out select [12]} else {[]};
    private _offset=_tail findIf {!isNil "_x" && {_x isEqualType []} && {(_x param [0,""]) in ["bloodUseV1","bloodUseAgeV1","bloodUseSpoiledV1","bloodUseSpoiledAgeV1"]}};
    if (_offset<0) then {count _out max 12} else {_offset+12}
}};
private _meta=_out param [_index,[]];
if (_mode=="get") exitWith {_meta};
private _blood=if (_kind=="prepared") then {
    private _class=_out param [1,""];(_class find "ACM_BloodBag_")==0 || {(_class find "ACM_FreshBloodBag_")==0}
        || {(_class find "ACE_bloodIV")==0} || {(_out param [8,""]) in ["blood","yset"]}
} else {(_out param [[0,1] select (_kind=="used"),""]) in ["Blood","FreshBlood"]};
private _freshExpired = false;
if (_blood && {["real"] call ACME_fnc_bloodTiming} && {["spoil"] call ACME_fnc_bloodTiming}) then {
    private _donorIndex = switch (_kind) do {case "used":{8};case "prepared":{11};default {10}};
    private _donor = _out param [_donorIndex,[]];
    if (_donor isEqualType [] && {count _donor == 4} && {(_donor select 2) isEqualType 0}) then {
        private _tag = _donor select 0;
        private _age = -1;
        if (_tag == "freshV1") then {_age = ([true] call ACME_fnc_clinicalClock) - (_donor select 2);};
        if (_tag == "freshAgeV1" && {_mode == "restore"}) then {_age = (_donor select 2) + _seconds;};
        _freshExpired = _age >= (["fresh"] call ACME_fnc_bloodTiming);
    };
};
if (_mode=="expired") exitWith {_blood && {_freshExpired || {_meta isNotEqualTo [] && {[_meta,"expired"] call ACME_fnc_bloodUseClock}}}};
if (!_blood || {_meta isEqualTo [] && {(_mode!="set") && {(_mode!="start") || {!(["real"] call ACME_fnc_bloodTiming)}}}}) exitWith {_out};
if (_mode=="set") then {_meta=+_clock;} else {_meta=[_meta,_mode,_seconds] call ACME_fnc_bloodUseClock;};
if (_freshExpired && {_meta isNotEqualTo []}) then {
    _meta set [0,["bloodUseSpoiledV1","bloodUseSpoiledAgeV1"] select (_mode=="snapshot")];
};
if (_kind=="native") then {
    if (count _out<8) then {_out pushBack -1;};
    if (count _out<9) then {_out pushBack "";};
};
private _defaults=switch (_kind) do {
    case "used": {[-1,[],""]};
    case "prepared": {[0,0,[]]};
    default {[_out param [6,0],[],""]};
};
private _base=[9,7] select (_kind=="used");
while {count _out<_index} do {
    private _offset=count _out-_base;
    _out pushBack (_defaults param [_offset,""]);
};
_out set [_index,_meta];
_out
