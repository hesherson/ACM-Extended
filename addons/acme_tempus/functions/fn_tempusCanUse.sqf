params ["_o"];
!isNull _o && {alive player} && {isNull (uiNamespace getVariable ["ACME_Tempus_dlg", displayNull])} && {_o isEqualTo player || {player distance _o < 3.5}}
