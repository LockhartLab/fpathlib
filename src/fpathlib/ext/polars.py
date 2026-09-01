from functools import wraps
from polars import *
import polars as pl
from fpathlib import expand_fpath_decorator, ExpandedFPath

def join_metadata(df, expanded_fpath):
    return df.join(
        expanded_fpath.to_polars(lazy=isinstance(df, pl.LazyFrame)),
        on="fname",
    )


@expand_fpath_decorator(post_process=join_metadata)
def read_csv(expanded_fpath, *args, **kwargs):
    """
    Read the paths in the collection as CSV files, and return a
    :obj:`polars.DataFrame` along with the metadata captured from the path
    variables.

    Parameters
    ----------
    expanded_fpath : :obj:`fpathlib.ExpandedFPath`
        An expanded f-string path.
    *args
        Positional arguments to pass to :meth:`polars.read_csv`.
    **kwargs
        Keyword arguments to pass to :meth:`polars.read_csv`.

    Returns
    -------
    :obj:`polars.DataFrame`
    """

    return scan_csv.__wrapped__(expanded_fpath, *args, **kwargs).collect()


@expand_fpath_decorator(post_process=join_metadata)
def read_txt(
    expanded_fpath,
    filter_expr=None,
    separator=None,
    new_columns=None,
    has_header=False,
    *args,
    **kwargs,
):
    """
    Read the paths in the collection as text files, where each line is a
    record, and return a :obj:`polars.DataFrame` along with the metadata
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
        Positional arguments to pass to :meth:`polars.read_csv`.
    **kwargs
        Keyword arguments to pass to :meth:`polars.read_csv`.

    Returns
    -------
    :obj:`polars.DataFrame`
    """

    return scan_txt.__wrapped__(
        expanded_fpath,
        filter_expr=filter_expr,
        separator=separator,
        new_columns=new_columns,
        has_header=has_header,
        *args,
        **kwargs,
    ).collect()


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

# TODO rename expanded_fpath as source
@expand_fpath_decorator(require_expandable=False, post_process=join_metadata)
def scan_txt(
    expanded_fpath,
    filter_expr=None,
    separator=None,
    new_columns=None,
    has_header=False,
    keep_line=False,
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
    keep_line : :obj:`bool`
        Whether to keep the original line as a column in the output. 
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

    # TODO schema and schema_overrides is probably broken

    lf = pl.scan_csv(
        expanded_fpath,
        include_file_paths="fname",
        separator="\n",
        new_columns=["line"],
        has_header=False,
        **kwargs,
    )

    expanded_fpath0 = expanded_fpath
    if isinstance(expanded_fpath, ExpandedFPath):
        expanded_fpath0 = expanded_fpath[0]
    lf0 = scan_txt(
        expanded_fpath0,
        filter_expr=filter_expr,
        separator=separator,
        new_columns=new_columns,
        has_header=has_header,
        keep_line=keep_line,
        *args,
        **kwargs,
    ).head(kwargs.get("infer_schema_length", 100))
            
    # Can filter lines before doing any further processing
    # This could be to remove lines with comments, etc.
    if filter_expr is not None:
        lf = lf.filter(filter_expr)

    # Separate lines into fields using `separator`
    if separator is not None:
        # Separate line into fields by separator
        lf = lf.with_columns(
            pl.col("line").str.split(separator, literal=False).alias("fields")
        )

        if not keep_line:
            lf = lf.drop("line")

        # Count the number of fields
        n_fields = lf0.select(pl.col("fields").list.len().unique()).collect().item()
        
        # Initial field names, may be renamed later from header or by `new_columns`
        fields = [f"field_{i}" for i in range(n_fields)]

        lf = lf.with_columns(
            [
                pl.col("fields").list.get(i).alias(field)
                for i, field in enumerate(fields)
            ]
        ).drop("fields")

        # LazyFrame does not guarantee order, so the header might not be the first row
        # This can be fixed by scan_csv with include_row_index. But this seems clunky
        if has_header:
            """
            first_row = lf.head(1).collect()
            header.to_pandas().transpose()[0].to_dict()
            lf = lf.slice(offset=1, length=None)
            header = first_row.select(pl.col(fields)).to_dict(as_series=False)
            lf = lf.rename({field: header[field][0] for field in fields})
            """
            raise NotImplementedError

        if new_columns is not None:
            lf = lf.rename(
                {field: new_column for field, new_column in zip(fields, new_columns)}
            )

        # Infer dtypes?
        if kwargs.get("infer_schema", True):
            sample = (
                lf0.collect()
                .write_csv()
                .encode()
            )
            inferred_schema = pl.read_csv(sample).schema
            lf = lf.cast(inferred_schema)

    return lf
