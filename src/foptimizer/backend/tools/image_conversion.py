from pathlib import Path

import oxipng
import numpy as np
from sourcepp import vtfpp

from .misc import exception_logger


def fit_alpha(vtf: vtfpp.VTF, output_file: Path, lossless: bool) -> bool:
    """
    Encodes the best alpha format for a supported encoding-encoded VTF image losslessly.
    
    :param vtf: The VTF to determine the optimal alpha format for.
    :type vtf: vtfpp.VTF
    :param output_file: The path of the VTF file to write to.
    :type output_file: Path
    :return: Whether the function completed successfully.
    :rtype: bool
    """

    try:
        if vtf.format.name in ("DXT5", "DXT1_ONE_BIT_ALPHA"):
            return fit_dxt(vtf=vtf, output_file=output_file, lossless=lossless)
        elif vtf.format.name in ("BGRA8888", "RGBA8888", "BGRX8888"):
            return fit_8888(vtf=vtf, output_file=output_file)
        else:
            vtf.bake_to_file(str(output_file))
    except Exception:
        exception_logger(exc=Exception("fit_alpha failed"))
        return False
    

def fit_8888(vtf: vtfpp.VTF, output_file: Path) -> bool:
    """
    Encodes the best alpha format for a 8888 prefix-encoded VTF image losslessly.
    
    :param vtf: The VTF to determine the optimal alpha format for.
    :type vtf: vtfpp.VTF
    :param output_file: The path of the VTF file to write to.
    :type output_file: Path
    :return: Whether the function completed successfully.
    :rtype: bool
    """

    try:
        if vtf.format.name not in ("BGRA8888", "RGBA8888", "BGRX8888"):
            vtf.bake_to_file(str(output_file))
            return True

        map_8888 = {"BGRA8888": ("BGR888"), "RGBA8888": ("RGB888"),"BGRX8888": ("BGR888")}

        target_format_name = map_8888[vtf.format.name]
        target_format = getattr(vtfpp.ImageFormat, target_format_name)
        
        num_frames = vtf.frame_count
        can_strip_alpha = True

        for i in range(num_frames):
            original_rgba = np.frombuffer(vtf.get_image_data_as_rgba8888(frame=i), dtype=np.uint8).copy()
            
            alpha = original_rgba[3::4]
            if np.any(alpha < 255):
                can_strip_alpha = False
                break
                
        if can_strip_alpha:
            vtf.set_format(target_format)
        
        vtf.bake_to_file(str(output_file))
        
        return True

    except Exception:
        exception_logger(exc=Exception("fit_8888 failed"))
        return False
    

def fit_dxt(vtf: vtfpp.VTF, output_file: Path, lossless: bool) -> bool:
    """
    Encodes the best alpha format for a DXT-encoded VTF image "losslessly."
    
    :param vtf: The VTF to determine the optimal alpha format for.
    :type vtf: vtfpp.VTF
    :param output_file: The path of the VTF file to write to.
    :type output_file: Path
    :return: Whether the function completed successfully.
    :rtype: bool
    """

    try:
        if vtf.format.name not in ("DXT5", "DXT1_ONE_BIT_ALPHA"):
            vtf.bake_to_file(str(output_file))
            return True

        original_format = vtf.format
        translucent = False
        bi_trans = False
        crushed = False

        for i in range(vtf.frame_count):
            vtf.set_format(original_format)

            original_rgba = np.frombuffer(vtf.get_image_data_as_rgba8888(frame=i), dtype=np.uint8).copy()
            alpha = original_rgba[3::4]

            if np.all(alpha == 0):
                # stops images with fully transparent alpha channels (for specularity?) being exported completely black
                vtf.set_format(original_format)
                vtf.bake_to_file(str(output_file))
                return True

            if np.any((alpha > 0) & (alpha < 255)):
                translucent = True
                break
            
            if np.any(alpha == 0):
                bi_trans = True

            if bi_trans and lossless:
                vtf.set_format(vtfpp.ImageFormat.DXT1_ONE_BIT_ALPHA)
                test_rgba = np.frombuffer(vtf.get_image_data_as_rgba8888(frame=i), dtype=np.uint8)

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

        vtf.bake_to_file(str(output_file))
        return True
    
    except Exception:
        exception_logger(exc=Exception("fit_dxt failed"))
        return False


def is_normal(vtf: vtfpp.VTF) -> bool:
    """
    Attempts to determine if a VTF image is supposed to be a normal/bump map.
    
    :param vtf: The VTF to be evaluated.
    :type vtf: vtfpp.VTF
    :return: Whether the VTF image appears to be a normal/bump map.
    :rtype: bool
    """

    try:
        image_data = vtf.get_image_data_as_rgba8888()
        pixels = np.frombuffer(image_data, dtype=np.uint8).astype(float) / 127.5 - 1.0
        pixels = pixels.reshape(-1, 4)[:, :3]

        magnitudes = np.linalg.norm(pixels, axis=1)
        
        avg_mag = np.mean(magnitudes)
        return 0.85 <= avg_mag <= 1.1
    except Exception:
        exception_logger(exc=Exception("is_normal failed"))
        return False


def shrink_solid(vtf: vtfpp.VTF, output_file: Path) -> bool:
    """
    Shrinks a solid-colour VTF into a 4x4 equivalent.
    
    :param vtf: The VTF to be evaluated if shrinking is possible.
    :type vtf: vtfpp.VTF
    :param output_file: The path of the VTF file to write to. 
    :type output_file: Path
    :return: Whether the function completed successfully.
    :rtype: bool
    """

    try:
        image_data = vtf.get_image_data_as_rgba8888()
        pixels = np.frombuffer(image_data, dtype=np.uint8).reshape(-1, 4)
        is_solid = np.all(pixels == pixels[0], axis=0).all()

        if is_solid:
            vtf.set_size(4, 4, vtfpp.ImageConversion.ResizeFilter.NICE)
        
        vtf.bake_to_file(str(output_file))

        return True
    except Exception:
        exception_logger(exc=Exception("shrink_solid failed"))
        return False


def resize_vtf(vtf: vtfpp.VTF, output_file: Path, w: int, h: int) -> bool:
    """
    Resizes and writes a VTF image.
    
    :param vtf: The VTF to be resized.
    :type vtf: vtfpp.VTF
    :param output_file: The resized VTF to be written to.
    :type output_file: Path
    :param w: The width of the resized VTF.
    :type w: int
    :param h: The height of the resized VTF.
    :type h: int
    :return: Whether the function completed successfully.
    :rtype: bool
    """

    try:

        if (vtf.width == w) and (vtf.height == h):
            return
        
        original_format = vtf.format

        vtf.set_format(vtfpp.ImageFormat.RGBA32323232F) # will crash without a conversion, but at least uses a lossless format (very memory heavy)
        
        vtf.set_size(w, h, vtfpp.ImageConversion.ResizeFilter.NICE) # why do 2:1 (w:h) images crash set_size()?

        vtf.set_format(original_format)

        vtf.bake_to_file(str(output_file))

        return True
    except Exception:
        exception_logger(exc=Exception("resize_vtf failed"))
        return False


def optimize_png(input_file: Path, output_file: Path, level: int = 6, lossless: bool = True) -> bool:
    """
    Optimizes a PNG image using oxipng.
    
    :param input_file: The PNG file to optimize.
    :type input_file: Path
    :param output_file: The optimized PNG file to write to.
    :type output_file: Path
    :param level: The "intensity" (0 to 6) of comparisons. 0 => fastest, largest filesizes. 6 => slowest, smallest filesizes.
    :type level: int
    :return: Whether the function completed successfully.
    :rtype: bool
    """

    try:
        level = int(level)

        if lossless:
            oxipng.optimize(
                input_file,
                output_file,
                level=level,
                force=True,
                optimize_alpha=False,
                strip=oxipng.StripChunks.safe(),
            )
        else:
            oxipng.optimize(
                input_file, 
                output_file, 
                level=level,
                force=True,
                optimize_alpha=True,
                strip=oxipng.StripChunks.all(),
                bit_depth_reduction=True,
                color_type_reduction=True,
                palette_reduction=True,
                scale_16=True
            )
        
        return True
    except Exception as e:
        print(e)
        exception_logger(exc=Exception("optimize_png failed"))
        return False