#!/usr/bin/env python3
"""Unhide the Advanced and Chipset menus in a Chuwi Minibook AMI Aptio V BIOS.

Chuwi hid both top-level tabs with `suppressif TRUE` in the root form set. This
rewrites EFI_IFR_TRUE_OP (0x46) to EFI_IFR_FALSE_OP (0x47) in those two
conditionals. Both opcodes are two bytes, so nothing shifts and no length or
offset needs recomputing.

See forms/FINDINGS.md for the analysis.

The IFR usually lives in the compressed DXE volume, so this will normally NOT
find anything in a raw BIOS.bin. Point it at the decompressed section body you
extracted with UEFITool NE, patch that, then use UEFITool's "Replace body".

Usage:
    ./patch_unlock.py <input> [-o <output>] [--extra] [--dry-run]
"""

import argparse
import sys

TRUE_OP = 0x46
FALSE_OP = 0x47


def h(s: str) -> bytes:
    """Parse space-separated hex bytes."""
    return bytes.fromhex(s.replace(" ", "").replace("\n", ""))


# --- primary lock -----------------------------------------------------------
#
# Root form set 0x2710, the tab bar. The two `suppressif TRUE` blocks are
# adjacent, so we match them as one 42-byte run — unique in any image.
#
#   0A 82                          suppressif
#   46 02                          TRUE                     <- flip
#   0F 0F .. Ref: Advanced (0x2712)
#   29 02                          endif
#   0A 82                          suppressif
#   46 02                          TRUE                     <- flip
#   0F 0F .. Ref: Chipset  (0x2713)
#   29 02                          endif

PRIMARY_LABEL = "Advanced + Chipset tabs (root form 0x2710)"
PRIMARY_SIG = h(
    "0A 82  46 02  0F 0F 1F 00 02 00 02 00 00 00 FF FF 00 12 27  29 02"
    "0A 82  46 02  0F 0F 20 00 02 00 03 00 00 00 FF FF 00 13 27  29 02"
)
PRIMARY_FLIPS = (2, 23)

# --- secondary, independent unconditional hides ----------------------------
#
# Each signature is `0A 82 46 02` (suppressif) or `19 82 46 02` (grayoutif)
# followed by enough of the guarded opcode to be unambiguous. The two USB
# entries share an identical 12-byte prefix, hence the full Setting opcode.

EXTRA = [
    (
        "Execute Disable Bit + Limit CPUID Maximum",
        h("0A 82  46 02  05 91 39 04 3A 04 69 00 01 00 67 05 10 10 00 01 00"),
    ),
    (
        "High Precision Timer",
        h("0A 82  46 02  05 91 8F 08 90 08 A4 05 01 00 C1 09 10 10 00 01 00"),
    ),
    (
        "ALS Support",
        h("0A 82  46 02  05 91 E8 06 E9 06 5C 04 01 00 EF 07 10 10 00 02 00"),
    ),
    (
        "Intel Graphics Pei Display Peim",
        h("0A 82  46 02  05 91 C6 06 C7 06 5A 04 01 00 F9 07 10 10 00 01 00"),
    ),
    (
        "_TMP 2 / _TMP 3 Object",
        h("0A 82  46 02  05 91 0E 14 0F 14 54 02 01 00 C1 03 10 10 00 01 00"),
    ),
    (
        "USB 2.0 Controller Mode",
        h("0A 82  46 02  19 82  12 06 A4 0C 01 00"
          "05 91 30 19 31 19 D2 03 27 00 2E 00 10 10 00 01 00"),
    ),
    (
        "XHCI Legacy Support",
        h("0A 82  46 02  19 82  12 06 A4 0C 01 00"
          "05 91 D9 0C DA 0C D3 03 27 00 2A 00 10 10 00 01 00"),
    ),
    (
        "TPM 2.0 InterfaceType (grayout)",
        h("19 82  46 02  05 91 79 1A 7A 1A A3 03 01 00 26 10 10 10 00 01 00"),
    ),
]


def apply(buf: bytearray, label: str, sig: bytes, flips=(2,), dry_run: bool = False) -> bool:
    """Locate sig exactly once and flip its TRUE opcodes. Returns True on success."""
    found = []
    start = 0
    while (i := buf.find(sig, start)) != -1:
        found.append(i)
        start = i + 1

    if not found:
        print(f"  [ MISS  ] {label}")
        return False
    if len(found) > 1:
        where = ", ".join(f"0x{o:X}" for o in found)
        print(f"  [ AMBIG ] {label}: {len(found)} matches ({where}) — refusing to guess")
        return False

    base = found[0]
    for f in flips:
        got = buf[base + f]
        if got != TRUE_OP:
            print(f"  [ FAIL  ] {label}: expected 0x46 at 0x{base + f:X}, found 0x{got:02X}")
            return False

    for f in flips:
        pos = base + f
        if not dry_run:
            buf[pos] = FALSE_OP
        print(f"  [  OK   ] {label}: 0x{pos:X}  0x46 -> 0x47")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("input", help="BIOS image or extracted IFR section body")
    ap.add_argument("-o", "--output", help="output path (default: <input>.unlocked)")
    ap.add_argument("--extra", action="store_true",
                    help="also unhide the secondary suppressed questions")
    ap.add_argument("--dry-run", action="store_true", help="report only, write nothing")
    args = ap.parse_args()

    with open(args.input, "rb") as fh:
        buf = bytearray(fh.read())
    print(f"loaded {args.input} ({len(buf):,} bytes)\n")

    print("primary lock:")
    if not apply(buf, PRIMARY_LABEL, PRIMARY_SIG, PRIMARY_FLIPS, args.dry_run):
        print(
            "\nThe primary signature is not present.\n"
            "Almost certainly the IFR is still LZMA-compressed. Open the image in\n"
            "UEFITool NE, extract the setup driver's section body, and run this\n"
            "against that instead. See forms/FINDINGS.md.",
            file=sys.stderr,
        )
        return 1

    if args.extra:
        print("\nsecondary hides:")
        for label, sig in EXTRA:
            apply(buf, label, sig, dry_run=args.dry_run)

    if args.dry_run:
        print("\ndry run — nothing written")
        return 0

    out = args.output or args.input + ".unlocked"
    with open(out, "wb") as fh:
        fh.write(buf)
    print(f"\nwrote {out}")
    print("Next: UEFITool NE -> Replace body -> Save image file -> flash.")
    print("Keep your untouched BIOS.bin. You will want it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
