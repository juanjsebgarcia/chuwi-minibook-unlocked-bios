# Chuwi Minibook BIOS tools

This is a work in progress repo.

The goal is to log and share my findings so the community can crack the BIOS to unlock advanced features.

This involves decompiling and reverse-engineering the current binary.

# 🚨 !WARNING! 🚨
Playing with the BIOS is inherently dangerous. Tread carefully or you'll end up with a brick.

I cannot be responsible for any damage caused to your device.

# Known issues
Using the AMIBCP to set the tree structure to `USER` or `Supervisor`. This does not impact the BIOS even after rebuild.

Searching for the `magic key` string, a few matches and none convincing. The IFR form structure doesn't seem correct for this approach either.

# Copyright
To err on the side of caution I will not be uploading pre-cracked BIOS images here.

I will aim to create a patch so you can modify your own BIOS.

Some of the tools used in this repo are the property of American Megatrends.
They were distributed to us by Chuwi, so I have taken the liberty of reuploading them.
