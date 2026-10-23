#!/usr/bin/env python3
"""Generate the download-portal manifest.json from boards.yaml + built bins.

The portal (and per-board SEO pages) fetch this file from the repo's main
branch (raw.githubusercontent.com serves CORS *) and render download links
straight from GitHub release assets.
"""
import argparse
import hashlib
import json
import pathlib

import yaml


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boards", required=True)
    ap.add_argument("--artifacts", required=True)
    ap.add_argument("--version", required=True)
    ap.add_argument("--klipper-commit", required=True)
    ap.add_argument("--katapult-commit", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    manifest = yaml.safe_load(open(args.boards))
    art = pathlib.Path(args.artifacts)

    base = (f"https://github.com/{args.repo}/releases/download/"
            f"klipper-{args.version}")

    def find_asset(board, variant):
        hits = sorted(art.glob(f"firmware-{board}-{variant}-{args.version}.*"))
        return hits[0] if hits else None

    out_boards = []
    missing = []
    for b in manifest["boards"]:
        builds = []
        for v in b["builds"]:
            a = find_asset(b["id"], v["variant"])
            if a is None:
                missing.append(f"{b['id']}/{v['variant']}")
                continue
            cfg = art / f"firmware-{b['id']}-{v['variant']}-{args.version}.config"
            builds.append({
                "variant": v["variant"],
                "katapult": bool(v.get("katapult", False)),
                "interface": "can" if "can" in v["variant"] else "usb",
                "asset": f"{base}/{a.name}",
                "file": a.name,
                "size": a.stat().st_size,
                "sha256": sha256(a),
                "config": (f"{base}/{cfg.name}" if cfg.exists() else None),
            })
        if builds:
            out_boards.append({
                "id": b["id"], "title": b["title"], "chip": b["chip"],
                "flash": b["flash"], "source": b["source"],
                "notes": b.get("notes", []), "warnings": b.get("warnings", []),
                "builds": builds,
            })

    if missing:
        raise SystemExit(f"missing built artifacts for: {missing}")

    doc = {
        "schema": 1,
        "generated_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "repo": f"https://github.com/{args.repo}",
        "klipper_version": args.version,
        "klipper_commit": args.klipper_commit,
        "katapult_commit": args.katapult_commit,
        "source_commits": {
            "klipper": f"https://github.com/Klipper3d/klipper/tree/{args.klipper_commit}",
            "katapult": f"https://github.com/Arksine/katapult/tree/{args.katapult_commit}",
        },
        "flash_methods": manifest["flash_methods"],
        "boards": out_boards,
    }
    with open(args.out, "w") as fh:
        json.dump(doc, fh, indent=1)
    print(f"manifest.json: {len(out_boards)} boards, "
          f"{sum(len(b['builds']) for b in out_boards)} bins")


if __name__ == "__main__":
    main()
