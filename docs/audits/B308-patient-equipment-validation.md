# B308 source validation

- 504 targeted Python/SQF-VM cases passed: 249 equipment, monitor and cooler
  cases, plus 255 retained transfusion, pressure, litter, inventory navigation,
  identity, journalled deployment and HPMK protection cases.
- New execution cases cover server reservations, duplicated inventory/ACK
  delivery, current-request receipts, guarded refunds, manual monitor reuse,
  four patient headings, elevated surfaces, shared cooler viewer lifetimes,
  full-container spoilage, volume preservation, sensor masking and pad-removal
  therapy gates. Engine objects, inventory commands and RPC are explicit mocked
  boundaries; they do not emulate actual Arma networking.
- The ACCUVAC binary comparison proves that all point positions and normals
  in all ten LODs receive exactly the intended 180-degree X rotation, with other
  mesh bytes preserved. HEMTT successfully reads the resulting model.
- HEMTT 1.23.1 `check --error-on-all` succeeded: 64 addon configs, 2,251 SQF
  files and 15 stringtables. The optional online wiki lookup used the bundled
  fallback. The B308 build contract and whitespace check passed.
- The equipment reference gate resolves 155 literal asset references across
  eight runtime addons. Named remote-execution coverage now checks config
  contributions across addons, including BATDOK and equipment.

The release package includes a separate artifact/signature verification result.
No new Chromium session was available; browser installation failed in this
environment. The existing embedded HTML is unchanged from B307. Source checks
of transparency and actual SQF browser-message tests do not prove native control
rendering. Windows PowerShell, native Addon Builder and Arma/dedicated-server
acceptance remain unexecuted here. See the B308 patch notes for the acceptance
matrix, persistence integration requirements and remaining artwork limitations.
