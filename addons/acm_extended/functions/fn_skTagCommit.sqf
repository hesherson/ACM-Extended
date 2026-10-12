/* B62: persist the three stored-syringe tag lines without repainting the editor on every keystroke.
   Avoiding a render here preserves focus/caret/IME composition while still keeping the stable syringe record live. */
disableSerialization;
private _d=findDisplay 84000;
if(isNull _d)exitWith{};
if (_d getVariable ["ACME_SK_TagEditRetired",false]) exitWith {};
private _store=[ACE_player]call ACME_fnc_skStoreEnsureIds;
private _i=[_store,false]call ACME_fnc_skSelectedIndex;
if(_i<0)exitWith{};
private _entry=+(_store select _i);
private _boundSyringe = _d getVariable ["ACME_SK_TagEditSyringeId",""];
if ((_entry param [13,"",[""]]) == "inventoryB279" || {_boundSyringe != ""}) then {
    private _valid = _boundSyringe == (_entry param [11,"",[""]])
        && {(_d getVariable ["ACME_SK_TagEditSignature",[]]) isEqualTo (_entry select [7,4])}
        && {(_entry param [13,"",[""]]) != "inventoryB279" || {[ACE_player,_entry] call ACME_fnc_skInventoryEditable}};
    if (!_valid) then {_i = -1; _d setVariable ["ACME_SK_TagEditSyringeId",""]; _d setVariable ["ACME_SK_TagEditRetired",true];};
};
if (_i < 0) exitWith {};
while{count _entry<12}do{_entry pushBack "";};
for "_n" from 0 to 2 do{
    private _ctrl=_d displayCtrl(84460+_n);
    private _t=(ctrlText _ctrl) select [0,25];
    _entry set[8+_n,_t];
    if((ctrlText _ctrl)!=_t)then{_ctrl ctrlSetText _t;};
};
_store set[_i,_entry];
[ACE_player, _store] call ACME_fnc_narcStoreCommit;
_d setVariable ["ACME_SK_TagEditSignature",_entry select [7,4]];
if !(uiNamespace getVariable ["ACME_SK_TagEditMode",false]) then {call ACME_fnc_skRefreshDrawn;};
