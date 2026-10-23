# License notes for distributed firmware binaries

Status: **drafted for review** (task t_a650816d asked for the license
approach to be reviewed before treating this as final).

## Klipper bins

Klipper is GPLv3-or-later (its `COPYING` is GPL-3.0). We compile unmodified
upstream Klipper source at a pinned commit. Distributing the binary requires
making the Corresponding Source available. We satisfy this by:

1. Building only from public, pinned upstream commits; every GitHub release
   names the exact Klipper commit and links to
   `https://github.com/Klipper3d/klipper/tree/<commit>` (complete,
   buildable source).
2. Publishing the exact `KCONFIG_CONFIG` preset used for every bin (attached
   to the release as `firmware-<board>-<variant>-<version>.config` and
   checked into `boards.yaml` / `tools/` in this repo) so anyone can
   reproduce the build with `make`.
3. Our own repo content (workflows, preset manifests, build scripts) is
   licensed GPLv3 via `LICENSE`.

No Klipper source is modified, so no additional source obligations arise
beyond the link to the upstream commit + our build recipes.

## Katapult bins

Katapult (Arksine/katapult) is GPLv3. Same approach: bins built from the
pinned commit named in each release, unmodified upstream source.

## Open review questions

1. Whether distributing "firmware-<board>-<variant>" bins under the A3DP
   brand needs a visible notice in the download portal that Klipper is a
   product of Kevin O'Connor / the Klipper project (trademark/attribution
   courtesy, not a license requirement). Proposed: yes — footer credit line.
2. Whether the release notes' "built by automation, not hardware-tested per
   target" disclaimer is sufficient liability wording. Proposed: also repeat
   it on the download portal.
