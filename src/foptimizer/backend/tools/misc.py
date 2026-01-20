import os
import shutil
import traceback
from pathlib import Path

import tomllib

def exception_logger(exc: Exception) -> None:
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


def fop_copy(src: Path, dst: Path, mode: int = 1) -> bool:
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