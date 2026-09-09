<p align="center">
  <img src="omvt_project_icon.png" alt="Open Madness Vehicle Tools" width="256">
</p>

# Open Madness Vehicle Tools
This repository consists of a set of scripts enabling development of original vehicle models for Slightly Mad Studios' Madness Engine racing games (tested with Project CARS 2 and Reiza Studios' Automobilista 2).

## Disclaimer
This is an unofficial, independent project. It is not affiliated with, authorized by, endorsed by, or sponsored by Reiza Studios, Slightly Mad Studios, or any of their affiliates. "Automobilista 2", "Project CARS", "Madness Engine", and all related names and marks are the property of their respective owners and are used here only to identify the software this toolkit interoperates with.

No game assets or game code are distributed by this project. You must own a legitimate copy of the target game to use this toolkit.

## Current Scope
This repository is intended to contain a variety of tools relating to vehicle development for Madness Engine games. It currently only contains tools relating to vehicle physics development.

## Contents:

### `./physics`
This subfolder contains a few Python scripts enabling decoding and encoding of the vehicle physics parameter files used by the game engine:
- `unpack.py` provides decode of `*.*dfbin` and `*.vdfm` files to human-readable and editable versions using the included codec scripts
- `pack.py` provides encode of the human-readable and editable versions of the `*.*dfbin` and `*.vdfm` files back to their original binary-packed versions
- `dfbin.py` is the codec for the `*.*dfbin` `ShCB` file format
- `vdfm.py` is the codec for the `*.vdfm` `Q02` file format

### `./physics/visualizers`
This subfolder contains a few Python scripts providing visualization of vehicle physics data (from the decoded files):
- `engine.py` provides visualization of an engine's torque curves in boosted and naturally-aspirated form, and throttle map data
- `gears.py` provides visualization of a car's gear ratios
- `geometry.py` provides visualization of a car's suspension geometry and other positional features
- `tires.py` provides visualization of a tire's slip curves, but only the ones from the `.HDT`, which are unused in PC2/AMS2 as they're overridden by the SETA tire model
- `_util.py` is a common utility library for the visualizer scripts
