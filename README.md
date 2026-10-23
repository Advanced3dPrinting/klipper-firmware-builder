# klipper-firmware-builder

Curated, CI-built prebuilt Klipper (and Katapult) firmware binaries for the
boards that dominate Klipper installs — built per Klipper release tag, named
`firmware-<board>-<variant>-<klipper-version>.bin`, published to GitHub
Releases, and consumed by the [A3DP download portal](
https://advanced3dprinting.com/pages/klipper-firmware-downloads).

**This repo ships binaries only for presets reviewed in `boards.yaml`.**
There is deliberately no "arbitrary menuconfig" option: every bin corresponds
to a reviewed Kconfig preset whose decision points (MCU, bootloader offset,
clock reference, communication interface) were taken from Klipper's own
`config/` file headers for that board, cross-checked against the
daily-CI-validated configs in
[3dwork-io/klipper_auto_builder_3dwork](https://github.com/3dwork-io/klipper_auto_builder_3dwork)
where a board has no upstream config file.

## Why curated presets

Wrong firmware is the #1 way users brick or misbehave a board (wrong
bootloader offset => no boot; wrong board pin mapping => heaters enabled
unexpectedly). Curated presets + per-board flashing instructions from
Klipper's own config headers are the whole point of this repo.

## How a build works

1. `.github/workflows/build.yml` resolves the Klipper ref:
   - scheduled every 6 h — newest `Klipper3d/klipper` release tag (skipped if
     release `klipper-<tag>` already exists here),
   - `repository_dispatch` with `{tag}` (fired by a release watcher),
   - manual `workflow_dispatch` with any ref (incl. `master` snapshots).
2. The `verify` job runs `tools/verify_presets.py` — every preset in
   `boards.yaml` is pushed through `make KCONFIG_CONFIG=… olddefconfig`
   against the *checked-out* Klipper/Katapult tree; if any curated symbol
   doesn't resolve (renamed, wrong MCU), the run fails before building.
3. The `build` job compiles each target:
   `KCONFIG_CONFIG=<preset> make olddefconfig && make`, applies per-board
   post-processing (e.g. MKS Robin wrapper), and renames the output to
   `firmware-<board>-<variant>-<version>.bin`.
4. The `release` job attaches all bins + a `manifest.json` (asset URLs,
   sha256s, per-board flashing instructions) to the GitHub release, and
   commits `manifest.json` to the repo so the download portal can fetch it
   (raw.githubusercontent.com serves CORS headers; release assets don't).

## Adding a board

1. Find the board's config file in
   [Klipper3d/klipper `config/`](https://github.com/Klipper3d/klipper/tree/master/config)
   and read its header — it states the exact menuconfig decisions.
2. Add a `boards:` entry to `boards.yaml` with the Kconfig symbols, a
   `source:` line quoting that header, and the right flash method.
3. Run `python3 tools/verify_presets.py --klipper <klipper checkout> --katapult <katapult checkout>`
   locally (no ARM toolchain needed).
4. Open a PR. CI re-verifies against the pinned Klipper tree.

Preset provenance values used in `source:`:
- `klipper:` — decision points quoted from the upstream config/ header.
- `3dwork:` — no upstream config file exists; preset taken from the
  3dwork auto-builder's daily-CI-validated `.config`.
- Katapult CAN presets are the community-standard recipe (crystal + CAN pins
  from the board's Klipper config header; Katapult deployed at base of flash
  via DFU, application then flashed at the matching bootloader offset).

## License

- `LICENSE` — GPLv3 (same as Klipper).
- `LICENSE-BUILDS.md` — what that means for these binaries and where the
  Corresponding Source lives (exact upstream commits + our presets).
- Katapult is GPLv3 as well.

## Disclaimer

Firmware is built by automation from reviewed configs but is **not tested on
hardware** per target. Always confirm the board page (MCU variant, bootloader
offset, communication interface) matches your physical board before flashing.
