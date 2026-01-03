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