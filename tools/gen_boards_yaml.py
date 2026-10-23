#!/usr/bin/env python3
"""Generate boards.yaml — the curated board/variant manifest.

Every variant line in this file was written by hand from a verified source:
  - klipper:  menuconfig decisions quoted from the board's config file header
              in Klipper3d/klipper config/ (upstream config/ dir)
  - 3dwork:   cross-checked against 3dwork-io/klipper_auto_builder_3dwork
              boards/<id>/firmware.config (daily CI-built against klipper master)
  - community: community-standard recipe (CAN toolhead Katapult/Klipper CAN),
              marked with lower confidence — flagged in the site UI.

Only symbols that exist in Klipper's Kconfig for the chosen MCU are used;
`make olddefconfig` + the verify step in tools/verify_presets.py enforces this.
"""
import yaml

# --- Kconfig fragment builders --------------------------------------------
def frag(mcu, flash, clock, comm, extra=None, low_level=True):
    """mcu: MACH_* symbol base e.g. STM32F446; flash: FLASH_START symbol suffix;
    clock: CLOCK_REF suffix (or None for rp2040); comm: list of comm symbols."""
    f = {"CONFIG_LOW_LEVEL_OPTIONS": "y", "CONFIG_MACH_STM32": "y"}
    f["CONFIG_MACH_" + mcu] = "y"
    if flash:
        f["CONFIG_STM32_FLASH_START_" + flash] = "y"
    if clock:
        f["CONFIG_STM32_CLOCK_REF_" + clock] = "y"
    for c in comm:
        f["CONFIG_" + c] = "y"
    if extra:
        f.update(extra)
    return f

def can_frag(mcu, flash, clock, can_sym, freq, extra=None):
    e = {"CONFIG_CANBUS_FREQUENCY": str(freq)}
    if extra:
        e.update(extra)
    return frag(mcu, flash, clock, [can_sym], extra=e)

def katapult_frag(mcu, clock, can_sym, freq):
    # Katapult deployed at base of flash via DFU (FLASH_START_0000 = plain
    # katapult, not the deployer). Klipper then uses the matching app offset.
    return {
        "CONFIG_LOW_LEVEL_OPTIONS": "y",
        "CONFIG_MACH_STM32": "y",
        "CONFIG_MACH_" + mcu: "y",
        "CONFIG_STM32_FLASH_START_0000": "y",
        "CONFIG_STM32_CLOCK_REF_" + clock: "y",
        "CONFIG_" + can_sym: "y",
        "CONFIG_CANBUS_FREQUENCY": str(freq),
    }

USB = "STM32_USB_PA11_PA12"
U1 = "STM32_SERIAL_USART1"
U3 = "STM32_SERIAL_USART3"

def can_speeds(can_sym, kat, freqs=(1000000, 500000)):
    out = []
    for fq in freqs:
        out.append({"variant": f"can-{fq//1000}k", "interface": "can",
                    "kconfig": can_frag, "kconfig_args": can_sym, "freq": fq, "katapult": False})
    return out

boards = []

def B(id_, title, slug_title, chip, variants, flash, source, notes=None, warnings=None):
    for v in variants:
        if callable(v["kconfig"]):
            args = v.pop("kconfig_args", None)
            if args is not None:
                v["kconfig"] = v["kconfig"](can_sym=args, freq=v.get("freq"))
            else:
                v["kconfig"] = v["kconfig"]()
        v.pop("kconfig_args", None)
        v.pop("freq", None)
    boards.append({
        "id": id_, "title": title, "chip": chip, "builds": variants,
        "flash": flash, "source": source, "notes": notes or [], "warnings": warnings or [],
    })

# ---------------------------------------------------------------- BTT Octopus
B("btt-octopus-1.1", "BTT Octopus v1.1 (non-Pro)", "octopus", "STM32F446/F429", [
    {"variant": "f446-usb", "kconfig": frag("STM32F446", "8000", "12M", [USB])},
    {"variant": "f429-usb", "kconfig": frag("STM32F429", "8000", "8M", [USB])},
], "sd-firmware-bin",
    "klipper: config/generic-bigtreetech-octopus-v1.1.cfg — F446: 32KiB bootloader + 12MHz; F429: 32KiB + 8MHz. Cross-checked 3dwork btt-octopus-11 (F446).",
    warnings=["Octopus v1.1 (non-Pro) bins must NOT be used on an Octopus Pro v1.1 — wrong pin mapping can enable a heater inadvertently."])

B("btt-octopus-pro-1.0", "BTT Octopus Pro v1.0", "octopus-pro", "STM32F446/F429/H723", [
    {"variant": "f446-usb", "kconfig": frag("STM32F446", "8000", "12M", [USB])},
    {"variant": "f429-usb", "kconfig": frag("STM32F429", "8000", "8M", [USB])},
    {"variant": "h723-usb", "kconfig": frag("STM32H723", "20000", "25M", [USB])},
], "sd-firmware-bin",
    "klipper: config/generic-bigtreetech-octopus-pro-v1.0.cfg — F446: 32KiB+12MHz; F429: 32KiB+8MHz; H723: 128KiB+25MHz. Cross-checked 3dwork btt-octopus-pro-446/h723.",
    warnings=["Octopus Pro v1.0 bins must not be used on Octopus Pro v1.1 or the non-Pro Octopus."])

B("btt-octopus-pro-1.1", "BTT Octopus Pro v1.1", "octopus-pro", "STM32H723", [
    {"variant": "h723-usb", "kconfig": frag("STM32H723", "20000", "25M", [USB])},
], "sd-firmware-bin",
    "klipper: config/generic-bigtreetech-octopus-pro-v1.1.cfg — H723: 128KiB bootloader + 25MHz crystal.",
    warnings=["Octopus Pro v1.1 bins must not be used on Octopus Pro v1.0 or the non-Pro Octopus."])

B("btt-octopus-max-ez", "BTT Octopus Max EZ", "octopus-max-ez", "STM32H723", [
    {"variant": "usb", "kconfig": frag("STM32H723", "20000", "25M", [USB])},
    {"variant": "can-1m", "kconfig": lambda **k: can_frag("STM32H723", "20000", "25M", "STM32_MMENU_CANBUS_PD0_PD1", 1000000)},
    {"variant": "can-500k", "kconfig": lambda **k: can_frag("STM32H723", "20000", "25M", "STM32_MMENU_CANBUS_PD0_PD1", 500000)},
    {"variant": "katapult-can-1m", "kconfig": katapult_frag("STM32H723", "25M", "STM32_MMENU_CANBUS_PD0_PD1", 1000000), "katapult": True},
    {"variant": "katapult-can-500k", "kconfig": katapult_frag("STM32H723", "25M", "STM32_MMENU_CANBUS_PD0_PD1", 500000), "katapult": True},
], "sd-firmware-bin",
    "klipper: config/generic-bigtreetech-octopus-max-ez.cfg — H723, 128KiB, 25MHz, USB or CAN (PD0/PD1). Katapult: community recipe (CAN on PD0/PD1).",
    notes=["CAN/Katapult variants are for use behind a USB-CAN bridge or USB-CAN-bridge mode."])

# ---------------------------------------------------------------- BTT SKR line
B("btt-skr-2", "BTT SKR 2", "skr-2", "STM32F407/F429", [
    {"variant": "f407-usb", "kconfig": frag("STM32F407", "8000", "8M", [USB])},
    {"variant": "f429-usb", "kconfig": frag("STM32F429", "8000", "8M", [USB])},
], "sd-firmware-bin",
    "klipper: config/generic-bigtreetech-skr-2.cfg — STM32F407 (older) or F429 (late-2021+), 32KiB bootloader. Cross-checked 3dwork btt-skr-2-407/429.",
    warnings=["Check the chip silkscreened on your board to pick F407 vs F429. Early SKR 2 rev has a heater-power flaw — verify your board revision."])

B("btt-skr-3", "BTT SKR 3", "skr-3", "STM32H723/H743", [
    {"variant": "h723-usb", "kconfig": frag("STM32H723", "20000", "25M", [USB])},
    {"variant": "h743-usb", "kconfig": frag("STM32H743", "20000", "25M", [USB])},
], "sd-firmware-bin",
    "klipper: config/generic-bigtreetech-skr-3.cfg — H743 or H723, 128KiB bootloader, 25MHz. Cross-checked 3dwork btt-skr-3-h723.",
    warnings=["Check the chip on your board to pick H723 vs H743."])

B("btt-skr-3-ez", "BTT SKR 3 EZ", "skr-3-ez", "STM32H723", [
    {"variant": "h723-usb", "kconfig": frag("STM32H723", "20000", "25M", [USB])},
], "sd-firmware-bin",
    "3dwork: boards/btt-skr-3-ez-h723/firmware.config — H723, 128KiB, 25MHz, USB. (No separate upstream config/ file for the EZ.)")

B("btt-skr-mini-e3-v1.2", "BTT SKR mini E3 v1.2", "skr-mini-e3", "STM32F103", [
    {"variant": "usb", "kconfig": frag("STM32F103", "7000", None, [USB], extra={"CONFIG_INITIAL_PINS": '"!PC13"'})},
], "sd-firmware-bin",
    "klipper: config/generic-bigtreetech-skr-mini-e3-v1.2.cfg — F103, 28KiB bootloader, USB, startup GPIO !PC13.")

B("btt-skr-mini-e3-v2.0", "BTT SKR mini E3 v2.0", "skr-mini-e3", "STM32F103", [
    {"variant": "usb", "kconfig": frag("STM32F103", "7000", None, [USB], extra={"CONFIG_INITIAL_PINS": '"!PA14"'})},
], "sd-firmware-bin",
    "klipper: config/generic-bigtreetech-skr-mini-e3-v2.0.cfg — F103, 28KiB bootloader, USB, startup GPIO !PA14.")

B("btt-skr-mini-e3-v3.0", "BTT SKR mini E3 v3.0", "skr-mini-e3", "STM32G0B1", [
    {"variant": "usb", "kconfig": frag("STM32G0B1", "2000", "8M", [USB])},
], "sd-firmware-bin",
    "klipper: config/generic-bigtreetech-skr-mini-e3-v3.0.cfg — G0B1, 8KiB bootloader, USB.")

B("btt-skr-cr6", "BTT SKR CR6 v1.0", "skr-cr6", "STM32F103", [
    {"variant": "usb", "kconfig": frag("STM32F103", "7000", None, [USB], extra={"CONFIG_INITIAL_PINS": '"!PA14"'})},
], "sd-firmware-bin",
    "klipper: config/generic-bigtreetech-skr-cr6-v1.0.cfg — F103, 28KiB bootloader, USB, startup GPIO !PA14.")

B("btt-manta-m4p", "BTT Manta M4P", "manta", "STM32G0B1", [
    {"variant": "usb", "kconfig": frag("STM32G0B1", "2000", "8M", [USB])},
], "sd-firmware-bin",
    "klipper: config/generic-bigtreetech-manta-m4p.cfg — G0B1, 8KiB bootloader, USB. Cross-checked 3dwork btt-manta-m4p.")

B("btt-manta-m5p", "BTT Manta M5P", "manta", "STM32G0B1", [
    {"variant": "usb", "kconfig": frag("STM32G0B1", "2000", "8M", [USB])},
    {"variant": "can-1m", "kconfig": lambda **k: can_frag("STM32G0B1", "2000", "8M", "STM32_MMENU_CANBUS_PD0_PD1", 1000000)},
    {"variant": "can-500k", "kconfig": lambda **k: can_frag("STM32G0B1", "2000", "8M", "STM32_MMENU_CANBUS_PD0_PD1", 500000)},
    {"variant": "katapult-can-1m", "kconfig": katapult_frag("STM32G0B1", "8M", "STM32_MMENU_CANBUS_PD0_PD1", 1000000), "katapult": True},
    {"variant": "katapult-can-500k", "kconfig": katapult_frag("STM32G0B1", "8M", "STM32_MMENU_CANBUS_PD0_PD1", 500000), "katapult": True},
], "sd-firmware-bin",
    "klipper: config/generic-bigtreetech-manta-m5p.cfg — G0B1, 8KiB, 8MHz, USB or CAN (PD0/PD1). Katapult: community recipe.")

B("btt-manta-m8p-v1.1", "BTT Manta M8P v1.1", "manta", "STM32G0B1", [
    {"variant": "usb", "kconfig": frag("STM32G0B1", "2000", "8M", [USB])},
    {"variant": "can-1m", "kconfig": lambda **k: can_frag("STM32G0B1", "2000", "8M", "STM32_MMENU_CANBUS_PD12_PD13", 1000000)},
    {"variant": "can-500k", "kconfig": lambda **k: can_frag("STM32G0B1", "2000", "8M", "STM32_MMENU_CANBUS_PD12_PD13", 500000)},
    {"variant": "katapult-can-1m", "kconfig": katapult_frag("STM32G0B1", "8M", "STM32_MMENU_CANBUS_PD12_PD13", 1000000), "katapult": True},
    {"variant": "katapult-can-500k", "kconfig": katapult_frag("STM32G0B1", "8M", "STM32_MMENU_CANBUS_PD12_PD13", 500000), "katapult": True},
], "sd-firmware-bin",
    "klipper: config/generic-bigtreetech-manta-m8p-v1.1.cfg — G0B1, 8KiB, 8MHz, USB or CAN (PD12/PD13). Katapult: community recipe.")

B("btt-manta-e3-ez", "BTT Manta E3 EZ", "manta", "STM32G0B1", [
    {"variant": "usb", "kconfig": frag("STM32G0B1", "2000", "8M", [USB])},
], "sd-firmware-bin",
    "3dwork: boards/btt-manta-e3ez/firmware.config — G0B1, 8KiB, USB. Cross-checked against upstream generic-bigtreetech-manta-e3ez.cfg pin file.")

B("btt-skr-pico", "BTT SKR Pico v1.0", "skr-pico", "RP2040", [
    {"variant": "usb", "kconfig": {"CONFIG_MACH_RPXXXX": "y", "CONFIG_MACH_RP2040": "y", "CONFIG_USB": "y"}, "ext": "uf2"},
], "rp2040-uf2",
    "klipper: config/generic-bigtreetech-skr-pico-v1.0.cfg — RP2040, USB. Output is klipper.uf2 (BOOTSEL mass-storage flash).")

B("btt-skrat-1.0", "BTT SKRat V1.0", "skrat", "STM32G0B1", [
    {"variant": "usb", "kconfig": frag("STM32G0B1", "2000", "8M", [USB], extra={"CONFIG_INITIAL_PINS": '"PA4"'})},
], "sd-firmware-bin",
    "3dwork: boards/btt-skrat-10/firmware.config — G0B1, 8KiB, 8MHz, USB, startup GPIO PA4. (No upstream config/ file.)")

# ---------------------------------------------------------------- Toolheads
for tid, tname, slug in [("btt-ebb36-v1.2", "BTT EBB36 v1.2 (EBBCan)", "ebb36"),
                          ("btt-ebb42-v1.2", "BTT EBB42 v1.2 (EBBCan)", "ebb42")]:
    B(tid, tname, slug, "STM32G0B1", [
        {"variant": "usb", "kconfig": frag("STM32G0B1", "0000", "8M", [USB])},
        {"variant": "can-1m", "kconfig": lambda **k: can_frag("STM32G0B1", "2000", "8M", "STM32_MMENU_CANBUS_PB0_PB1", 1000000)},
        {"variant": "can-500k", "kconfig": lambda **k: can_frag("STM32G0B1", "2000", "8M", "STM32_MMENU_CANBUS_PB0_PB1", 500000)},
        {"variant": "katapult-can-1m", "kconfig": katapult_frag("STM32G0B1", "8M", "STM32_MMENU_CANBUS_PB0_PB1", 1000000), "katapult": True},
        {"variant": "katapult-can-500k", "kconfig": katapult_frag("STM32G0B1", "8M", "STM32_MMENU_CANBUS_PB0_PB1", 500000), "katapult": True},
    ], "dfu-toolhead",
        "klipper: sample-bigtreetech-ebb-canbus-v1.2.cfg — G0B1, 8MHz, USB or CAN (PB0/PB1). USB variant: 3dwork btt-ebb36-12 (no bootloader, DFU flash). CAN: 8KiB offset for Katapult app. Katapult: community recipe.",
        notes=["EBB36 and EBB42 v1.2 use the same firmware; pick your board's page for matching instructions."])

B("btt-ebb-sb-can", "BTT EBB SB2209/SB2240 (CAN)", "ebb-sb", "STM32G0B1", [
    {"variant": "usb", "kconfig": frag("STM32G0B1", "0000", "8M", [USB])},
    {"variant": "can-1m", "kconfig": lambda **k: can_frag("STM32G0B1", "2000", "8M", "STM32_MMENU_CANBUS_PB0_PB1", 1000000)},
    {"variant": "can-500k", "kconfig": lambda **k: can_frag("STM32G0B1", "2000", "8M", "STM32_MMENU_CANBUS_PB0_PB1", 500000)},
    {"variant": "katapult-can-1m", "kconfig": katapult_frag("STM32G0B1", "8M", "STM32_MMENU_CANBUS_PB0_PB1", 1000000), "katapult": True},
    {"variant": "katapult-can-500k", "kconfig": katapult_frag("STM32G0B1", "8M", "STM32_MMENU_CANBUS_PB0_PB1", 500000), "katapult": True},
], "dfu-toolhead",
    "klipper: sample-bigtreetech-ebb-sb-canbus-v1.0.cfg — G0B1, 8MHz, USB or CAN (PB0/PB1). Katapult: community recipe.")

for tid, tname, slug in [("mellow-fly-sht36", "Mellow Fly SHT36", "fly-sht36"),
                          ("mellow-fly-sht42", "Mellow Fly SHT42", "fly-sht42")]:
    B(tid, tname, slug, "STM32F072", [
        {"variant": "usb", "kconfig": frag("STM32F072", "0000", "8M", [USB])},
        {"variant": "can-1m", "kconfig": lambda **k: can_frag("STM32F072", "2000", "8M", "STM32_CANBUS_PA11_PA12", 1000000)},
        {"variant": "can-500k", "kconfig": lambda **k: can_frag("STM32F072", "2000", "8M", "STM32_CANBUS_PA11_PA12", 500000)},
        {"variant": "katapult-can-1m", "kconfig": katapult_frag("STM32F072", "8M", "STM32_CANBUS_PA11_PA12", 1000000), "katapult": True},
        {"variant": "katapult-can-500k", "kconfig": katapult_frag("STM32F072", "8M", "STM32_CANBUS_PA11_PA12", 500000), "katapult": True},
    ], "dfu-toolhead",
        "3dwork: boards/mellow-fly-sht-36 / sht-42/firmware.config — STM32F072 (not G0B1), 8MHz, USB (no bootloader, DFU flash). CAN (PA11/PA12) + Katapult: community recipe.",
        notes=["The SHT36/42 use an STM32F072 — a very common mistake is selecting G0B1 in menuconfig."])

# ---------------------------------------------------------------- Third-party
B("fysetc-spider", "FYSETC Spider v1.x", "spider", "STM32F446", [
    {"variant": "no-bootloader-usb", "kconfig": frag("STM32F446", "0000", "12M", [USB])},
    {"variant": "32k-bootloader-usb", "kconfig": frag("STM32F446", "8000", "12M", [USB])},
], "spider",
    "klipper: config/generic-fysetc-spider.cfg — F446, 12MHz, flash to 0x08000000 (no bootloader). 3dwork builds with 32KiB bootloader (Spider v1.1 with bootloader) — both variants provided; check which your board boots.",
    warnings=["Picking the wrong bootloader offset for your Spider revision means the board will not boot the firmware (no damage; re-flash the other variant)."])

B("mks-robin-nano-v2", "MKS Robin Nano V2", "robin-nano", "STM32F103", [
    {"variant": "usart3", "kconfig": frag("STM32F103", "7000", None, [U3]),
     "postprocess": "mks_robin", "post_output": "Robin_nano35.bin"},
], "mks-robin",
    "klipper: config/generic-mks-robin-nano-v2.cfg — F103, 28KiB bootloader, USART3 PB11/PB10, output wrapped via scripts/update_mks_robin.py.")

B("mks-robin-nano-v3", "MKS Robin Nano V3", "robin-nano", "STM32F407", [
    {"variant": "usb", "kconfig": frag("STM32F407", "C000", "8M", [USB])},
], "sd-firmware-bin",
    "klipper: config/generic-mks-robin-nano-v3.cfg — F407, 48KiB bootloader, USB. Cross-checked 3dwork mks-robin-nano-30.")

B("ldo-leviathan-v1.2", "LDO Leviathan v1.2", "leviathan", "STM32F446", [
    {"variant": "usb", "kconfig": frag("STM32F446", "8000", "12M", [USB])},
], "dfu-board",
    "klipper: config/generic-ldo-leviathan-v1.2.cfg — F446, 32KiB bootloader, 12MHz, USB.",
    notes=["3dwork builds this board with no bootloader offset (DFU flash); we follow Klipper's own header (32KiB bootloader). If your Leviathan has no bootloader, use DFU and report back."])

B("creality-4.2.2", "Creality 4.2.2 (Ender 3 V2 and similar)", "creality-4.2.2", "STM32F103", [
    {"variant": "usart1", "kconfig": frag("STM32F103", "7000", None, [U1])},
    {"variant": "usart3", "kconfig": frag("STM32F103", "7000", None, [U3])},
], "sd-firmware-bin",
    "klipper: config/printer-creality-ender3-v2-2020.cfg — F103, 28KiB bootloader, USART1 PA10/PA9 (or USART3 PB11/PB10 on the LCD IDC).",
    notes=["The 4.2.2 has no onboard USB-serial port; use the USART1 bin with a USB-TTL adapter, or the USART3 bin wired to the LCD port."])

B("creality-4.2.7", "Creality 4.2.7", "creality-4.2.7", "STM32F103", [
    {"variant": "usart1", "kconfig": frag("STM32F103", "7000", None, [U1])},
    {"variant": "usart3", "kconfig": frag("STM32F103", "7000", None, [U3])},
], "sd-firmware-bin",
    "klipper: config/generic-creality-v4.2.7.cfg — F103, 28KiB bootloader, USART1 PA10/PA9 (or USART3 PB11/PB10 on the LCD IDC).")

B("artillery-ruby-v1.2", "Artillery Ruby v1.2 (Sidewinder X2 / Genius Pro)", "ruby", "STM32F401", [
    {"variant": "usb", "kconfig": frag("STM32F401", "0000", "8M", [USB])},
], "ruby",
    "klipper: config/printer-artillery-sidewinder-x2-2022.cfg — F401, no bootloader, USB. Cross-checked 3dwork artillery-ruby-12.",
    notes=["Flashing requires the physical Boot0 bridge per Artillery's procedure."])

# ---------------------------------------------------------------- flash methods
flash_methods = {
    "sd-firmware-bin": [
        "1. Copy the downloaded `.bin` to the root of a FAT32-formatted microSD card (≤32 GB).",
        "2. Rename the file exactly to `firmware.bin` (no other `.bin` file may remain on the card from a previous flash).",
        "3. Power the board OFF, insert the card, power ON.",
        "4. Wait 30–60 seconds. The board's status LED usually blinks during the flash.",
        "5. Power off, remove the card, and check the card on your PC: a `FIRMWARE.CUR` file means the flash succeeded.",
        "6. Reinsert the card only if your config reads files from it, then connect the host.",
    ],
    "rp2040-uf2": [
        "1. Unplug the board. Hold the BOOTSEL button while plugging in USB.",
        "2. A drive named `RPBOOT` (or `RPI-RP2`) appears.",
        "3. Copy the downloaded `.uf2` onto that drive. The board reboots automatically.",
    ],
    "dfu-toolhead": [
        "1. Unplug the toolhead board. Hold its BOOT button while plugging in USB.",
        "2. Run `lsusb` — the board shows as `0483:df11` (STM32 DFU).",
        "3. `sudo dfu-util -a 0 -d 0483:df11 --dfu-adjust=0x0800 -D <downloaded .bin>`",
        "4. Unplug/replug. (For CAN variants flashed at an 8 KiB offset, flash Katapult first — see the Katapult column.)",
    ],
    "dfu-board": [
        "1. Put the board in DFU mode (BOOT jumper/button per your board's docs) and plug in USB.",
        "2. `sudo dfu-util -a 0 -d 0483:df11 --dfu-adjust=0x0800 -D <downloaded .bin>`",
        "3. Unplug/replug.",
    ],
    "mks-robin": [
        "1. The downloaded `.bin` is already wrapped for MKS bootloaders (update_mks_robin.py applied at build time).",
        "2. Copy it to a FAT32 microSD card, power the printer off, insert the card, power on.",
        "3. Wait for the flash, power off, remove the card.",
    ],
    "ruby": [
        "1. Power off and unplug everything.",
        "2. Bridge the +3.3V pin to the Boot0 pin on the Ruby board (physical jumper).",
        "3. Connect USB to the board (not the printer's other USB) and power on.",
        "4. `make flash FLASH_DEVICE=/dev/serial/by-id/usb-Klipper_stm32f401xc_*-if00` (or dfu-util if the device enumerates as DFU).",
        "5. Remove the bridge and power-cycle.",
    ],
    "spider": [
        "1. no-bootloader variant: flash via ST-Link/OpenOCD to 0x08000000, or via DFU if your Spider has the DFU bootloader.",
        "2. 32k-bootloader variant: copy the `.bin` to a FAT32 SD card as `firmware.bin`, power-cycle the board with the card inserted.",
    ],
}

doc = {
    "schema": 1,
    "bin_naming": "firmware-<board>-<variant>-<klipper-version>.bin",
    "flash_methods": flash_methods,
    "boards": boards,
}

with open("boards.yaml", "w") as fh:
    yaml.safe_dump(doc, fh, sort_keys=False, default_flow_style=False, width=100)

n_builds = sum(len(b["builds"]) for b in boards)
print(f"boards: {len(boards)}  builds: {n_builds}")
