# fOptimizer
![Version](https://img.shields.io/badge/version-1.2.0-orange)
![License](https://img.shields.io/github/license/fxington/foptimizer)
![Issues](https://img.shields.io/github/issues/fxington/foptimizer)

## Overview

foxington's Optimizer is a Source format optimizer and redundancy-culling program. It can be run via CLI, or as a self-contained program through the provided GUI.

## Installation

fOptimizer for Windows can be downloaded via the
[Releases](https://github.com/fxington/foptimizer/releases) section on its GitHub page.

Unzip the .zip archive, then run **start_foptimizer.bat** to install dependencies into a virtual environment and initialize the GUI.

The earliest officially-supported Python version is **3.11**.

## Usage

fOptimizer functions are primarily intended to be GUI-based. Hover over each button or element to view a tooltip regarding its intended usage.

To integrate fOptimizer functions into your own programs, install fOptimizer as an editable package using ```python -m pip install -e path/to/foptimizer```. Then, simply ```import foptimizer``` into your own project.

## Contributing

Any and all suggestions, improvements, and bug fixes are welcome. Bug reports must be created via a GitHub issue. If you believe you have found a solution to a bug,
please submit a bug report outlining the cause and a fix you have found.

New avenues for optimization are always appreciated and will be considered via feature request.

## License

fOptimizer is an open-source project distributed under the MIT license.

## Credits & Third-Party Tools
This project utilizes the following incredible tools:
* [oxipng](https://github.com/oxipng/oxipng) - Lossless-focused PNG optimizer by Joshua Holmer (shssoichiro).
* [PNGQuant](https://pngquant.org/) - Lossy PNG compression library and associated CLI by Kornel Lesiński.
* [oggenc2](https://www.rarewares.org/ogg-oggenc.php) - Ogg Vorbis CLI encoder by RareWares.
* [SourcePP](https://github.com/craftablescience/sourcepp) - Source engine format parsing library by Laura Lewis (CraftableScience).
* [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) - Modern-look Tkinter wrapper by Tom Schimansky.