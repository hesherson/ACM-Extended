# B318 clinical timing

## Server settings

Use the **Server** page of CBA Addon Options and restart the mission. The server reads only the saved Server values and sends the resolved policy to all machines, including join-in-progress players and headless clients. Client and mission overrides do not change the effective policy. A hosted or single-player game uses the host as the server.

| CBA setting | Default |
|---|---:|
| `ACME_medicationTimeScale` | 1.00 |
| `ACME_bloodRealTime` | Enabled |
| `ACME_bloodSpoilEnabled` | Enabled |
| `ACME_persistentCooler1Hours` | 24 h |
| `ACME_persistentCooler2Hours` | 24 h |
| `ACME_persistentCooler4Hours` | 48 h |
| `ACME_bloodStoredWarmHours` | 4 h |
| `ACME_bloodFreshHours` | 24 h |
| `ACME_bloodSpikedHours` | 4 h |
| `ACME_bloodFridgeDays` | 21 days |

`ACME_bloodRealTime` replaces the old opt-in campaign toggle. Existing server overrides for the cooler holdover settings remain valid. An admin can disable real-time blood storage to recover the previous short-mission cooler durations and 30-minute loose-blood clock.

## Medication washout

Native route onset and peak timing still determine when a dose starts working. The amount on board now decays exponentially from representative adult pharmacokinetic references. Clinical washout uses its own clock where redistribution matters. Amiodarone's weeks-long terminal tail does not prolong its immediate IV hemodynamic effect, and residual propofol does not prolong a short bolus's hypnosis. Unknown third-party medications, synthetic overdose records, calcium homeostasis, and the local hyaluronidase response keep their existing models. The native medication history retains its first 15 fields, and the concentrations of the custom infusion trackers use the same reference where applicable. Extended infusion histories coalesce nearby post-peak samples. This is a population-level game model with approximate distribution fractions and a 0.1% residual cutoff.

| Drug | Model reference half-life |
|---|---:|
| Adenosine | 5 s, representative of less than 10 s |
| Epinephrine | 3 min, representative of less than 5 min IV |
| Norepinephrine | 2 min 24 s |
| Esmolol | 9 min |
| Lidocaine | 100 min, with an 8-minute initial phase |
| Amiodarone | 20 days, with a 10-minute early distribution approximation |
| Morphine / TXA | 2 h |
| Fentanyl | 3 h 39 min terminal, with a faster clinical washout |
| Ketamine | 2 h 30 min terminal, with a 12 min 30 s initial phase |
| Midazolam | 3 h terminal |
| Ceftriaxone | 7 h |
| Propofol | 5 h 30 min terminal, with a separate short clinical effect |

## Whole-blood storage and use

The mod models stored refrigerated whole blood as CPD stock. An untouched fridge lot expires after 21 days, and an actual restock counts as a new lot. Carry coolers model validated passive transport, with 24 hours for each compact carrier and 48 hours for the 4U carrier. Actual holdover depends on the carrier and its conditioning. Once the coolant expires, the cooler stops protecting the bags and the warm timer advances at full speed. Re-cooling pauses accumulated warm exposure, and moving or spiking a unit does not give it a fresh warm-use window.

Stored whole blood has a conservative 4-hour limit out of controlled storage. Spiked units stop flowing at 4 hours, or sooner if the stored unit's inherited exposure uses up the window. A walking-blood-bank unit expires 24 hours after collection, even if spiked near that deadline. Spoiled player-carried blood remains in inventory. Refrigerated whole blood is never modeled as frozen.

The fridge shelf-life clock is lot-level. A generic stored-blood inventory item does not carry a printed collection date, so fridge lot age is not an individual manufacturer's expiry date on bags issued to players. The separate ACE plasma item has no frozen/thawed state in this build. Its storage is outside this whole-blood model.

## Persistence

Continue calling the existing medical, cooler and loose-exposure restore APIs with real elapsed offline seconds when campaign time should advance. Native medication timestamps and fresh-blood donor age now advance by that duration as well. Fridge snapshots add elapsed lot seconds and accept the older v1 format. Use `[_fridge,_snapshot,_offlineGameMinutes,_offlineSeconds] call ACME_fnc_bloodFridgeRestore` to advance both the in-game restock schedule and the independent shelf-life clock. Existing three-argument callers still work. An older save with no lot clock starts with zero recorded lot age.

## Clinical references

- [FDA whole blood dating, 21 CFR § 610.53](https://www.law.cornell.edu/cfr/text/21/610.53)
- [AABB Circular of Information](https://www.aabb.org/docs/default-source/default-document-library/resources/circular-of-information-watermark.pdf)
- [Joint Trauma System whole-blood guidance](https://jts.health.mil/assets/docs/cpgs/training/Whole_Blood_Transfusion_CPG_Training_25_Feb_2019.pdf)
- [Prolonged Field Care damage control resuscitation, transport table](https://guidance.nattrauma.org/media/yhejdtb0/damage_control_resuscitation_pfc_01_oct_2018_id73.pdf)
- [FDA epinephrine label](https://www.accessdata.fda.gov/drugsatfda_docs/label/2026/204640Orig1s022lbl.pdf), [DailyMed norepinephrine label](https://dailymed.nlm.nih.gov/dailymed/getFile.cfm?setid=c4de72a8-2a75-4984-ce90-e4870226dc12&type=pdf), [FDA esmolol label](https://www.accessdata.fda.gov/drugsatfda_docs/label/2024/205703s003lbl.pdf) and [DailyMed adenosine label](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=9508caf5-0e3a-4d32-909d-bff7ea40ec30)
- [FDA lidocaine label](https://www.accessdata.fda.gov/drugsatfda_docs/label/2026/017584s044lbl.pdf), [DailyMed amiodarone label](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=e9151c1b-b70c-477b-868a-fffdc5c51830) and [FDA IV amiodarone distribution data](https://www.accessdata.fda.gov/drugsatfda_docs/label/2021/022325s016lbl.pdf)
- [FDA morphine label](https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/202515s046lbl.pdf), [FDA fentanyl label](https://www.accessdata.fda.gov/drugsatfda_docs/label/2026/215870s002lbl.pdf), [FDA ketamine label](https://www.accessdata.fda.gov/drugsatfda_docs/label/2026/016812s057lbl.pdf) and [DailyMed midazolam label](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=78e28b13-414e-4c34-a42c-caf1c3ba1f54)
- [FDA tranexamic acid label](https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/019281s048lbl.pdf), [DailyMed ceftriaxone label](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=53df951b-2eee-44b1-bae2-df7ed85bc0ed) and [Propofol pharmacokinetics](https://ncbi.nlm.nih.gov/sites/books/NBK430884/?report=printable)
