import io
import subprocess
import sys
from pathlib import Path

import numpy as np
from sourcepp import vtfpp

from .misc import exception_logger, fop_copy

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).resolve().parent
OXIPNG_EXE = BASE_DIR / "oxipng" / "oxipng.exe"
PNGQUANT_EXE = BASE_DIR / "pngquant" / "pngquant.exe"

FOPTIMIZER_HALVE_INDEX = 19
FOPTIMIZER_SHRINK_INDEX = 20
SUPPORTED_FORMATS = (
    ("DXT5", "DXT3", "DXT1_ONE_BIT_ALPHA"),
    ("BGRA8888", "RGBA8888", "ABGR8888", "ARGB8888", "BGRX8888"),
)


def fit_alpha(input_file: Path, output_file: Path, lossless: bool) -> bool:
    """
    Encodes the best alpha format for a supported encoding-encoded VTF image losslessly.

    :param input_file: The path of the VTF to determine the optimal alpha format for.
    :type input_file: Path
    :param output_file: The path of the VTF file to write to.
    :type output_file: Path
    :return: Whether the function completed successfully.
    :rtype: bool
    """

    try:
        vtf = vtfpp.VTF(input_file)

        format_name = vtf.format.name
        if format_name in SUPPORTED_FORMATS[0]:
            return fit_dxt(
                input_file=input_file, output_file=output_file, lossless=lossless
            )
        elif format_name in SUPPORTED_FORMATS[1]:
            return fit_8888(input_file=input_file, output_file=output_file)
        else:
            vtf.bake_to_file(output_file)
        return True
    except Exception as e:
        exception_logger(e)
        return False


def fit_8888(input_file: Path, output_file: Path) -> bool:
    """
    Encodes the best alpha format for a 8888 prefix-encoded VTF image losslessly.

    :param input_file: The path of the VTF to determine the optimal alpha format for.
    :type input_file: Path
    :param output_file: The path of the VTF file to write to.
    :type output_file: Path
    :return: Whether the function completed successfully.
    :rtype: bool
    """

    try:
        vtf = vtfpp.VTF(input_file)

        if vtf.format.name not in SUPPORTED_FORMATS[1]:
            fop_copy(src=input_file, dst=output_file, mode=1)
            return True

        alpha_8888 = {
            "BGRA8888": "BGR888",
            "RGBA8888": "RGB888",
        }

        # shift: rgb channels need to be rearranged to fit target format
        shift_8888 = {
            "ABGR8888": ("BGR888", 0, [1, 2, 3]),
            "ARGB8888": ("RGB888", 2, [3, 0, 1]),
        }

        # free: always applicable due to waste, no checks needed
        free_8888 = {"BGRX8888": "BGR888"}

        # where are these even used lol
        dudv_8888 = {
            "UVLX8888": "UV88",
            "UVWQ8888": "UV88",
        }

        format_name = vtf.format.name
        is_alpha = format_name in alpha_8888
        is_shift = format_name in shift_8888
        is_free = format_name in free_8888

        if not is_alpha and not is_shift:
            if is_free:
                target_format = getattr(vtfpp.ImageFormat, free_8888[format_name])
                vtf.set_format(target_format)
                vtf.bake_to_file(output_file)
            else:
                fop_copy(src=input_file, dst=output_file, mode=1)
            return True

        if is_alpha:
            target_format_name = alpha_8888[format_name]
            alpha_idx = 3
            swizzle = None
        else:
            target_format_name, alpha_idx, swizzle = shift_8888[format_name]

        target_format = getattr(vtfpp.ImageFormat, target_format_name)
        can_strip_alpha = True

        for i in range(vtf.frame_count):
            raw_data = np.frombuffer(vtf.get_image_data_raw(frame=i), dtype=np.uint8)
            pixels = raw_data.reshape(-1, 4)
            if np.any(pixels[:, alpha_idx] < 255):
                can_strip_alpha = False
                break

        if can_strip_alpha:
            if is_shift:
                frames = [
                    np.frombuffer(
                        vtf.get_image_data_raw(frame=i), dtype=np.uint8
                    ).copy()
                    for i in range(vtf.frame_count)
                ]

                vtf.set_format(target_format)

                for i, raw_data in enumerate(frames):
                    pixels = raw_data.reshape(-1, 4)
                    stripped = pixels[:, swizzle].flatten()

                    try:
                        vtf.set_image(
                            image_data=stripped.tobytes(),
                            format=target_format,
                            width=vtf.width,
                            height=vtf.height,
                            filter=vtfpp.ImageConversion.ResizeFilter.NICE,
                            mip=0,
                            frame=i,
                        )
                    except Exception as e:
                        print(f"Error: {e}")
            else:
                vtf.set_format(target_format)
            vtf.bake_to_file(output_file)
        else:
            fop_copy(src=input_file, dst=output_file, mode=1)

        return True

    except Exception as e:
        exception_logger(e)
        return False


def fit_dxt(input_file: Path, output_file: Path, lossless: bool) -> bool:
    """
    Encodes the best alpha format for a DXT-encoded VTF image "losslessly."

    :param input_file: The path of the VTF to determine the optimal alpha format for.
    :type input_file: Path
    :param output_file: The path of the VTF file to write to.
    :type output_file: Path
    :return: Whether the function completed successfully.
    :rtype: bool
    """

    try:
        vtf = vtfpp.VTF(input_file)

        if vtf.format.name not in SUPPORTED_FORMATS[0]:
            fop_copy(src=input_file, dst=output_file, mode=1)
            return True

        original_format = vtf.format
        translucent = False
        bi_trans = False
        crushed = False

        for i in range(vtf.frame_count):
            vtf.set_format(original_format)

            original_rgba = np.frombuffer(
                vtf.get_image_data_as_rgba8888(frame=i), dtype=np.uint8
            ).copy()
            alpha = original_rgba[3::4]

            if np.all(alpha == 0):
                # stops images with fully transparent alpha channels
                # (for specularity?) being exported completely black
                fop_copy(src=input_file, dst=output_file, mode=1)
                return True

            if np.any((alpha > 0) & (alpha < 255)):
                translucent = True
                break

            if np.any(alpha == 0):
                bi_trans = True

            if bi_trans and lossless:
                vtf.set_format(vtfpp.ImageFormat.DXT1_ONE_BIT_ALPHA)
                test_rgba = np.frombuffer(
                    vtf.get_image_data_as_rgba8888(frame=i), dtype=np.uint8
                )

                if not np.array_equal(original_rgba, test_rgba):
                    crushed = True
                    break

        if translucent:
            vtf.set_format(original_format)
        elif bi_trans:
            if crushed:
                vtf.set_format(original_format)
            else:
                vtf.set_format(vtfpp.ImageFormat.DXT1_ONE_BIT_ALPHA)
        else:
            vtf.set_format(vtfpp.ImageFormat.DXT1)

        vtf.bake_to_file(output_file)
        return True

    except Exception as e:
        exception_logger(e)
        return False


def is_normal_vtf(input_file: Path) -> bool:
    """
    Attempts to determine if a VTF image is supposed to be a normal/bump map.

    :param input_file: The path of the VTF image to be evaluated.
    :type input_file: Path
    :return: Whether the VTF image appears to be a normal/bump map.
    :rtype: bool
    """

    try:
        vtf = vtfpp.VTF(input_file)

        input_file_name = input_file.stem.lower()
        if "bump" in input_file_name or input_file_name.endswith("_n"):
            return True

        image_data = vtf.get_image_data_as_rgba8888()
        pixels = np.frombuffer(image_data, dtype=np.uint8).astype(float) / 127.5 - 1.0
        pixels = pixels.reshape(-1, 4)[:, :3]

        magnitudes = np.linalg.norm(pixels, axis=1)

        avg_mag = np.mean(magnitudes)

        # threshold can be adjusted as some images can be misinterpreted as being majority normal data
        return 0.85 <= avg_mag <= 1.1
    except Exception as e:
        exception_logger(e)
        return False


def shrink_solid(input_file: Path, output_file: Path) -> bool:
    """
    Shrinks a solid-colour VTF into a 4x4 equivalent.

    :param input_file: The path of the VTF to be evaluated if shrinking is possible.
    :type input_file: Path
    :param output_file: The path of the VTF file to write to.
    :type output_file: Path
    :return: Whether the function completed successfully.
    :rtype: bool
    """

    try:
        vtf = vtfpp.VTF(input_file)

        image_data = vtf.get_image_data_as_rgba8888()
        pixels = np.frombuffer(image_data, dtype=np.uint8).reshape(-1, 4)
        is_solid = np.all(pixels == pixels[0], axis=0).all()

        if is_solid and not vtf.flags & 1 << FOPTIMIZER_SHRINK_INDEX:
            resize_vtf(
                input_file=input_file,
                output_file=output_file,
                width=4,
                height=4,
                flag_index=FOPTIMIZER_SHRINK_INDEX,
            )
        else:
            fop_copy(src=input_file, dst=output_file, mode=1)

        return True
    except Exception as e:
        exception_logger(e)
        return False


def resize_vtf(
    input_file: Path, output_file: Path, width: int, height: int, flag_index: int = None
) -> bool:
    """
    Resizes and writes a VTF image.

    :param input_file: The path of the VTF to be resized.
    :type input_file: Path
    :param output_file: The path of the resized VTF to be written to.
    :type output_file: Path
    :param width: The width of the resized VTF.
    :type width: int
    :param height: The height of the resized VTF.
    :type height: int
    :return: Whether the function completed successfully.
    :rtype: bool
    """

    try:
        vtf = vtfpp.VTF(input_file)

        if (vtf.width == width and vtf.height == height) or (width <= 1 or height <= 1):
            fop_copy(src=input_file, dst=output_file, mode=1)
            return True

        vtf.set_size(width, height, vtfpp.ImageConversion.ResizeFilter.NICE)
        if flag_index:
            vtf.add_flags(1 << flag_index)
        vtf.bake_to_file(output_file)
        return True

    except Exception as e:
        exception_logger(e)
        return False


def optimize_png(
    input_file: Path, output_file: Path, level: int = 100, lossless: bool = True
) -> bool:
    """
    Optimizes a PNG image.

    :param input_file: The path of the PNG file to optimize.
    :type input_file: Path
    :param output_file: The path of the optimized PNG file to write to.
    :type output_file: Path
    :param level: The normalized "intensity" of compression and comparisons.
    0 => fastest, largest filesizes. 100 => slowest, smallest filesizes.
    :type level: int
    :return: Whether the function completed successfully.
    :rtype: bool
    """
    try:
        input_file_cache = io.BytesIO(input_file.read_bytes())
        input_file_size = input_file.stat().st_size
        
        if lossless:
            command = [
                str(OXIPNG_EXE),
                input_file,
                "--out",
                output_file,
                "--opt",
                str(round(6 / 100 * level)),
                "--preserve",
                "--strip",
                "safe",
            ]
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )

        else:
            command = [
                str(PNGQUANT_EXE),
                input_file,
                "-f",
                "-o",
                output_file,
                "--speed",
                str(max(1, 11 - round(10 / 100 * level))),
                "--quality",
                f"0-{max(1, int(level))}",
                "--strip",
            ]
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )

        if input_file_size <= output_file.stat().st_size:
            with open(output_file, 'wb') as f_out:
                f_out.write(input_file_cache.getvalue())

        return True
    except Exception as e:
        exception_logger(e)
        return False


def halve_normal(input_file: Path, output_file: Path) -> bool:
    """
    Halves the dimensions of a VTF image if it is interpreted as a normal map.
    Limited to a minimum of 4x4 pixels.

    :param input_file: The path of the VTF to be resized.
    :type input_file: Path
    :param output_file: The path of the resized VTF to be written to.
    :type output_file: Path
    :return: Whether the function completed successfully.
    :rtype: bool
    """

    try:
        vtf = vtfpp.VTF(input_file)

        # checking halve_normal flag against vtf.flags bitmask
        if is_normal_vtf(input_file) and not (
            vtf.flags & (1 << FOPTIMIZER_HALVE_INDEX)
        ):
            width = max(4, vtf.width // 2)
            height = max(4, vtf.height // 2)

            resize_vtf(
                input_file=input_file,
                output_file=output_file,
                width=width,
                height=height,
                flag_index=FOPTIMIZER_HALVE_INDEX,
            )
        else:
            fop_copy(src=input_file, dst=output_file, mode=1)

        return True
    except Exception as e:
        exception_logger(e)
        return
