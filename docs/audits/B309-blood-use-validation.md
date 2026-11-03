# B309 source validation

The selected validation set contains 914 distinct tests:

- 34 B309 cases execute portable use clocks, permanent spoilage, canonical blood
  drainage, source inventory exposure, actual native IV event/owner creation,
  exact-volume returns, medical save/restore, offline ages, prepared/Used owner
  admission, legacy tuples and the equipment death/deletion races.
- 331 retained persistence, fresh-blood, prepared inventory, exact return,
  installed-line, Y-workflow and resource-custody cases pass.
- 45 existing native prepared-carrier transaction cases pass.
- 504 retained B287/B300–B308 equipment, monitor, transfusion, pressure, litter,
  navigation, build-identity and journalled deployment cases pass. The historical
  B303 scope guard was rerun after adding B309's explicitly changed native Add
  Bag path to its permitted set. It passes on the finished source, as do the
  current identity and B301 historical scope contracts.

Tests execute production SQF with explicit engine, config, UI and transport
boundaries. They do not reproduce native Arma object/network behavior. In
particular, stopped/expired blood is tested inside the complete canonical
per-bag integrator; the event handoff then executes the actual owner-side bag
factory. Inventory/config mocks remain distinct from those production decisions.

HEMTT 1.23.1 `check --error-on-all` succeeds: 64 addon configs, 2,254 SQF files
and 15 stringtables. The optional wiki lookup uses its bundled fallback. The
build identity contract and whitespace checks pass. The equipment reference
gate resolves 155 references across eight runtime addons; named remote-call
coverage remains complete.

The release ZIP includes a separate artifact/signature verification result.
No new HTML or model artwork is introduced. Native Arma/dedicated-server,
Windows PowerShell, engine controls and native model binarization remain
unexecuted in this environment. The test candidate retains MLOD models; the
Windows source deploy helper performs the normal native HEMTT release.
