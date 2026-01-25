<div align="center">

# fOptimizer <br> ![Progress Bar](assets/progress_bar_looponce.png)

[![Version](https://img.shields.io/github/v/release/fxington/fOptimizer?color=orange)](https://github.com/fxington/foptimizer/releases)
![License](https://img.shields.io/github/license/fxington/foptimizer)
![Issues](https://img.shields.io/github/issues/fxington/foptimizer)

### Benchmarks
(as of January 16, 2025)
| Content | Original Size | fOptimized Size | Compression* |
| :--- | :---: | :--- | :---: |
| Project: Synapse / HL2RP | 9.58 GB | 5.57 GB | ![projectsynpasehl2rp](https://geps.dev/progress/58?dangerColor=006600&warningColor=006600&successColor=006600) |
| Mutiny Network / DarkRP | 3.51 GB | 2.26 GB | ![mutinydrp](https://geps.dev/progress/64?dangerColor=006600&warningColor=006600&successColor=006600) |
| Civil Networks / SCPRP | 12.6 GB | 8.66 GB | ![civilscprp](https://geps.dev/progress/69?dangerColor=006600&warningColor=006600&successColor=006600) |
| Icefuse Networks / ImperialRP | 9.97 GB | 7.09 GB | ![icefuseimprp](https://geps.dev/progress/71?dangerColor=006600&warningColor=006600&successColor=006600) |
| Sunrust / Zombie Survival (no maps) | 4.87 GB | 3.82 GB | ![sunrustzs](https://geps.dev/progress/78?dangerColor=006600&warningColor=006600&successColor=006600) |

\*fOptimized filesize as a percentage of original filesize (one-click optimizations, default settings)

</div>

## Overview

foxington's Optimizer is a Source format optimizer and redundancy-culling program. It can be run via CLI, or as a self-contained program through the provided GUI.

## Installation

fOptimizer for Windows can be downloaded via the
[Releases](https://github.com/fxington/foptimizer/releases) section on its GitHub page.

Unzip the .zip archive, then run **start_foptimizer.bat** to install dependencies into a virtual environment and initialize the GUI.

The earliest officially-supported Python version is **3.10**.

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

## Common Installation Issues
* I'm getting the error: <br>ImportError: DLL load failed while importing _sourcepp_impl: The specified module could not be found.<br>

SourcePP requires that a version of the Microsoft Visual C++ Redistributables be installed on your system. You can find a list of them [here](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170#latest-supported-redistributable-version).