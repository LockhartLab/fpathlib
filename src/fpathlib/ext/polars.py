
from polars import *
import polars as pl
from fpathlib import expand_fpath

def scan_csv(fpath, exclude_path_patterns=None, require_metadata=True, **kwargs):
    """
    Scan the paths in the collection as CSV files, and return a polars DataFrame.

    Parameters
    ----------
    fpath : :obj:`str`
        An f-string path, where the variables are captured and stored along the path
        name.
    exclude_path_patterns : :obj:`str` or :obj:`Iterable`[:obj:`str`]
        Exclude paths that match the supplied pattern. (Default: None).
    require_metadata : :obj:`bool`
        Require that all paths identified must have found metadata. (Default: True).   
    **kwargs
        Keyword arguments to pass to :meth:`polars.scan_csv`.

    Returns
    -------
    :obj:`polars.LazyFrame`
    """

    expanded_fpath = expand_fpath(
		fpath,
		exclude_path_patterns=exclude_path_patterns,
		require_metadata=require_metadata,
	)

    lf = pl.scan_csv(
        expanded_fpath,
        include_file_paths="fname",
        **kwargs,
    )

    lf = lf.join(
        expanded_fpath.to_polars(lazy=True),
        on="fname",
    )

    return lf
