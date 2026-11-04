# B312 candidate — Tempus mounts and cables

Version 1.2.4.1 / protocol 6. Cumulative on B311.

- Added two Eden/Zeus field mounting trays and server-validated mount/release actions for already deployed Pro/LS monitors. Normal inventory pickup releases the tray first.
- Added explicit USB connection/unplug actions alongside existing wireless pairing. Patient/range/occupancy guards and episode counters fence stale requests.
- Added client-local, bounded patient-lead/USB cable presentation driven by active sensor flags; no physics ropes or visual network traffic.
- Added world schema 2 mount/USB references with schema-1 import support, attachment preflight/rollback and staged-object pickup fencing.
- Reconciles stale patient equipment slots and respects external carry/attachment takeover.
- Fixed a Ventway durable-ID handoff race caused by next-frame native object deletion.

The new trays are generic ACME field props, with no charging simulation. Cable anchors are approximate and cosmetic; native fit/rendering/replication still need acceptance. Read B312-tempus-mounts-cables.md for usage, limits, budgets and updated persistence order. Existing Tempus artwork, UI and clinical authority remain unchanged. No mission autosave backend is installed.
