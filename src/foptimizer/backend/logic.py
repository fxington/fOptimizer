from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

from .tools.remove_redundancies import remove_unused_files, remove_unaccessed_vtfs
from .tools.image_conversion import optimize_png, fit_alpha, shrink_solid, halve_normal
from .tools.audio_conversion import wav_to_ogg
from .tools.patcher import remove_duplicate_vtfs

def _universal_worker(tool_func, src: Path, dst: Path, ext: tuple[str], **kwargs):
    dst.parent.mkdir(parents=True, exist_ok=True)
    
    dst = dst.with_suffix(f".{ext[1]}")
    return tool_func(input_file=src, output_file=dst, **kwargs)


def handle_batch_parallel(input_dir: Path, output_dir: Path, ext: tuple[str], opt_func, progress_window=None, **kwargs):
    files = list(input_dir.rglob(f"*.{ext[0]}"))
    total = len(files)
    
    if total == 0:
        if progress_window:
            progress_window.update(0, 0)
        return

    with ProcessPoolExecutor() as executor:
        futures = {}
        for src in files:
            future = executor.submit(_universal_worker, opt_func, src, output_dir / src.relative_to(input_dir), ext=ext, **kwargs)
            futures[future] = src

        for i, future in enumerate(as_completed(futures), 1):
            try:
                future.result()
            except Exception as e:
                print(f"Error processing {futures[future].name}: {e}")
            
            if progress_window:
                progress_window.update(i, total)


def logic_optimize_png(input_dir: Path, output_dir: Path, level: int = 6, lossless: bool = True, progress_window=None):
    handle_batch_parallel(input_dir=input_dir,
                          output_dir=output_dir,
                          ext=("png", "png"),
                          opt_func=optimize_png,
                          progress_window=progress_window,
                          level=level,
                          lossless=lossless
    )


def logic_fit_alpha(input_dir: Path, output_dir: Path, lossless: bool, progress_window=None):
    handle_batch_parallel(input_dir=input_dir,
                          output_dir=output_dir,
                          ext=("vtf", "vtf"),
                          opt_func=fit_alpha,
                          progress_window=progress_window,
                          lossless=lossless
    )


def logic_halve_normals(input_dir: Path, output_dir: Path, progress_window=None):
    handle_batch_parallel(input_dir=input_dir,
                          output_dir=output_dir,
                          ext=("vtf", "vtf"),
                          opt_func=halve_normal,
                          progress_window=progress_window
    )


def logic_shrink_solid(input_dir: Path, output_dir: Path, progress_window=None):
    handle_batch_parallel(input_dir=input_dir,
                          output_dir=output_dir,
                          ext=("vtf", "vtf"),
                          opt_func=shrink_solid,
                          progress_window=progress_window
    )


def logic_wav_to_ogg(input_dir: Path, output_dir: Path, level: int = 5, remove: bool = True, progress_window=None):
    handle_batch_parallel(input_dir=input_dir,
                          output_dir=output_dir,
                          ext=("wav", "ogg"),
                          opt_func=wav_to_ogg,
                          progress_window=progress_window,
                          quality=level,
                          remove=remove
    )


def logic_remove_unaccessed_vtfs(input_dir: Path, output_dir: Path, remove: bool = True, progress_window=None):
    remove_unaccessed_vtfs(input_dir=input_dir,
                           output_dir=output_dir,
                           remove=remove,
                           progress_window=progress_window
    )


def logic_remove_unused_files(input_dir: Path, output_dir: Path, remove: bool, progress_window=None):
    remove_unused_files(input_dir=input_dir,
                        output_dir=output_dir,
                        remove=remove,
                        progress_window=progress_window
    )

def logic_remove_duplicate_vtfs(input_dir: Path, output_dir: Path, progress_window=None):
    remove_duplicate_vtfs(input_dir=input_dir,
                          output_dir=output_dir,
                          progress_window=progress_window
    )