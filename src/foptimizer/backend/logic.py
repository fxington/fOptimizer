from pathlib import Path
from sourcepp import vtfpp

from .tools.remove_redundancies import remove_unused_files, remove_unaccessed_vtfs
from .tools.image_conversion import optimize_png, fit_alpha, is_normal, resize_vtf, shrink_solid
from .tools.audio_conversion import wav_to_ogg

FOPTIMIZER_FLAG_INDEX = 19


def get_enabled_flag_indices(vtf: vtfpp.VTF):
    total_sum = vtf.flags
    enabled_indexes = []
    index = 0
    
    while total_sum > 0:
        if total_sum & 1:
            enabled_indexes.append(index)
        total_sum >>= 1
        index += 1
    return enabled_indexes


def handle_batch(input_dir: Path, output_dir: Path, extension: str, progress_bar=None):
    output_dir.mkdir(parents=True, exist_ok=True)
    
    files = list(input_dir.rglob(f"*.{extension}"))
    total = len(files)
    
    if total == 0:
        if progress_bar:
            progress_bar.set(0)
        return

    for i, src in enumerate(files, 1):
        relative_path = src.relative_to(input_dir)
        dst = output_dir / relative_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        
        yield src, dst
        
        if progress_bar:
            progress_bar.set(i / total)


def logic_remove_unused_files(input_dir: Path, output_dir: Path, remove: bool, progress_bar=None):
    if progress_bar: progress_bar.set(0.1)
    remove_unused_files(input_dir=input_dir, output_dir=output_dir, remove=remove)
    if progress_bar: progress_bar.set(1.0)


def logic_optimize_png(input_dir: Path, output_dir: Path, level: int = 6, lossless: bool = True, progress_bar=None):
    for src, dst in handle_batch(input_dir, output_dir, "png", progress_bar):
        optimize_png(input_file=src, output_file=dst, level=level, lossless=lossless)


def logic_fit_alpha(input_dir: Path, output_dir: Path, lossless: bool, progress_bar=None):
    for src, dst in handle_batch(input_dir, output_dir, "vtf", progress_bar):
        vtf = vtfpp.VTF(str(src))
        fit_alpha(vtf=vtf, output_file=dst, lossless=lossless)


def logic_halve_normals(input_dir: Path, output_dir: Path, progress_bar=None):
    for src, dst in handle_batch(input_dir, output_dir, "vtf", progress_bar):
        vtf = vtfpp.VTF(str(src))
        enabled_flags = get_enabled_flag_indices(vtf)
        
        if is_normal(vtf) and FOPTIMIZER_FLAG_INDEX not in enabled_flags:
            width = max(4, vtf.width // 2)
            height = max(4, vtf.height // 2)
            
            resize_vtf(vtf=vtf, output_file=dst, w=width, h=height)

            halved_vtf = vtfpp.VTF(str(dst))
            halved_vtf.add_flags(1 << FOPTIMIZER_FLAG_INDEX)
            halved_vtf.bake_to_file(str(dst))


def logic_shrink_solid(input_dir: Path, output_dir: Path, progress_bar=None):
    for src, dst in handle_batch(input_dir, output_dir, "vtf", progress_bar):
        vtf = vtfpp.VTF(str(src))
        shrink_solid(vtf=vtf, output_file=dst)


def logic_wav_to_ogg(input_dir: Path, output_dir: Path, level: int = 5, remove: bool = True, progress_bar=None):
    for src, dst in handle_batch(input_dir, output_dir, "wav", progress_bar):
        ogg_dst = dst.with_suffix(".ogg")
        wav_to_ogg(input_file=src, output_file=ogg_dst, quality=level, remove=remove)


def logic_remove_unaccessed_vtfs(input_dir: Path, output_dir: Path, remove: bool = True, progress_bar=None):
    if progress_bar: progress_bar.set(0.1)
    remove_unaccessed_vtfs(input_dir=input_dir, output_dir=output_dir, remove=remove)
    if progress_bar: progress_bar.set(1.0)