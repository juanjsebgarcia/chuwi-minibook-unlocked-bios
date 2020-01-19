# IFR analysis — how Chuwi hid the menus

Source: `setup_form_ifr_dump.txt` (extracted from the live UEFI HII database).

## Summary

Nothing was removed. The firmware carries the **complete** AMI Aptio V setup form set —
**194 forms**, including everything the OEM pretends does not exist:

| Form ID | Form |
|---|---|
| 0x2712 | Advanced |
| 0x2713 | Chipset |
| 0x272A | CPU Configuration |
| 0x272C | Power & Performance |
| 0x272D | CPU - Power Management Control |
| 0x272F | View/Configure Turbo Options |
| 0x2730–0x2735 | CPU / System Agent / Core-IA / GT VR Settings |
| 0x2736 | Power Limit 3 Settings |
| 0x2737 | Config TDP Configurations |
| 0x2738 | View/Configure CPU Lock Options |
| 0x27B5 | OverClocking Performance Menu |
| 0x27BB | Memory Overclocking Menu |
| 0x27BC | Turn Around Timing |
| 0x27BD | Voltage PLL Trim Controls |
| 0x279B | Platform Thermal Configuration |
| 0x27A0 | RTD3 settings |
| 0x27DC | Thunderbolt(TM) Configuration |

Of those 194 forms, **190 are reachable by a normal `Ref`** and only three are genuine
orphans (`Demo Board`, and two duplicate `TCG Storage device Security Configuration`
forms). The tree is intact.

## The actual mechanism

The root form set — `Form: Setup, Form ID: 0x2710`, the thing that draws the top-level
tab bar — reads as follows (dump offsets `0x2A639`–`0x2A69F`):

```
0x2A639   Ref: Main,        Variable: 0xFFFF   {0F 0F 09 00 02 00 01 00 00 00 FF FF 00 11 27}
0x2A648   Suppress If:                         {0A 82}
0x2A64A       True                             {46 02}      <-- !!
0x2A64C       Ref: Advanced, Variable: 0xFFFF  {0F 0F 1F 00 02 00 02 00 00 00 FF FF 00 12 27}
0x2A65B   End If                               {29 02}
0x2A65D   Suppress If:                         {0A 82}
0x2A65F       True                             {46 02}      <-- !!
0x2A661       Ref: Chipset, Variable: 0xFFFF   {0F 0F 20 00 02 00 03 00 00 00 FF FF 00 13 27}
0x2A670   End If                               {29 02}
0x2A672   Ref: Security,    Variable: 0xFFFF   {0F 0F 3B 00 02 00 04 00 00 00 FF FF 00 14 27}
0x2A681   Ref: Boot,        Variable: 0xFFFF   {0F 0F 21 00 02 00 05 00 00 00 FF FF 00 15 27}
0x2A690   Ref: Save & Exit, Variable: 0xFFFF   {0F 0F 4E 00 02 00 06 00 00 00 FF FF 00 16 27}
```

`suppressif TRUE` — an *unconditional* suppression — wrapped around the `Ref` to
**Advanced** and the `Ref` to **Chipset**. That is the whole lock. Two opcodes.
Everything beneath those two forms is unsuppressed and fully functional; it is simply
never linked into the visible tab bar.

## Why AMIBCP got us nowhere

AMIBCP's `USER` / `Supervisor` access flags are consulted by AMI's TSE when it decides
whether a *user of a given privilege* may see a question. They are evaluated **after**
the IFR's own conditional expressions. A `suppressif TRUE` is not an access-control
decision — it is an unconditional instruction to the form browser, and no access level
can override it. Setting the tree to `Supervisor` was therefore always going to be a
no-op, exactly as observed.

Likewise, the `magic key` hunt was chasing a mechanism this firmware does not use.
There is no hidden keystroke, no unlock string, no `SystemAccess` gate on the top-level
menu. It is a hard `suppressif TRUE`.

## The patch

`EFI_IFR_TRUE_OP` = `0x46`, `EFI_IFR_FALSE_OP` = `0x47`. Both are two-byte opcodes of
identical length, so this is a pure byte-for-byte substitution: no lengths change, no
offsets shift, no IFR relocation, nothing downstream to recompute.

Flip the two `0x46` bytes to `0x47` and `suppressif FALSE` never fires. The tabs appear.

Search signature (42 contiguous bytes, unique in the image):

```
0A 82 46 02 0F 0F 1F 00 02 00 02 00 00 00 FF FF 00 12 27 29 02
0A 82 46 02 0F 0F 20 00 02 00 03 00 00 00 FF FF 00 13 27 29 02
     ^^                                                  ^^
```

See `tools/patch_unlock.py`.

### Important caveat on offsets

The offsets above (`0x2A64A`, `0x2A65F`) are offsets **into the extracted HII blob**,
not into `BIOS.bin`. Do not seek to them in the flash image. In Aptio V the setup IFR
lives in the compressed DXE firmware volume, so a raw byte search over `BIOS.bin` will
generally *fail*. The workflow is:

1. Open `BIOS.bin` in **UEFITool NE**.
2. Locate the setup driver carrying the form set (`AMITSE` / `SetupData` / the DXE
   holding the IFR); UEFITool decompresses volume contents as it parses.
3. Extract the relevant section **body**, patch it with `tools/patch_unlock.py`.
4. *Replace body* with the patched file, then *Save image file*. UEFITool recompresses
   and fixes the volume for you.
5. Flash. `AfuEfix64.efi` (see `backup_bios_tool/`) or a hardware programmer.

## Secondary unconditional hides

Thirteen further `suppressif TRUE` / `grayoutif TRUE` / `disableif TRUE` blocks exist
deeper in the tree. These are separate from the main lock and each hides only its own
question(s). Flip them the same way if wanted:

| Dump offset of `46 02` | Hides |
|---|---|
| `0x2B9D3` | Execute Disable Bit, Limit CPUID Maximum |
| `0x2A8D8` | STM32 FW Version (action) |
| `0x30F79` | `_TMP 2 Object`, `_TMP 3 Object` |
| `0x32F69` | Expected CPU Freq (action) |
| `0x3425E` | three numerics in Boot |
| `0x35134` | TPM 2.0 InterfaceType (grayout only) |
| `0x35EDA` | USB 2.0 Controller Mode |
| `0x35F0B` | XHCI Legacy Support |
| `0x36DC8` | unnamed action |
| `0x38710` | Intel Graphics Pei Display Peim |
| `0x38762` | ALS Support |
| `0x3B8D7` | High Precision Timer |
| `0x4F518` | three numerics (`disableif`) |

## Dead end, ruled out

`Variable 0xCA4 equals 0x1` appears in **93** `grayoutif` conditions and looks
temptingly like a master lock byte. It is not: `0xCA4` is a PCIe **`Topology`** setting
(`0x4542E`). Those grayouts are legitimate topology-dependent behaviour. Leave it alone.

## The no-flash alternative

If the goal is *control* rather than a visibly unlocked menu, every one of these
questions already reads and writes real NVRAM:

- **VarStore 0x1**, name `Setup`
- **GUID** `EC87D643-EBA4-4BB5-A1E5-3F3E36B20DA9` (the standard AMI `SETUP_DATA` store)
- **Size** `0x10F2` (4338 bytes)

The `Variable: 0x...` value on every `Setting:` line in the dump is that question's byte
offset within this varstore. So `High Precision Timer` is `Setup[0x9C1]`,
`Execute Disable Bit` is `Setup[0x567]`, and so on. Poke them directly with `setup_var`,
`RU.EFI`, or a UEFI shell tool and the hidden options take effect with **zero** risk of
bricking. This is by far the safer route for experimentation, and a good way to prove a
setting does what you think before you commit to a reflash.
