import sys
import subprocess
from pathlib import Path

from .misc import exception_logger

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).resolve().parent
OGGENC_EXE = BASE_DIR / "oggenc2" / "oggenc2.exe"


def wav_to_ogg(input_file: Path, output_file: Path, quality: int = 5, remove: bool = True) -> bool:
    """
    Converts a WAV audio file to an OGG audio file using oggenc2
    
    :param input_file: The WAV file to convert.
    :type input_file: Path
    :param output_file: The OGG file to write to.
    :type output_file: Path
    :param quality: The bitrate "level" (-1 to 10) to encode the OGG with. -1 => lowest quality, smallest filesizes. 10 => highest quality, largest filesizes.
    :type quality: int
    :return: Whether the function completed successfully.
    :rtype: bool
    """

    try:
        command = [
            str(OGGENC_EXE),
            str(input_file),
            "-q", str(quality),
            "-o", str(output_file)
        ]
        subprocess.run(command, check=True, capture_output=True, text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW)
        if remove:
            input_file.unlink()

        return True
    except Exception as e:
        exception_logger(e)
        return False