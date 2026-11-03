private _persistent=missionNamespace getVariable ["ACME_persistentCampaignTiming",false];
ACME_bloodLooseSpoilTime=if (_persistent) then {14400} else {1800};
ACME_coolerThawRateInside=if (_persistent) then {1} else {0.2};
