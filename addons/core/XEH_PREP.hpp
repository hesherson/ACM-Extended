PREP(addVehicleCarryLoadActions);
PREP(addVehiclePatientActions);
PREP(addVehicleUnloadCarryPatientActions);
PREP(beginCarryAssist);
PREP(beginContinuousAction);
PREP(bvmActive);
PREP(canWake);
PREP(requestWake);
PREP(reconcileWake);
PREP(cancelCarryingPrompt);
PREP(canCheckDogtag);
PREP(checkIncompatibleAddons);
PREP(cprActive);
PREP(effectOxygen);
PREP(fullHealLocal);
PREP(generateMedicationTypeMap);
PREP(generateTargetVitals);
PREP(getBleedSeverity);
PREP(getBodyPartString);
PREP(getUp);
PREP(getUpPrompt);
PREP(handleRespawn);
PREP(handleSitting);
PREP(handleCriticalVitals);
PREP(handleFatalVitals);
PREP(handleKnockOut);
PREP(handleTreatmentText);
PREP(initUnit);
PREP(isForcedUnconscious);
PREP(onCardiacArrest);
PREP(onUnconscious);
PREP(progressBarAction);
PREP(resetVariables);
PREP(splitMedicationPack_childActions);
PREP(splitMedicationPack);
PREP(treatmentTextPFH);
PREP(treatmentNative);
PREP(unloadAndCarryPatient);
PREP(setTargetVitalsState);
PREP(setLyingState);
PREP(setWasTreated);
PREP(setContinuousActionActive);
PREP(setContinuousActionState);
PREP(setAceMedicalState);
PREP(setDraggingCapability);
PREP(setCursorInteractionMode);

PREP(continuousHoldRelease);
PREP(registerContinuousRuntime);

PREP(setCargoLoadCapability);
PREP(registerDownedProtectionReason);
PREP(suppressPhysicalBandageReopening);

// Completed loadout replacement boundaries, including owner-local AI/HC.
PREP(equipmentKitChanged);
PREP(registerEquipmentKitRuntime);

// Preserve retired patient carrier contents at explicit kit boundaries.
PREP(carrierLegacySnapshot);
PREP(carrierRetireToWorld);
PREP(carrierKitChanged);
