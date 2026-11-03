uiNamespace setVariable ["ACME_TempusLS_dlg", displayNull];
if (ACME_tempusls_rObj isNotEqualTo ACME_tempusls_cObj) then { deleteVehicle ACME_tempusls_rObj };
ACME_tempusls_cObj = objNull;
ACME_tempusls_rObj = objNull;
private _cam = missionNamespace getVariable ["ACME_tempusls_cam", objNull];
if (!isNull _cam) then {
	_cam cameraEffect ["terminate", "back"];
	camDestroy _cam;
};
ACME_tempusls_cam = objNull;
deleteVehicle (missionNamespace getVariable ["ACME_tempusls_light", objNull]);
ACME_tempusls_light = objNull;
