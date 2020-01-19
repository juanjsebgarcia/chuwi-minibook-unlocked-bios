# Chuwi Minibook BIOS tools

This is a work in progress repo.

The goal is to log and share my findings so the community can crack the BIOS to unlock advanced features.

This involves decompiling and reverse-engineering the current binary.

# 🚨 !WARNING! 🚨
Playing with the BIOS is inherently dangerous. Tread carefully or you'll end up with a brick.

I cannot be responsible for any damage caused to your device.

# Findings

**The lock is found.** See [`forms/FINDINGS.md`](forms/FINDINGS.md) for the full analysis.

Chuwi removed nothing. The firmware still contains the complete AMI Aptio V form set —
194 forms, including `Advanced`, `Chipset`, full CPU/VR/turbo control, an
`OverClocking Performance Menu` and a `Memory Overclocking Menu`. 190 of those 194 forms
are still reachable by a normal `Ref`.

The entire lock is **two opcodes** in the root form set (form ID `0x2710`): a
`suppressif TRUE` wrapped around the `Ref` to `Advanced`, and another around the `Ref` to
`Chipset`. Flip both `EFI_IFR_TRUE_OP` (`0x46`) to `EFI_IFR_FALSE_OP` (`0x47`) and the
tabs come back. Same opcode length, so nothing shifts.

[`tools/patch_unlock.py`](tools/patch_unlock.py) does exactly that, by byte signature.

## Resolved dead ends

- **AMIBCP `USER` / `Supervisor` access levels had no effect.** They never could. Access
  levels are evaluated *after* the IFR's own conditional expressions, and no access level
  overrides an unconditional `suppressif TRUE`.
- **The `magic key` string hunt was chasing the wrong mechanism.** This firmware has no
  hidden keystroke and no unlock string gating the top-level menu.

## Not yet done

- Confirming which FFS/section in `BIOS.bin` carries the IFR (needs an actual image dump —
  the IFR sits in the compressed DXE volume, so raw byte search on `BIOS.bin` will miss).
- Flashing and validating on hardware.

# Copyright
To err on the side of caution I will not be uploading pre-cracked BIOS images here.

I will aim to create a patch so you can modify your own BIOS.

Some of the tools used in this repo are the property of American Megatrends.
They were distributed to us by Chuwi, so I have taken the liberty of reuploading them.
