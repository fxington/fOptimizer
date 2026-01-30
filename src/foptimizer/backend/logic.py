from pathlib import Path

from .tools.audio_conversion import wav_to_ogg, wav_stereo_to_mono
from .tools.deduplication import remove_duplicate_vtfs, remove_vpk_files
from .tools.image_conversion import convert_to_dxt, fit_alpha, optimize_png, shrink_normal, shrink_solid
from .tools.remove_redundancies import remove_unaccessed_vtfs, remove_unused_files
from .tools.misc import handle_batch_parallel


ALIASES = {}
def register(name):
    def decorator(func):
        ALIASES[name] = func
        return func
    return decorator


@register("DEDUPLICATE_VTF")
def logic_remove_duplicate_vtfs(
    input_dir: Path,
    output_dir: Path,
    progress_window=None,
):
    remove_duplicate_vtfs(
        input_dir=input_dir,
        output_dir=output_dir,
        progress_window=progress_window
    )


@register("FIT_ALPHA_VTF")
def logic_fit_alpha(
    input_dir: Path,
    output_dir: Path,
    progress_window=None,
    lossless: bool = True,
):
    handle_batch_parallel(
        input_dir=input_dir,
        output_dir=output_dir,
        ext=("vtf", "vtf"),
        opt_func=fit_alpha,
        progress_window=progress_window,
        lossless=lossless,
    )


@register("SHRINK_NORMAL_VTF")
def logic_shrink_normals(
    input_dir: Path,
    output_dir: Path,
    progress_window=None,
    multiplier: int = 2,
    clamp_w: int = 0,
    clamp_h: int = 0,
    override_flags: bool = False,
):
    handle_batch_parallel(
        input_dir=input_dir,
        output_dir=output_dir,
        ext=("vtf", "vtf"),
        opt_func=shrink_normal,
        progress_window=progress_window,
        multiplier=multiplier,
        clamp=(clamp_w, clamp_h),
        override_flags=override_flags,
    )


@register("OPTIMIZE_PNG")
def logic_optimize_png(
    input_dir: Path,
    output_dir: Path,
    progress_window=None,
    level: int = 6,
    lossless: bool = True,
):
    handle_batch_parallel(
        input_dir=input_dir,
        output_dir=output_dir,
        ext=("png", "png"),
        opt_func=optimize_png,
        progress_window=progress_window,
        level=level,
        lossless=lossless,
    )


@register("REMOVE_REDUNDANT_CONTENT")
def logic_remove_unused_files(
    input_dir: Path,
    output_dir: Path,
    progress_window=None,
    remove: bool = True,
):
    remove_unused_files(
        input_dir=input_dir,
        output_dir=output_dir,
        remove=remove,
        progress_window=progress_window,
    )


@register("REMOVE_UNACCESSED_VTF")
def logic_remove_unaccessed_vtfs(
    input_dir: Path,
    output_dir: Path,
    progress_window=None,
    remove: bool = True,
):
    remove_unaccessed_vtfs(
        input_dir=input_dir,
        output_dir=output_dir,
        remove=remove,
        progress_window=progress_window,
    )


@register("REMOVE_VPK_CONTENT")
def logic_remove_vpk_files(
    input_dir: Path,
    output_dir: Path,
    progress_window=None,
):
    remove_vpk_files(
        input_dir=input_dir, output_dir=output_dir, progress_window=progress_window
    )


@register("SHRINK_SOLID_VTF")
def logic_shrink_solid(
    input_dir: Path,
    output_dir: Path,
    progress_window=None,
    override_flags: bool = False,
):
    handle_batch_parallel(
        input_dir=input_dir,
        output_dir=output_dir,
        ext=("vtf", "vtf"),
        opt_func=shrink_solid,
        progress_window=progress_window,
        override_flags=override_flags,
    )


@register("STEREO_TO_MONO_WAV")
def logic_wav_stereo_to_mono(
    input_dir: Path,
    output_dir: Path,
    progress_window=None,
    remove: bool = True,
):
    handle_batch_parallel(
        input_dir=input_dir,
        output_dir=output_dir,
        ext=("wav", "wav"),
        opt_func=wav_stereo_to_mono,
        progress_window=progress_window,
        remove=remove,
    )
    
    
@register("CONVERT_TO_DXT")
def logic_convert_to_dxt(
    input_dir: Path,
    output_dir: Path,
    progress_window=None,
):
    handle_batch_parallel(
        input_dir=input_dir,
        output_dir=output_dir,
        ext=("vtf", "vtf"),
        opt_func=convert_to_dxt,
        progress_window=progress_window,
    )


@register("WAV_TO_OGG")
def logic_wav_to_ogg(
    input_dir: Path,
    output_dir: Path,
    progress_window=None,
    level: int = 5,
    remove: bool = True,
):
    handle_batch_parallel(
        input_dir=input_dir,
        output_dir=output_dir,
        ext=("wav", "ogg"),
        opt_func=wav_to_ogg,
        progress_window=progress_window,
        quality=level,
        remove=remove,
    )
