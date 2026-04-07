from collections.abc import Sequence
from glob import glob
import numpy as np
import parse
import pathlib
import polars as pl
import re


class Path(pathlib.Path):
    def __init__(self, path, metadata=None):
        super().__init__(path)
        self.metadata = metadata

    def match(self, path_pattern):
        for path_pattern in np.hstack([path_pattern]):
            if super().match(path_pattern):
                return True
        return False

# TODO does scan_csv belong here?
class Paths(Sequence):
    def __init__(self, paths):
        if len(paths) != len(set(paths)):
            raise AttributeError("paths are not unique")
        self.paths = paths

    def __getitem__(self, item):
        return self.paths[item]

    def __len__(self):
        return len(self.paths)

    @property
    def metadata(self):
        metadata = {path: path.metadata for path in self.paths}
        return metadata

    def to_frame(self):
        data = [{"fname": str(key), **value} for key, value in self.metadata.items()]
        return pl.DataFrame(data)

    def to_polars(self, lazy=False):
        df = self.to_frame()
        if lazy:
            df = df.lazy()
        return df


def var_paths(fstring, exclude=None, require_metadata=True):
    """
    Use an f-string to extract out a collection of paths, where the f-string variables are captured and stored along the path name.

    Parameters
    ----------
    fstring : :obj:`str`
    exclude : :obj:`bool`
    require_metadata : :obj:`bool`
    """

    parser = parse.compile(fstring)

    paths = []
    for fname in glob(re.sub(r"\{.*?\}", "*", fstring)):
        path = Path(fname)
        if exclude and path.match(exclude):
            continue
        path.metadata = getattr(parser.parse(fname), "named", None)
        if require_metadata and path.metadata is None:
            msg = f"metadata not found for '{fname}' with fstring '{fstring}'"
            raise AttributeError(msg)
        paths.append(path)

    return Paths(paths)
