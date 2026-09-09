<p align="center">
  <img src="omvt_project_icon.png" alt="Open Madness Vehicle Tools" width="256">
</p>

# Open Madness Vehicle Tools
This repository consists of a set of scripts enabling development of original vehicle models for Slightly Mad Studios' Madness Engine racing games (tested with Project CARS 2 and Reiza Studios' Automobilista 2).

## Disclaimer
This is an unofficial, independent project. It is not affiliated with, authorized by, endorsed by, or sponsored by Reiza Studios, Slightly Mad Studios, or any of their affiliates. "Automobilista 2", "Project CARS", "Madness Engine", and all related names and marks are the property of their respective owners and are used here only to identify the software this toolkit interoperates with.

No game code or vehicle physics data are distributed by this project. You must own a legitimate copy of the target game to use this toolkit.

## Current Scope
This repository is intended to contain a variety of tools relating to vehicle development for Madness Engine games. It currently only contains tools relating to vehicle physics development.

## Contents:

### `./physics`
This subfolder contains a few Python scripts enabling decoding and encoding of the vehicle physics parameter files used by the game engine:
- `unpack.py` provides decode of `*.*dfbin` and `*.vdfm` files to human-readable and editable versions using the included codec scripts
- `pack.py` provides encode of the human-readable and editable versions of the `*.*dfbin` and `*.vdfm` files back to their original binary-packed versions
- `dfbin.py` is the codec for the `*.*dfbin` `ShCB` file format
- `vdfm.py` is the codec for the `*.vdfm` `Q02` file format
- `names.json` is a list of short identifier tokens used to reverse lookup3 hashes when unpacking. It was recovered from strings present in game binaries and from dictionary attack against those hashes.

### `./physics/visualizers`
This subfolder contains a few Python scripts providing visualization of vehicle physics data (from the decoded files):
- `engine.py` provides visualization of an engine's torque curves in boosted and naturally-aspirated form, and throttle map data
- `gears.py` provides visualization of a car's gear ratios
- `geometry.py` provides visualization of a car's suspension geometry and other positional features
- `tires.py` provides visualization of a tire's slip curves, but only the ones from the `.HDT`, which are unused in PC2/AMS2 as they're overridden by the SETA tire model
- `_util.py` is a common utility library for the visualizer scripts

## License
This project is free software, licensed under [GPL-3.0-or-later](LICENSE) with an [output exception](LICENSE-EXCEPTION.txt).

### Tool output is not automatically yours
The copyleft terms apply to this toolkit and to derivatives of the toolkit. They do not apply to files the tools emit. The [output exception](LICENSE-EXCEPTION.txt) states that explicitly: packing, unpacking, or plotting a file does not make that file GPL.

That waiver is not a transfer of someone else's copyright.

- Physics data you author yourself is yours as far as this toolkit is concerned. You may license, distribute, and sell it.
- Unpacked game physics data is still the publisher's data in another encoding. Editing it does not by itself make it yours. This toolkit does not authorize redistributing game physics data or derivatives of it. Doing so may infringe copyright and may violate the game's EULA.

The bundled identifier list is a set of short names used to reverse hashes so unpacked files are readable. Seeing those names in an unpacked file does not change who owns the physics data around them.

### Contributing and naming
See [CONTRIBUTING.md](CONTRIBUTING.md) for the sign-off requirement, and [TRADEMARKS.md](TRADEMARKS.md) for how the project name may be used.
