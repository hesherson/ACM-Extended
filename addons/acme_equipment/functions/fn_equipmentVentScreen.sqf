/* Local, read-only world display. Only nearby deployed ventilators render a UI texture. */
params ["_o"];
private _p=_o getVariable ["ACME_eq_patient",objNull];
if (isNull _p || {_o distance ACE_player>8}) exitWith {};
private _on=_p getVariable ["ACME_vent_powerOn",false];
if (!_on) exitWith {_o setVariable ["ACME_eq_screenTexture",""];_o setObjectTexture [1,"\\acme_ventway\\data\\ventway_screen_off_co.paa"];};
private _name="ACME_VentwayWorld_"+((netId _o splitString ":") joinString "_");
private _texture=format ["#(argb,512,256,1)ui('RscDisplayEmpty','%1')",_name];
if ((_o getVariable ["ACME_eq_screenTexture",""])!=_texture) then {_o setVariable ["ACME_eq_screenTexture",_texture];_o setObjectTexture [1,_texture];};
private _display=findDisplay _name;
if (isNull _display) exitWith {};
private _control=_display getVariable ["ACME_readout",controlNull];
if (isNull _control) then {
    _control=_display ctrlCreate ["RscStructuredText",-1];
    _control ctrlSetPosition [0,0,1,1];_control ctrlCommit 0;
    _control ctrlSetBackgroundColor [0.01,0.03,0.02,1];
    _display setVariable ["ACME_readout",_control];
};
private _rate=_p getVariable ["ACME_vent_bpm",12];
private _vt=_p getVariable ["ACME_vent_vt",500];
private _peep=_p getVariable ["ACME_vent_peep",5];
private _fio2=(_p getVariable ["ACME_vent_fio2",21]);
_control ctrlSetStructuredText parseText format ["<t font='RobotoCondensed' color='#98ffb6' size='1.1'>VENTWAY SPARROW<br/>RR %1 /min  |  VT %2 mL<br/>PEEP %3 cmH2O<br/>FiO2 %4%%</t>",_rate,_vt,_peep,_fio2];
