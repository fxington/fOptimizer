import os
import shutil
import tomllib
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path


def exception_logger(exc: Exception):
    """
    Logs an exception to error.log.
    
    :param exc: The exception to log.
    :type exc: Exception
    """

    error = ''.join(traceback.format_exception(None, exc, exc.__traceback__))
    with open("error.log", "a") as log:
        log.write(error)


def get_project_version():
    try:
        path = Path(__file__).parent.parent.parent.parent.parent / "pyproject.toml" 
        with open(path, "rb") as f:
            data = tomllib.load(f)
            return data["project"]["version"]
    except Exception:
        return "0.0.0 (unknown)"


def fop_copy(
    src: Path,
    dst: Path,
    mode: int = 1,
) -> bool:
    try:
        if mode == 1:
            shutil.copy(src, dst)
        else:
            shutil.copy2(src, dst)
            
    except FileExistsError:
        pass
    except shutil.SameFileError:
        pass
    except Exception as e:
        exception_logger(e)


def size_bytes(input_path: Path) -> int:
    if(input_path.is_dir()):
        _helper = lambda input_dir: sum(f.stat().st_size
                                        if f.is_file()
                                        else _helper(f.path)
                                        for f in os.scandir(input_dir)
                                    )
        return _helper(input_path)
    else:
        return input_path.stat().st_size
    
    
def _universal_worker(
    tool_func,
    src: Path,
    dst: Path,
    ext: tuple[str],
    **kwargs,
):
    dst.parent.mkdir(parents=True, exist_ok=True)

    dst = dst.with_suffix(f".{ext[1]}")
    return tool_func(input_file=src, output_file=dst, **kwargs)


def handle_batch_parallel(
    input_dir: Path,
    output_dir: Path,
    ext: tuple[str],
    opt_func,
    progress_window=None,
    **kwargs,
):
    files = list(input_dir.rglob(f"*.{ext[0]}"))
    total = len(files)

    if total == 0:
        if progress_window:
            progress_window.update(0, 0)
        return

    with ProcessPoolExecutor() as executor:
        futures = {}
        for src in files:
            future = executor.submit(
                _universal_worker,
                opt_func,
                src,
                output_dir / src.relative_to(input_dir),
                ext=ext,
                **kwargs,
            )
            futures[future] = src

        for i, future in enumerate(as_completed(futures), 1):
            try:
                future.result()
            except Exception as e:
                print(f"Error processing {futures[future].name}: {e}")

            if progress_window and (i % 10 == 0 or i == total):
                progress_window.update(i, total)


def interp_hex_color(
    hex_start: str,
    hex_end: str,
    progress: float,
) -> str:
    # https://gist.github.com/setuc/c6f0491163ee4622cc03f181fa67c854
    start_rgb = tuple(int(hex_start.strip("#")[i:i+2], 16) for i in (0, 2, 4))
    end_rgb = tuple(int(hex_end.strip("#")[i:i+2], 16) for i in (0, 2, 4))

    result_rgb = tuple(
        round(s + (e - s) * progress)
        for s, e in zip(start_rgb, end_rgb)
    )

    interpolated = "#{:02x}{:02x}{:02x}".format(*result_rgb)
    return interpolated
