/* Render this assembly in independent layers: original native hub is unchanged.
   An active needle uses the existing Catheter control; remote viewers see ordered milestones. */
params ["_row","_job","_elapsed","_ctrls"];
_ctrls params ["_accessory","_film","_lockCtrl","_secondaryCtrl",["_baseFilm",controlNull]];
private _state=_row param [15,[]];
private _extension=_state param [0,false];
private _dressed=_state param [2,false];
private _line=_state param [3,false];
private _lock=_state param [4,false];
private _gauge=_state param [5,0];
private _action=if (count _job>=7 && {serverTime<=(_job select 6)}) then {_job select 2} else {""};
private _direct=!_extension;
private _accRow=[_row,_direct] call ACME_fnc_ivFieldAccessoryRow;
private _tex=if (_extension) then {
    if (_line) then {"\acm_extended\ui\iv\finish\line_ca.paa"} else {"\acm_extended\ui\iv\finish\extension_ca.paa"}
} else {if (_line) then {"\acm_extended\ui\iv\finish\cursor_line_ca.paa"} else {""}};
if (_action in ["extension","line","flush"]) then {
    if (_action=="extension") then {_accRow=[_row,false] call ACME_fnc_ivFieldAccessoryRow;};
    _tex=[_job select 5,_elapsed] call ACME_fnc_ivFinishFrame;
    if (_direct && {_action=="line"}) then {_tex="\acm_extended\ui\iv\finish\cursor_line_ca.paa";};
    if (_direct && {_action=="flush"}) then {
        private _parts=_tex splitString "\";
        _tex="\acm_extended\ui\iv\field\direct_"+(_parts select ((count _parts)-1));
    };
};
private _pulling=uiNamespace getVariable ["ACME_IV_PullLayers",[]];
private _paint={
    params ["_ctrl","_texture"];
    if (isNull _ctrl || {_ctrl in _pulling}) exitWith {false};
    if ((_ctrl getVariable ["ACME_IV_FinishTexture","-"])!=_texture) then {_ctrl ctrlSetText _texture;_ctrl setVariable ["ACME_IV_FinishTexture",_texture];};
    _ctrl ctrlShow (_texture!="");true
};
if ([_accessory,_tex] call _paint) then {
    [_accessory,_accRow,1052/2048] call ACME_fnc_ivFinishPose;
    _accessory ctrlSetFade (if (_direct && {_action=="line"}) then {1-((_elapsed max 0) min 1)} else {0});_accessory ctrlCommit 0;
};
private _lockTex=if (_lock) then {"\acm_extended\ui\iv\field\lock_ca.paa"} else {""};
if (_action=="lock") then {
    private _f=(floor ((_elapsed max 0)*30)) min 23;
    _lockTex=format ["\acm_extended\ui\iv\field\lock_%1_ca.paa",_f];
};
if ([_lockCtrl,_lockTex] call _paint) then {[_lockCtrl,_row] call ACME_fnc_ivFieldPose;};
private _frame=14;
if (_action in ["field14","field16"]) then {
    _gauge=if (_action=="field14") then {14} else {16};_frame=_job param [7,1];
};
private _d=uiNamespace getVariable ["ACME_IV_DLG",displayNull];
private _localRow=_d getVariable ["ACME_IV_FieldRow",[]];
private _localInsert=(_d getVariable ["ACME_IV_FieldInserting",false]) && {(_localRow param [14,""])==(_row param [14,""])};
private _secondaryTex=if (_gauge>0 && {!_localInsert}) then {[_gauge,_row param [6,""],_frame] call ACME_fnc_ivCathTex} else {""};
if ([_secondaryCtrl,_secondaryTex] call _paint && {_secondaryTex!=""}) then {
    private _child=[_row,_gauge] call ACME_fnc_ivFieldSecondaryRow;
    private _r=uiNamespace getVariable ["ACME_IV_BodyRect",[]];
    [_secondaryCtrl,(_r select 0)+(_r select 2)*(_child select 2),(_r select 1)+(_r select 3)*(_child select 3),_row param [6,""],_row param [13,0]] call ACME_fnc_ivCathPose;
};
// The short primary film remains under the second catheter, including while advancing it.
private _fieldJob=_action in ["field14","field16"];
private _separateBase=!isNull _baseFilm;
private _baseCovered=(_state param [6,false]) || {_fieldJob && {_dressed}};
if ([_baseFilm,if (_baseCovered) then {"\acm_extended\ui\iv\field\dressing_lock_ca.paa"} else {""}] call _paint) then {
    [_baseFilm,_row] call ACME_fnc_ivFieldPose;_baseFilm ctrlSetFade 0;_baseFilm ctrlCommit 0;
};
private _filmTex=if ((_dressed && {!(_fieldJob && {_separateBase})}) || {_action=="dressing"}) then {
    format ["\acm_extended\ui\iv\field\dressing_%1_ca.paa",["lock","field"] select ((_state param [5,0])>0)]
} else {""};
if ([_film,_filmTex] call _paint) then {
    [_film,_row] call ACME_fnc_ivFieldPose;
    _film ctrlSetFade (if (_action=="dressing") then {1-((_elapsed/1.2) max 0 min 1)} else {0});_film ctrlCommit 0;
};
