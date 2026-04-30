from collections.abc import Sequence
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

    def match(self, path_patterns, case_sensitive=None):
        """
        Perform :meth:`pathlib.Path.match` on several `path_patterns`.

        Parameters
        ----------
        path_patterns : :obj:`str` or :obj:`Iterable`[:obj:`str`]
            One or more path patterns to match against. (Default: None).
        case_sensitive : :obj:`bool`
            Whether to perform case-sensitive matching. If None, the default, then the
            behavior is determined by the operating system. (Default: None).

        Returns
        -------
        :obj:`generator`[:obj:`bool`]
        """

        if isinstance(path_patterns, str):
            path_patterns = [path_patterns]

        for path_pattern in path_patterns:
            yield super().match(path_pattern, case_sensitive=case_sensitive)

    def match_all(self, path_patterns, case_sensitive=None):
        """
        Perform :meth:`pathlib.Path.match` on several `path_patterns`. All patterns
        must match.

        Parameters
        ----------
        path_patterns : :obj:`str` or :obj:`Iterable`[:obj:`str`]
            One or more path patterns to match against. (Default: None).
        case_sensitive : :obj:`bool`
            Whether to perform case-sensitive matching. If None, the default, then the
            behavior is determined by the operating system. (Default: None).

        Returns
        -------
        :obj:`bool`
        """

        for match in self.match(path_patterns, case_sensitive=case_sensitive):
            if not match:
                return False

        return True

    def match_any(self, path_patterns, case_sensitive=None):
        """
        Perform :meth:`pathlib.Path.match` on several `path_patterns`. Any pattern
        must match.

        Parameters
        ----------
        path_patterns : :obj:`str` or :obj:`Iterable`[:obj:`str`]
            One or more path patterns to match against. (Default: None).
        case_sensitive : :obj:`bool`
            Whether to perform case-sensitive matching. If None, the default, then the
            behavior is determined by the operating system. (Default: None).

        Returns
        -------
        :obj:`bool`
        """

        for match in self.match(path_patterns):
            if match:
                return True

        return False


class FPath:
    """
    :obj:`FPath` is an f-string version of :obj:`Path`. This does not behave like a
    typical Path, because typically there are several matches to the f-string Path.
    Therefore, the :meth:`.FPath.expand` method must be used to create an
    :obj:`ExpandedFPath` that lists all the possibilities.

    Parameters
    ----------
    fpath : :obj:`str`
        An f-string path, where the variables are captured and stored along the path
        name.

    Returns
    -------
    :obj:`.FPath`
    """

    def __init__(self, fpath):
        self.fpath = fpath

    def __repr__(self):
        return "FPath({!r})".format(self.fpath)

    def expand(self, exclude_path_patterns=None, require_metadata=True):
        """
        Use an f-string to extract out a collection of paths, where the f-string
        variables are captured and stored along the path name.

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

        return ExpandedFPath(paths=paths, fpath=self)


# TODO does scan_csv belong here?
class ExpandedFPath(Sequence):
    """
    :obj:`ExpandedFPath` is the result of expanding an :obj:`FPath`. It is a
    collection of :obj:`Path` objects that match the f-string pattern, and their
    associated metadata.

    Parameters
    ----------
    paths : :obj:`Iterable`[:obj:`Path`]
        A collection of :obj:`Path` objects that match the f-string pattern, and their
        associated metadata.
    fpath : :obj:`FPath`
        The original :obj:`FPath` that was expanded to create this
        :obj:`ExpandedFPath`.
    """

    def __init__(self, paths, fpath):
        if len(paths) != len(set(paths)):
            raise AttributeError("paths are not unique")
        self.paths = paths
        self.fpath = fpath

    def __getitem__(self, item):
        return self.paths[item]

    def __len__(self):
        return len(self.paths)

    def __repr__(self):
        n = len(self)

        txt = f"{self.fpath.__repr__()}\n\n"
        txt += f"{n} matches found:\n\n"

        for path in self.paths[:10]:
            txt += f"{repr(path)}\n"
        if n > 10:
            txt += "...\n"

        return txt

    @property
    def metadata(self):
        """
        Return the metadata for each path in the collection.

        Returns
        -------
        :obj:`dict`[:obj:`str`, :obj:`dict`]
        """

        metadata = {path: path.metadata for path in self.paths}
        return metadata

    def to_polars(self, lazy=False):
        """
        Convert the metadata for each path in the collection to a polars DataFrame.

        Parameters
        ----------
        lazy : :obj:`bool`
            Return a lazy polars DataFrame? (Default: False).

        Returns
        -------
        :obj:`polars.DataFrame` or :obj:`polars.LazyFrame`
        """

        try:
            import polars as pl
        except ImportError:
            msg = "`polars` must be installed to use this feature"
            raise ImportError(msg)

        data = [{"fname": str(key), **value} for key, value in self.metadata.items()]
        df = pl.DataFrame(data)
        if lazy:
            df = df.lazy()
        return df


def expand_fpath(fpath, exclude_path_patterns=None, require_metadata=True):
    """
    Use an f-string to extract out a collection of paths, where the f-string variables
    are captured and stored along the path name. This is a convenience function that
    simply creates an :obj:`FPath` and calls its :meth:`.expand` method.

    Parameters
    ----------
    fpath : :obj:`str`
        An f-string path, where the variables are captured and stored along the path
        name.
    exclude_path_patterns : :obj:`str` or :obj:`Iterable`[:obj:`str`]
        Exclude paths that match the supplied pattern. (Default: None).
    require_metadata : :obj:`bool`
        Require that all paths identified must have found metadata. (Default: True).

    Returns
    -------
    :obj:`.ExpandedFPath`
    """

    return FPath(fpath).expand(
        exclude_path_patterns=exclude_path_patterns,
        require_metadata=require_metadata,
    )
