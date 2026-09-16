from collections.abc import Sequence
from glob import glob, iglob
import parse
import re

from .path import Path
from .utils import import_optional_dependency


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
        self.fpath = str(fpath)  # must be string, not Path or something else

    def __repr__(self):
        return "FPath({!r})".format(self.fpath)

    def _compile_parser(self):
        """
        Compile `self.fpath` for metadata extraction, after checking it
        doesn't mix a {} named capture with a bare glob wildcard outside of
        one -- shared by :meth:`.expand` and :meth:`.iexpand`.
        """

        parser = parse.compile(self.fpath)

        # glob() (used to find files) and `parse` (used above to extract
        # {name} values) disagree about what a bare '*', '?', or '[...]'
        # means outside a {} capture: glob treats it as a wildcard, but
        # parse's format-string language only special-cases {...} and
        # reads everything else -- including '*' -- as literal text to
        # match. A pattern like "{a}/*" would find files fine via glob()
        # but then fail to parse against that same string, since real
        # filenames don't literally contain "/*" -- silently producing
        # metadata=None for every match, or raising a confusing "metadata
        # not found" error, with no indication that '*' was the actual
        # problem. Fail fast and explain it instead. Only applies when
        # there's a {} capture to begin with -- a plain glob with none is a
        # separate, unaffected case (no metadata is expected from it).
        if parser.named_fields:
            literal_fpath = re.sub(r"\{.*?\}", "", self.fpath)
            for c in "*?[":
                if c in literal_fpath:
                    msg = (
                        f"glob wildcard {c!r} outside a {{}} capture is not "
                        f"supported in {self.fpath!r} -- 'parse' treats it "
                        "as a literal character, not a wildcard. Use a "
                        "named capture (e.g. '{a}/{b}') if you want that "
                        "segment captured too."
                    )
                    raise ValueError(msg)

        return parser

    def iexpand(self, exclude_path_patterns=None, require_metadata=True, errors="raise"):
        """
        Lazily yield each :obj:`.Path` matching the f-string pattern, one at
        a time, instead of building the whole :obj:`.ExpandedFPath` up
        front. Useful when a pattern could match a very large number of
        files and you don't want them all held in memory at once, or want
        to start processing before the full glob finishes walking the
        filesystem. :meth:`.expand` is built on top of this generator.

        Parameters
        ----------
        exclude_path_patterns : :obj:`str` or :obj:`Iterable`[:obj:`str`]
            Exclude paths that match the supplied pattern. (Default: None).
        require_metadata : :obj:`bool`
            Require that all paths identified must have found metadata. (Default: True).
        errors : :obj:`str`
            How to handle the "no matches" case, checked once the pattern is
            fully exhausted. If "raise", then raise an error. If "warn",
            then warn. If "ignore", then do nothing. (Default: "raise").

        Yields
        ------
        :obj:`.Path`
        """

        # Validate and compile eagerly, here in a plain (non-generator)
        # method, so a bad `errors` value or an unsupported wildcard/{}
        # mix raises as soon as iexpand() is called -- not deferred until
        # whatever code actually starts iterating the result, which is the
        # usual surprise with putting validation inside a generator
        # function's body.
        if errors not in {"raise", "warn", "ignore"}:
            msg = f"invalid value for 'errors': {errors}"
            raise ValueError(msg)

        parser = self._compile_parser()

        return self._iexpand(parser, exclude_path_patterns, require_metadata, errors)

    def _iexpand(self, parser, exclude_path_patterns, require_metadata, errors):
        n = 0
        for fname in iglob(re.sub(r"\{.*?\}", "*", self.fpath)):
            path = Path(fname)
            if exclude_path_patterns and path.match_any(exclude_path_patterns):
                continue
            path.metadata = getattr(parser.parse(fname), "named", None)
            if require_metadata and path.metadata is None:
                msg = f"metadata not found for '{fname}' with '{self.fpath}'"
                raise AttributeError(msg)
            n += 1
            yield path

        if n == 0 and errors != "ignore":
            msg = f"no paths found for {self.fpath.__repr__()}"
            if errors == "raise":
                raise IOError(msg)
            elif errors == "warn":
                import warnings

                warnings.warn(msg)

    def expand(self, exclude_path_patterns=None, require_metadata=True, errors="raise"):
        """
        Use an f-string to extract out a collection of paths, where the f-string
        variables are captured and stored along the path name.

        Parameters
        ----------
        exclude_path_patterns : :obj:`str` or :obj:`Iterable`[:obj:`str`]
            Exclude paths that match the supplied pattern. (Default: None).
        require_metadata : :obj:`bool`
            Require that all paths identified must have found metadata. (Default: True).
        errors : :obj:`str`
            How to handle errors. If "raise", then raise an error. If "warn", then warn
            and return an empty collection. If "ignore", then ignore the error and
            return an empty collection. (Default: "raise").

        Returns
        -------
        :obj:`.ExpandedFPath`
        """

        paths = list(
            self.iexpand(
                exclude_path_patterns=exclude_path_patterns,
                require_metadata=require_metadata,
                errors=errors,
            )
        )

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

    # TODO fix value types?
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

        pl = import_optional_dependency("polars")

        # `value` is None whenever this ExpandedFPath was built with
        # require_metadata=False and a path's metadata simply wasn't found
        # (e.g. a plain glob with no named captures at all) -- treat that as
        # "no metadata columns" rather than crashing on `**None`.
        data = [
            {"fname": str(key), **(value or {})} for key, value in self.metadata.items()
        ]
        df = pl.DataFrame(data)
        if lazy:
            df = df.lazy()
        return df
