
from polars import *
import polars as pl
from fpathlib import expand_fpath_decorator

@expand_fpath_decorator 
def scan_csv(expanded_fpath, *args, **kwargs):
    """
    Scan the paths in the collection as CSV files, and return a 
	:obj:`polars.LazyFrame` along with the metadata captured from the path 
	variables.

    Parameters
    ----------
	expanded_fpath : :obj:`fpathlib.ExpandedFPath`
		An expanded f-string path, where the variables are captured and stored. 
	*args
		Positional arguments to pass to :meth:`polars.scan_csv`.
    **kwargs
        Keyword arguments to pass to :meth:`polars.scan_csv`.

    Returns
    -------
    :obj:`polars.LazyFrame`
    """

    lf = pl.scan_csv(
        expanded_fpath,
        include_file_paths="fname",
		*args,
        **kwargs,
    )

    lf = lf.join(
        expanded_fpath.to_polars(lazy=True),
        on="fname",
    )

