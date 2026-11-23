class CfgVehicles {
    class Module_F;

    class ACME_ModuleBase_Zeus: Module_F {
        curatorCanAttach = 1;
        category = "ACME_Curator_Category";
        displayName = "Module";
        icon = QACEPATHTOF(zeus,ui\Icon_Module_Zeus_Heal_ca.paa);
        functionPriority = 1;
        isGlobal = 1;
        isTriggerActivated = 0;
        scope = 1;
        scopeCurator = 2;
    };

    class ACME_ModuleUnCardiacArrest: ACME_ModuleBase_Zeus {
        displayName = CSTRING(Module_UnCardiacArrest);
        function = QFUNC(unCardiacArrest);
    };
    class ACME_ModuleForceWakeUp: ACME_ModuleBase_Zeus {
        displayName = CSTRING(Module_ForceWakeUp);
        function = QFUNC(forceWakeUp);
        icon = QACEPATHTOF(zeus,ui\Icon_Module_Zeus_Heal_ca.paa);
    };
    class ACME_ModuleSetBloodVolume: ACME_ModuleBase_Zeus {
        displayName = CSTRING(Module_SetBloodVolume);
        icon = QPATHTOF(ui\Icon_Module_BloodVolume_ca.paa);
        curatorInfoType = QGVAR(RscSetBloodVolume);
    };
    class ACME_ModuleInflictCardiacArrest: ACME_ModuleBase_Zeus {
        displayName = CSTRING(Module_InflictCardiacArrest);
        icon = QPATHTOF(ui\Icon_Module_CardiacArrest_ca.paa);
        curatorInfoType = QGVAR(RscInflictCardiacArrest);
    };
    class ACME_ModuleInflictChestInjury: ACME_ModuleBase_Zeus {
        displayName = CSTRING(Module_InflictChestInjury);
        icon = QPATHTOF(ui\Icon_Module_ChestInjury_ca.paa);
        curatorInfoType = QGVAR(RscInflictChestInjury);
    };
    class ACME_ModuleGivePain: ACME_ModuleBase_Zeus {
        displayName = CSTRING(Module_GivePain);
        icon = QPATHTOF(ui\Icon_Module_GivePain_ca.paa);
        curatorInfoType = QGVAR(RscGivePain);
    };
    class ACME_ModuleSetOxygen: ACME_ModuleBase_Zeus {
        displayName = CSTRING(Module_SetOxygen);
        icon = QPATHTOF(ui\Icon_Module_SetOxygen_ca.paa);
        curatorInfoType = QGVAR(RscSetOxygen);
    };
    class ACME_ModuleSetBloodType: ACME_ModuleBase_Zeus {
        displayName = CSTRING(Module_SetBloodType);
        icon = QPATHTOF(ui\Icon_Module_SetBloodType_ca.paa);
        curatorInfoType = QGVAR(RscSetBloodType);
    };
    class ACME_ModuleTogglePlotArmor: ACME_ModuleBase_Zeus {
        displayName = CSTRING(Module_PlotArmor);
        function = QFUNC(togglePlotArmor);
        icon = QPATHTOF(ui\Icon_Module_PlotArmor_ca.paa);
    };
    class ACME_ModuleAssignFullHealFacility: ACME_ModuleBase_Zeus {
        displayName = CSTRING(Module_AssignFullHealFacility);
        function = QFUNC(assignFullHealFacility);
        icon = QPATHTOEF(mission,ui\Icon_Module_FullHealFacility_ca.paa);
    };
};
