#include "..\main\script_macros.hpp"
class ACM_MedicalMenu_ActionButton_ACME_AED;
class ACM_MedicalMenu_ActionButton_L_ACME_AED;
class ACM_MedicalMenu_ActionButton_ACME_TempusPro_Item: ACM_MedicalMenu_ActionButton_ACME_AED {
    textureNoShortcut = "\acme_tempus\data\tempus_icon_ca.paa";
};
class ACM_MedicalMenu_ActionButton_L_ACME_TempusPro_Item: ACM_MedicalMenu_ActionButton_L_ACME_AED {
    textureNoShortcut = "\acme_tempus\data\tempus_icon_ca.paa";
};
class ACM_MedicalMenu_ActionButton_ACME_TempusLS_Item: ACM_MedicalMenu_ActionButton_ACME_AED {
    textureNoShortcut = "\acme_tempusls\data\tempusls_icon_ca.paa";
};
class ACM_MedicalMenu_ActionButton_L_ACME_TempusLS_Item: ACM_MedicalMenu_ActionButton_L_ACME_AED {
    textureNoShortcut = "\acme_tempusls\data\tempusls_icon_ca.paa";
};

// Same advanced treatment category as the LifePak. Sensors remain specific to each device.
class ace_medical_treatment_actions {
    class CheckPulse;
    class ACME_TempusProSetup: CheckPulse {
        displayName = "Set Up Tempus Pro";
        displayNameProgress = "Setting up Tempus Pro";
        category = "advanced";
        allowedSelections[] = {"Body"};
        treatmentLocations = 0;
        medicRequired = "ACM_circulation_allowAED";
        treatmentTime = 1.5;
        allowSelfTreatment = 0;
        items[] = {};
        consumeItem = 0;
        condition = "[_medic,_patient,'pro','setup'] call ACME_fnc_equipmentMonitorAction";
        callbackSuccess = "[_medic,_patient,'pro','setup',true] call ACME_fnc_equipmentMonitorAction";
        ACM_menuIcon = "ACME_TempusPro_Item";
    };
    class ACME_TempusLSSetup: ACME_TempusProSetup {
        displayName = "Set Up Tempus LS";
        displayNameProgress = "Setting up Tempus LS";
        condition = "[_medic,_patient,'ls','setup'] call ACME_fnc_equipmentMonitorAction";
        callbackSuccess = "[_medic,_patient,'ls','setup',true] call ACME_fnc_equipmentMonitorAction";
        ACM_menuIcon = "ACME_TempusLS_Item";
    };
    class ACME_TempusProView: ACME_TempusProSetup {
        displayName = "View Tempus Pro";
        displayNameProgress = "";
        treatmentTime = 0.1;
        allowedSelections[] = {"All"};
        condition = "[_medic,_patient,'pro','view'] call ACME_fnc_equipmentMonitorAction";
        callbackSuccess = "[_medic,_patient,'pro','view',true] call ACME_fnc_equipmentMonitorAction";
    };
    class ACME_TempusLSView: ACME_TempusProView {
        displayName = "View Tempus LS";
        condition = "[_medic,_patient,'ls','view'] call ACME_fnc_equipmentMonitorAction";
        callbackSuccess = "[_medic,_patient,'ls','view',true] call ACME_fnc_equipmentMonitorAction";
        ACM_menuIcon = "ACME_TempusLS_Item";
    };
    class ACME_TempusProMeasureBP: ACME_TempusProView {
        displayName = "Measure NIBP (Tempus Pro)";
        allowedSelections[] = {"Body","RightArm"};
        condition = "[_medic,_patient,'pro','nibp'] call ACME_fnc_equipmentMonitorAction";
        callbackSuccess = "[_medic,_patient,'pro','nibp',true] call ACME_fnc_equipmentMonitorAction";
    };
#define ACME_EQUIPMENT_ACTION(NAME,BASE,LABEL,KIND,OP,ICON) \
    class NAME: BASE { \
        displayName = LABEL; \
        displayNameProgress = LABEL; \
        allowedSelections[] = {"Body"}; \
        ACM_menuIcon = ICON; \
        condition = QUOTE([ARR_4(_medic,_patient,KIND,OP)] call ACME_fnc_equipmentMonitorAction); \
        callbackSuccess = QUOTE([ARR_5(_medic,_patient,KIND,OP,true)] call ACME_fnc_equipmentMonitorAction); \
    }
    ACME_EQUIPMENT_ACTION(ACME_TempusProDisconnect,ACME_TempusProView,"Disconnect Tempus Pro",'pro','disconnect',"ACME_TempusPro_Item");
    ACME_EQUIPMENT_ACTION(ACME_TempusLSDisconnect,ACME_TempusLSView,"Disconnect Tempus LS",'ls','disconnect',"ACME_TempusLS_Item");
    ACME_EQUIPMENT_ACTION(ACME_TempusLSPair,ACME_TempusLSView,"Pair Tempus LS with Pro",'ls','pair',"ACME_TempusLS_Item");
    ACME_EQUIPMENT_ACTION(ACME_TempusLSUsb,ACME_TempusLSView,"Connect Tempus USB cable",'ls','usb',"ACME_TempusLS_Item");
    ACME_EQUIPMENT_ACTION(ACME_TempusLSUnplug,ACME_TempusLSView,"Disconnect Tempus USB cable",'ls','unplug',"ACME_TempusLS_Item");
#undef ACME_EQUIPMENT_ACTION

    class ACME_SetDownBloodCooler: ACME_TempusProView {
        displayName = "Set Down Blood Cooler";
        displayNameProgress = "Select Blood Cooler";
        allowedSelections[] = {"Body"};
        medicRequired = 0;
        ACM_menuIcon = "";
        condition = "count ([_medic] call ACME_fnc_coolerRows) > 0";
        callbackSuccess = "[{params ['_medic','_patient']; private _rows = [_medic] call ACME_fnc_coolerRows; if (_rows isNotEqualTo []) then {[(_rows select 0) select 0,_patient] call ACME_fnc_coolerOpenDialog;};},[_medic,_patient],0.1] call CBA_fnc_waitAndExecute";
    };

#define ACME_TEMPUS_SENSOR(NAME,LABEL,KIND,INDEX,ATTACH,PART,TIME,ICON) \
    class NAME: ACME_TempusProSetup { \
        displayName = LABEL; \
        displayNameProgress = LABEL; \
        allowedSelections[] = {PART}; \
        treatmentTime = TIME; \
        ACM_menuIcon = ICON; \
        condition = QUOTE([ARR_4(_medic,_patient,KIND,[ARR_2(INDEX,ATTACH)])] call ACME_fnc_equipmentMonitorAction); \
        callbackSuccess = QUOTE([ARR_5(_medic,_patient,KIND,[ARR_2(INDEX,ATTACH)],true)] call ACME_fnc_equipmentMonitorAction); \
    }
    ACME_TEMPUS_SENSOR(ACME_TempusProECGAttach,"Attach ECG leads (Tempus Pro)",'pro',0,true,"Body",3,"ACME_TempusPro_Item");
    ACME_TEMPUS_SENSOR(ACME_TempusProECGRemove,"Remove ECG leads (Tempus Pro)",'pro',0,false,"Body",1,"ACME_TempusPro_Item");
    ACME_TEMPUS_SENSOR(ACME_TempusProSpO2Attach,"Attach SpO2 sensor (Tempus Pro)",'pro',1,true,"RightArm",2,"ACME_TempusPro_Item");
    ACME_TEMPUS_SENSOR(ACME_TempusProSpO2Remove,"Remove SpO2 sensor (Tempus Pro)",'pro',1,false,"RightArm",1,"ACME_TempusPro_Item");
    ACME_TEMPUS_SENSOR(ACME_TempusProNIBPAttach,"Attach NIBP cuff (Tempus Pro)",'pro',2,true,"RightArm",3,"ACME_TempusPro_Item");
    ACME_TEMPUS_SENSOR(ACME_TempusProNIBPRemove,"Remove NIBP cuff (Tempus Pro)",'pro',2,false,"RightArm",1,"ACME_TempusPro_Item");
    ACME_TEMPUS_SENSOR(ACME_TempusProCapnoAttach,"Attach EtCO2 line (Tempus Pro)",'pro',3,true,"Head",3,"ACME_TempusPro_Item");
    ACME_TEMPUS_SENSOR(ACME_TempusProCapnoRemove,"Remove EtCO2 line (Tempus Pro)",'pro',3,false,"Head",1,"ACME_TempusPro_Item");
    ACME_TEMPUS_SENSOR(ACME_TempusProTemperatureAttach,"Attach temperature probe (Tempus Pro)",'pro',4,true,"Body",2,"ACME_TempusPro_Item");
    ACME_TEMPUS_SENSOR(ACME_TempusProTemperatureRemove,"Remove temperature probe (Tempus Pro)",'pro',4,false,"Body",1,"ACME_TempusPro_Item");
    ACME_TEMPUS_SENSOR(ACME_TempusLSECGAttach,"Attach ECG leads (Tempus LS)",'ls',0,true,"Body",3,"ACME_TempusLS_Item");
    ACME_TEMPUS_SENSOR(ACME_TempusLSECGRemove,"Remove ECG leads (Tempus LS)",'ls',0,false,"Body",1,"ACME_TempusLS_Item");
    ACME_TEMPUS_SENSOR(ACME_TempusLSPadsAttach,"Attach defibrillator pads (Tempus LS)",'ls',5,true,"Body",3,"ACME_TempusLS_Item");
    ACME_TEMPUS_SENSOR(ACME_TempusLSPadsRemove,"Remove defibrillator pads (Tempus LS)",'ls',5,false,"Body",1,"ACME_TempusLS_Item");
#undef ACME_TEMPUS_SENSOR
};
