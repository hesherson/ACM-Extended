uiNamespace setVariable ["ACME_Tempus_dlg", displayNull];
if (ACME_tempus_rObj isNotEqualTo ACME_tempus_cObj) then { deleteVehicle ACME_tempus_rObj };
ACME_tempus_cObj = objNull;
ACME_tempus_rObj = objNull;
private _cam = missionNamespace getVariable ["ACME_tempus_cam", objNull];
if (!isNull _cam) then {
	_cam cameraEffect ["terminate", "back"];
	camDestroy _cam;
};
ACME_tempus_cam = objNull;
deleteVehicle (missionNamespace getVariable ["ACME_tempus_light", objNull]);
ACME_tempus_light = objNull;
