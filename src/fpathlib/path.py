from glob import glob
import parse
import pathlib
import re


class Path(pathlib.Path):
    """
    :obj:`Path` is simply :obj:`pathlib.Path` with metadata.
        
    Parameters
    ----------
    *pathsegments 
    """

    def __init__(self, *pathsegments, metadata=None):
        super().__init__(*pathsegments)
        self.metadata = metadata

    def match_any(self, path_patterns):
        """
        Perform :meth:`pathlib.Path.match` on several `path_patterns`.

        Returns
        -------
        :obj:`bool`
        """

        if isinstance(path_patterns, str):
            path_patterns = [path_patterns]
  
        for path_pattern in path_patterns:
            if self.match(path_pattern):
                return True

        return False


class FPath:
    """
    :obj:`FPath` is an f-string version of :obj:`Path`. This does not behave like a typical Path, because typically there are several matches to the f-string Path. Therefore, the :meth:`.FPath.expand` method must be used to create an :obj:`ExpandedFPath` that lists all the possibilities.

    Example:
    

    Parameters
    ----------
    fpath : :obj:`str`

    Returns
    -------
    :obj:`.FPath`
    """

    def __init__(self, fpath):
        self.fpath = fpath

    def expand(self, exclude_path_patterns=None, require_metadata=True):
        """
        Use an f-string to extract out a collection of paths, where the f-string variables are captured and stored along the path name.
    
        Parameters
        ----------
        exclude_path_patterns : :obj:`str` or :obj:`Iterable`[:obj:`str`]
            Exclude paths that match the supplied pattern. (Default: None).
        require_metadata : :obj:`bool`
            Require that all paths identified must have found metadata. (Default: True).

        Returns
        -------
        :obj:`.ExpandedFPath`
        """
    
        parser = parse.compile(self.fpath)
    
        paths = []
        for fname in glob(re.sub(r"\{.*?\}", "*", self.fpath)):
            path = Path(fname)
            if exclude_path_patterns and path.match_any(exclude_path_patterns):
                continue
            path.metadata = getattr(parser.parse(fname), "named", None)
            if require_metadata and path.metadata is None:
                msg = f"metadata not found for '{fname}' with fstring '{fstring}'"
                raise AttributeError(msg)
            paths.append(path)
    
        return ExpandedFPath(paths)


# TODO does scan_csv belong here?
class ExpandedFPath:
    def __init__(self, paths, path_pattern):
        if len(paths) != len(set(paths)):
            raise AttributeError("paths are not unique")
        self.paths = paths
        self.path_pattern = path_pattern

    def __getitem__(self, item):
        return self.paths[item]

    def __len__(self):
        return len(self.paths)

    @property
    def metadata(self):
        metadata = {path: path.metadata for path in self.paths}
        return metadata

    def to_polars(self, lazy=False):
        data = [{"fname": str(key), **value} for key, value in self.metadata.items()]
        df = pl.DataFrame(data)
        if lazy:
            df = df.lazy()
        return df


def expand_fpath(fpath, exclude=None, require_metadata=True):
    """
    """

    return FPath(fpath).expand(exclude=exclude, require_metadata=require_metadata)
