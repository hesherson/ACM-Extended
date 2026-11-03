params ["_o"];
!isNull _o && {!(_o getVariable ["ACME_eq_busy",false])} && {alive player} && {isNull (uiNamespace getVariable ["ACME_TempusLS_dlg", displayNull])} && {_o isEqualTo player || {player distance _o < 3.5}}
