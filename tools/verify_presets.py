#!/usr/bin/env python3
"""Verify every preset in boards.yaml resolves cleanly against a Klipper and
Katapult checkout (offline check — runs `make olddefconfig`, no toolchain
compile). Prints a table and exits non-zero on any dropped/conflicting symbol.

Usage: verify_presets.py --klipper <dir> [--katapult <dir>] [--board <id>]
"""
import argparse
import pathlib
import subprocess
import sys
import tempfile

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent


def olddefconfig(src, cfgfile):
    r = subprocess.run(["make", f"KCONFIG_CONFIG={cfgfile}", "olddefconfig"],
                       cwd=src, capture_output=True, text=True)
    return r


def parse_cfg(path):
    out = {}
    for line in open(path):
        line = line.strip()
        if line.startswith("CONFIG_") and " is not set" in line:
            out[line.split()[1]] = "n"
        elif line.startswith("CONFIG_") and "=" in line:
            k, _, v = line.partition("=")
            out[k] = v
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--klipper", required=True)
    ap.add_argument("--katapult")
    ap.add_argument("--board")
    args = ap.parse_args()

    manifest = yaml.safe_load(open(ROOT / "boards.yaml"))
    fails, table = [], []
    with tempfile.TemporaryDirectory() as td:
        for b in manifest["boards"]:
            if args.board and b["id"] != args.board:
                continue
            for v in b["builds"]:
                kat = v.get("katapult", False)
                src = args.katapult if kat else args.klipper
                if kat and not src:
                    fails.append((b["id"], v["variant"], "no katapult checkout given"))
                    continue
                cfgfile = pathlib.Path(td) / "t.config"
                with open(cfgfile, "w") as fh:
                    for k, val in v["kconfig"].items():
                        fh.write(f"{k}={val}\n")
                r = olddefconfig(src, cfgfile)
                if r.returncode != 0:
                    fails.append((b["id"], v["variant"], "olddefconfig failed: " + r.stderr[-200:]))
                    continue
                final = parse_cfg(cfgfile)
                missing = [k for k in v["kconfig"] if final.get(k) != v["kconfig"][k]]
                if missing:
                    fails.append((b["id"], v["variant"], f"dropped: {missing}"))
                    continue
                mcu = final.get("CONFIG_MCU", "?")
                fa = final.get("CONFIG_FLASH_APPLICATION_ADDRESS", "-")
                ck = final.get("CONFIG_CLOCK_FREQ", "-")
                if kat:
                    srcname = "katapult"
                else:
                    srcname = "klipper"
                table.append(f"{b['id']:<24} {v['variant']:<20} [{srcname}] mcu={mcu:<12} app=0x{int(fa,16):x} clock={ck}")
    print("\n".join(table))
    print(f"\n{len(table)} presets verified OK, {len(fails)} FAILED")
    for f in fails:
        print("FAIL", *f)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
