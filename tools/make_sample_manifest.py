#!/usr/bin/env python3
"""Build a sample manifest.json from boards.yaml (fake assets) for local
browser testing of the download portal widget."""
import hashlib
import json
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
boards = yaml.safe_load(open(ROOT / "boards.yaml"))


def fake_sha(seed):
    return hashlib.sha256(seed.encode()).hexdigest()


out_boards = []
for b in boards["boards"]:
    builds = []
    for v in b["builds"]:
        name = f"firmware-{b['id']}-{v['variant']}-v0.12.0.bin"
        builds.append({
            "variant": v["variant"],
            "katapult": bool(v.get("katapult", False)),
            "interface": "can" if "can" in v["variant"] else "usb",
            "asset": f"https://example.invalid/releases/download/{name}",
            "file": name,
            "size": 200000 + (len(name) * 997) % 150000,
            "sha256": fake_sha(name),
            "config": f"https://example.invalid/releases/download/{name.replace('.bin', '.config')}",
        })
    out_boards.append({
        "id": b["id"], "title": b["title"], "chip": b["chip"],
        "flash": b["flash"], "source": b["source"],
        "notes": b.get("notes", []), "warnings": b.get("warnings", []),
        "builds": builds,
    })

doc = {
    "schema": 1,
    "generated_at": "2026-10-23T00:00:00Z",
    "repo": "https://github.com/Advanced3dPrinting/klipper-firmware-builder",
    "klipper_version": "v0.12.0",
    "klipper_commit": "0" * 40,
    "katapult_commit": "1" * 40,
    "source_commits": {"klipper": "#", "katapult": "#"},
    "flash_methods": boards["flash_methods"],
    "boards": out_boards,
}
dest = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "sample-manifest.json"
dest.write_text(json.dumps(doc, indent=1))
print(f"wrote {dest} ({len(out_boards)} boards)")
