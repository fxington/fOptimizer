from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("foptimizer")
except PackageNotFoundError:
    __version__ = "unknown"