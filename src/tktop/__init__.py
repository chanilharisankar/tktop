from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("tktop")
except PackageNotFoundError:
    __version__ = "1.1.0"
