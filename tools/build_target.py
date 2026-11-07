#!/usr/bin/env python3
"""Build one board variant from a Klipper/Katapult checkout.

Usage:
  build_target.py --board <board-id> --variant <variant> \
      --klipper <dir> [--katapult <dir>] --version <ver> --out <dir>

Writes out/firmware-<board>-<variant>-<version>.bin (or .uf2).
Fails hard if any explicitly requested Kconfig symbol did not survive
`make olddefconfig` (typo'd or wrong-MCU symbol => corrupt preset).
"""
import argparse
import os
import pathlib
import shutil
import subprocess
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent


def run(cmd, cwd, env=None):
    e = dict(os.environ)
    if env:
        e.update(env)
    r = subprocess.run(cmd, cwd=cwd, env=e, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stdout[-4000:] + "\n" + r.stderr[-4000:] + "\n")
        raise SystemExit(f"FAILED: {' '.join(cmd)} (cwd={cwd})")
    return r


def find_build(board_id, variant, manifest):
    for b in manifest["boards"]:
        if b["id"] == board_id:
            for v in b["builds"]:
                if v["variant"] == variant:
                    return b, v
    raise SystemExit(f"unknown board/variant: {board_id}/{variant}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--board", required=True)
    ap.add_argument("--variant", required=True)
    ap.add_argument("--klipper", required=True)
    ap.add_argument("--katapult")
    ap.add_argument("--version", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--jobs", default="4")
    args = ap.parse_args()

    manifest = yaml.safe_load(open(ROOT / "boards.yaml"))
    board, build = find_build(args.board, args.variant, manifest)
    katapult = build.get("katapult", False)
    if katapult and not args.katapult:
        raise SystemExit("katapult variant requires --katapult checkout")
    src = pathlib.Path(args.katapult if katapult else args.klipper).resolve()

    out = pathlib.Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    cfgfile = out / f"config-{args.board}-{args.variant}.config"
    with open(cfgfile, "w") as fh:
        for k, v in build["kconfig"].items():
            fh.write(f"{k}={v}\n")

    run(["make", "clean"], cwd=src)
    run(["make", f"KCONFIG_CONFIG={cfgfile}", "olddefconfig"], cwd=src)

    # Verify every explicitly set symbol survived olddefconfig.
    final = {}
    for line in open(cfgfile):
        line = line.strip()
        if line.startswith("CONFIG_") and "=" in line and "not set" not in line:
            k, _, v = line.partition("=")
            final[k] = v
    missing = [k for k in build["kconfig"] if final.get(k) != build["kconfig"][k]]
    if missing:
        raise SystemExit(
            f"{args.board}/{args.variant}: symbols dropped by olddefconfig "
            f"(invalid for this MCU): {missing}")

    run(["make", f"KCONFIG_CONFIG={cfgfile}", f"-j{args.jobs}"], cwd=src)

    produced = src / "out" / ("katapult.bin" if katapult else "klipper.bin")
    if build.get("postprocess") == "mks_robin":
        wrapped = src / "out" / build["post_output"]
        run([sys.executable, "scripts/update_mks_robin.py",
             str(produced), str(wrapped)], cwd=src)
        produced = wrapped
    if build.get("ext") == "uf2":
        produced = src / "out" / "klipper.uf2"
    if not produced.exists():
        raise SystemExit(f"expected artifact missing: {produced}")

    ext = produced.suffix  # .bin or .uf2
    dest = out / f"firmware-{args.board}-{args.variant}-{args.version}{ext}"
    shutil.copy2(produced, dest)
    shutil.copy2(cfgfile, out / f"{dest.stem}.config")
    print(f"OK {dest.name} ({dest.stat().st_size} bytes)")
    print(f"  mcu={final.get('CONFIG_MCU')} "
          f"flash_start={final.get('CONFIG_FLASH_APPLICATION_ADDRESS')} "
          f"clock={final.get('CONFIG_CLOCK_FREQ')}")


if __name__ == "__main__":
    main()
