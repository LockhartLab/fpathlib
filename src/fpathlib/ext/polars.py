from functools import wraps
from polars import *
import polars as pl
from fpathlib import expand_fpath_decorator


def join_metadata(df, expanded_fpath):
    return df.join(
        expanded_fpath.to_polars(lazy=isinstance(df, pl.LazyFrame)),
        on="fname",
    )


@expand_fpath_decorator(post_process=join_metadata)
def scan_csv(expanded_fpath, *args, **kwargs):
    """
    Scan the paths in the collection as CSV files, and return a
        :obj:`polars.LazyFrame` along with the metadata captured from the path
        variables.

    Parameters
    ----------
        expanded_fpath : :obj:`fpathlib.ExpandedFPath`
                An expanded f-string path.
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

    return lf


@expand_fpath_decorator(post_process=join_metadata)
def scan_txt(
    expanded_fpath,
    filter_expr=None,
    separator=None,
    new_columns=None,
    has_header=False,
    *args,
    **kwargs,
):
    """
    Scan the paths in the collection as text files, where each line is a
    record, and return a :obj:`polars.LazyFrame` along with the metadata
    captured from the path. The text files can also be delimited by
    `separator`, in which case the lines are split by the separator and each
    field is a record. The names of these field can be set by `new_columns`.

    Parameters
    ----------
    expanded_fpath : :obj:`fpathlib.ExpandedFPath`
        An expanded f-string path.
    filter_expr : :obj:`polars.Expr`, optional
        Filter the lines before splitting by the separator (if provided).
    separator : :obj:`str`, optional
        Deliminatorg to split each line into fields.
    new_columns : :obj:`list`[:obj:`str`], optional
        List of new column names to rename the fields after splitting by the separator.
        If not provided, the fields are named as `field_0`, `field_1`, etc.
    has_header : :obj:`bool`
        Whether the text files have a header line that should be skipped. The header
        must have the same delimiter as the separator provided in `separator`.
        (Default: False)
    *args
        Positional arguments to pass to :meth:`polars.scan_csv`.
    **kwargs
        Keyword arguments to pass to :meth:`polars.scan_csv`.

    Returns
    -------
    :obj:`polars.LazyFrame`
    """

    # TODO there are forbidden variables that should not be in expanded_fpath
    # such as 'line' and 'fields' and 'fname'

    lf = pl.scan_csv(
        expanded_fpath,
        include_file_paths="fname",
        separator="\n",
        new_columns=["line"],
        has_header=False,
        **kwargs,
    )

    if filter_expr is not None:
        lf = lf.filter(filter_expr)

    if separator is not None:
        lf = lf.with_columns(fields=pl.col("line").str.split(separator, literal=False))
        n_fields = lf.select(pl.col("fields").list.len().unique()).collect()
        if n_fields.shape[0] > 1:
            msg = "number of fields must be consistent across all lines", n_fields
            raise ValueError(msg)
        n_fields = n_fields.item()
        lf = lf.with_columns(
            [pl.col("fields").list.get(i).alias(f"field_{i}") for i in range(n_fields)]
        ).drop(["fields", "line"])

        if new_columns is not None:
            lf = lf.rename({f"field_{i}": col for i, col in enumerate(new_columns)})

    return lf
