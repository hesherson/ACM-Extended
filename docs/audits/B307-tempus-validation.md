# B307 validation

- HEMTT 1.23.1 `check --error-on-all` succeeded: 64 addon configs rapified, 2,227 SQF files compiled, 15 stringtables checked. Optional online wiki lookup used the bundled database fallback.
- HEMTT `release --no-bin --no-archive` built the complete 27-PBO candidate. All 27 signatures verified against its generated public key. The delivery directory contains only the explicitly expected artifact set and documentation/checksums.
- Packaged Pro, LS and BATDOK HTML bytes match the current source exactly.
- 214 targeted Python/SQF-VM tests cover B306 monitor clinical behavior, 34 B307 feed/charge lifetime cases, retained inventory navigation/cooler transactions/persistence, identity drift rejection, journalled deployment and HPMK protection.
- 183 retained B300–B304 transfusion, pressure and litter tests passed with their historical Git fixtures available.
- Chromium checks passed for all three native browser handshakes, host waveform/sweep/power/signal reset, and BATDOK provider updates. The added LS browser check passed patient switching, clinical-epoch reset, expired authorization removal, retained valid authorization and the initial charge handshake.
- Existing fluid-card browser checks passed at all four retained viewport sizes.
- The imported equipment reference gate resolved 155 literal references across eight runtime addons. No imported models/textures were modified in this update.
- The explicit B307 build contract and `git diff --check` passed.

The 397 targeted tests and Chromium runs do not execute Arma networking, rendering, engine controls or native animations. The downloadable candidate retains MLOD models because Windows Addon Builder/Arma are unavailable here. The Windows source deployment runs the existing normal native release command. Dedicated-server, low-FPS, HC/JIP and real-world placement acceptance remain outstanding as detailed in the B307 patch notes. No claim of universal mod compatibility or completed native multiplayer validation is made.
