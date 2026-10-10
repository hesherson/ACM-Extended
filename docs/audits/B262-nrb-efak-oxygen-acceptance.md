# B262 — EFAK NRB oxygen compatibility (1.2.4.1 candidate)

## Source changes

- NRB checks the same loose-container sources as before, then asks the EFAK-aware item count **only when EFAK's draw-charge function is present**. The first eligible medic/patient supply donor is retained.
- Native reserve drawing ignores zero-ammo ACM cylinders, allowing another charged cylinder or EFAK's charge-debit fallback to be tried. The NRB request/ACK, session ledger, consumption rate and sound lifecycle are not changed.
- This integrates the compatibility correction raised in community PR #32 on the existing B261 development branch. It does not merge to main or publish a release.

## Dedicated-server acceptance (required)

Server, clients and HC must all run identical B262 files; retain their RPTs.

1. With **no EFAK** and only an ACM oxygen tank shown inside an EFAK-style kit, NRB source eligibility must not change; with a normal charged loose tank, NRB applies and oxygen draws.
2. With EFAK loaded, a charged cylinder **only in the treating medic's kit** must permit NRB on another player, and the oxygen debit must occur on that medic's owner (not the patient or server).
3. With a cylinder **only in the patient's kit**, NRB applied by another medic must debit that patient on its owner, with reserve decreasing over the expected 15 L/min flow.
4. Medic's packed oxygen vs patient's loose oxygen: verify provider-first donor order and only one cylinder decrements per acknowledged NRB charge. Reverse availability and verify patient fallback.
5. An empty loose cylinder plus a charged packed cylinder must use the packed oxygen. With all sources empty, normal NRB mode must refuse placement; Hardcore's permitted no-oxygen mask must still give no SpO2 benefit.
6. Ensure an EFAK cylinder reaches depletion, becomes the expected empty replacement, stops NRB oxygen without free oxygen or infinite retry, and does not debit multiple times under packet lag/provider locality handoff.
7. Regress BVM and other consumers of ACM_breathing_fnc_useOxygenTankReserve: no EFAK, loose full/near-empty/zero cylinders, with and without a packed cylinder; confirm the same reserve accounting.
8. Repeat major B257/B261 clinical/network and transfusion acceptance paths. No unrelated changes to IV, chest, cardiac or transfusion UI behavior.

## Release gate

GitHub strict full regression, native ownership audit, HEMTT check, Windows HEMTT release/signature audit, 2-client dedicated-server/HC test and clean RPT are all required before a public release. CI is not a substitute for EFAK runtime acceptance.
