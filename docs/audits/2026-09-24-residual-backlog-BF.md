# Residual backlog BF: retired final-name UI reconciliation

Parent checkpoint: `692deef6ccb1a8d0b057001b38bd9e8a36b25f42` (residual BE).

The BE focused residual run reduced the modified test set to one failure. The remaining B20 assertion still required retired control IDs `84160/84161` for the old single final-syringe-name UI.

Current behavior deliberately replaced that field with the three-line clinical tag editor:

- pending tag editors use 84601–84603;
- each tag line is capped at 25 characters;
- stored-syringe tag editing uses the current 84460-series editor controls;
- `fn_skFinalName.sqf` is a compatibility shim and returns an empty string without mutating prepared syringe metadata.

BF updates B20 to reuse the current tag-limit and editor-wiring contracts and explicitly protects the absence of 84160/84161.

BF is test/audit-only. No runtime SQF, config, networking, assets, gameplay or release packaging changed.
