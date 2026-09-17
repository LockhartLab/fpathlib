from functools import wraps
import polars as _polars
from fpathlib import expand_fpath_decorator, ExpandedFPath


def __getattr__(name):
    # Delegates any attribute this module doesn't define itself to the real
    # polars module, so `fpathlib.ext.polars` remains a drop-in replacement for
    # `import polars` (pl.DataFrame, pl.col, pl.List, etc. all still resolve).
    # Unlike `from polars import *`, this only kicks in for names Python didn't
    # already find defined here, so it can't silently shadow builtins like
    # `list` or `len` for this module's own implementation code.
    return getattr(_polars, name)


def join_metadata(df, expanded_fpath):
    # "fname" is ExpandedFPath.to_polars()'s normal, public column name --
    # rename it to the same reserved "_fname" that scan_csv/scan_parquet/
    # scan_txt use internally, so the join key can never collide with an
    # `include_file_paths` name a caller chose (including "fname" itself).
    metadata = expanded_fpath.to_polars(lazy=isinstance(df, _polars.LazyFrame))
    metadata = metadata.rename({"fname": "_fname"})
    return df.join(metadata, on="_fname").drop("_fname")


@expand_fpath_decorator(postprocess=join_metadata)
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


@expand_fpath_decorator(postprocess=join_metadata)
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


@expand_fpath_decorator(postprocess=join_metadata)
def scan_csv(expanded_fpath, include_file_paths=None, *args, **kwargs):
    """
    Scan the paths in the collection as CSV files, and return a
    :obj:`polars.LazyFrame` along with the metadata captured from the path
    variables.

    Parameters
    ----------
    expanded_fpath : :obj:`fpathlib.ExpandedFPath`
        An expanded f-string path.
    include_file_paths : :obj:`str`, optional
        Name to give a column of each row's source file path in the
        output. The file path is always used internally to join captured
        metadata; without this, it isn't kept in the result. (Default: None)
    *args
        Positional arguments to pass to :meth:`polars.scan_csv`.
    **kwargs
        Keyword arguments to pass to :meth:`polars.scan_csv`.

    Returns
    -------
    :obj:`polars.LazyFrame`
    """

    lf = _polars.scan_csv(
        expanded_fpath,
        include_file_paths="_fname",
        *args,
        **kwargs,
    )

    if include_file_paths is not None:
        lf = lf.with_columns(_polars.col("_fname").alias(include_file_paths))

    return lf


@expand_fpath_decorator(postprocess=join_metadata)
def scan_parquet(expanded_fpath, include_file_paths=None, *args, **kwargs):
    """
    Scan the paths in the collection as a parquet file, and return a
    :obj:`polars.LazyFrame` along with the metadata captured from the path
    variables.

    Parameters
    ----------
    expanded_fpath : :obj:`fpathlib.ExpandedFPath`
        An expanded f-string path.
    include_file_paths : :obj:`str`, optional
        Name to give a column of each row's source file path in the
        output. The file path is always used internally to join captured
        metadata; without this, it isn't kept in the result. (Default: None)
    *args
        Positional arguments to pass to :meth:`polars.scan_parquet`.
    **kwargs
        Keyword arguments to pass to :meth:`polars.scan_parquet`.

    Returns
    -------
    :obj:`polars.LazyFrame`
    """

    lf = _polars.scan_parquet(
        expanded_fpath,
        include_file_paths="_fname",
        *args,
        **kwargs,
    )

    if include_file_paths is not None:
        lf = lf.with_columns(_polars.col("_fname").alias(include_file_paths))

    return lf


# TODO rename expanded_fpath as source
@expand_fpath_decorator(postprocess=join_metadata)
def scan_txt(
    expanded_fpath,
    filter_expr=None,
    separator=None,
    new_columns=None,
    has_header=False,
    keep_line=False,
    include_file_paths=None,
    usecols=None,
    validate_schema=True,
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
    include_file_paths : :obj:`str`, optional
        Name to give a column of each row's source file path in the
        output. The file path is always used internally to join captured
        metadata; without this, it isn't kept in the result. (Default: None)
    usecols : :obj:`list`[:obj:`int`], optional
        Indexes of columns to keep in the output. If not provided, all columns are kept. Only applicable if `separator` is provided.
    validate_schema : :obj:`bool`
        When the field count is inferred from a single representative file
        (the fast path for a multi-file glob/pattern), also check that no
        *other* matched file has *more* fields than that sample. A file with
        fewer fields than the sample already raises a clear polars error
        (out-of-bounds list access); a file with more fields would otherwise
        have its extra columns silently dropped instead of erroring. This
        check reads every matched file's line count, which costs an extra
        full pass over the data on top of the fast path -- pass False if
        you've already confirmed your files are consistent and want to
        skip it for speed on very large globs. (Default: True)
    *args
        Positional arguments to pass to :meth:`polars.scan_csv`.
    **kwargs
        Keyword arguments to pass to :meth:`polars.scan_csv`.

    Returns
    -------
    :obj:`polars.LazyFrame`
    """

    # TODO there are forbidden variables that should not be in expanded_fpath
    # such as 'line' and 'fields' and '_fname'

    # TODO schema and schema_overrides is probably broken

    lf = _polars.scan_csv(
        expanded_fpath,
        include_file_paths="_fname",
        separator="\n",
        new_columns=["line"],
        has_header=False,
        **kwargs,
    )

    # Can filter lines before doing any further processing
    # This could be to remove lines with comments, etc.
    if filter_expr is not None:
        lf = lf.filter(filter_expr)

    if include_file_paths is not None:
        lf = lf.with_columns(_polars.col("_fname").alias(include_file_paths))

    # Separate lines into fields using `separator`
    if separator is not None:
        # Separate line into fields by separator
        lf = lf.with_columns(
            _polars.col("line").str.split(separator, literal=False).alias("fields")
        )

        if not keep_line:
            lf = lf.drop("line")

        # With many matched files, inferring the field count/dtypes directly
        # against the full glob is extremely slow (every file has to be opened
        # before a `.head()` takes effect). Instead, recurse on a single
        # representative file -- expanded_fpath[0] -- and reuse its already-cheap
        # (single-file) inference below instead of duplicating it here. Computed
        # once here since it's needed by both the field-count branch below and
        # the dtype-inference branch further down.
        infer_schema = kwargs.get("infer_schema", True)
        sample_schema = None
        if (
            isinstance(expanded_fpath, ExpandedFPath)
            and len(expanded_fpath) > 1
            and (usecols is None or infer_schema)
        ):
            sample_schema = scan_txt(
                expanded_fpath[0],
                filter_expr=filter_expr,
                separator=separator,
                new_columns=new_columns,
                has_header=has_header,
                usecols=usecols,
                **kwargs,
            ).collect_schema()

        # Set the columns to use for the fields.
        # Either specify a subset of columns to use, or use all columns
        if usecols is not None:
            fields = {}
            for col in usecols:
                fields[col] = f"field_{col}"

        else:
            if sample_schema is not None:
                n_fields = len(sample_schema) - 1  # minus '_fname'
            else:
                n_fields = (
                    lf.head(1)
                    .select(_polars.col("fields").list.len().unique())
                    .collect()
                    .item()
                )

            # Initial field names, may be renamed later from header or by `new_columns`
            fields = {i: f"field_{i}" for i in range(n_fields)}

            # n_fields came from a single sample file (see above), so a file
            # with *fewer* fields than the sample will already raise a clear
            # polars error below (list.get() on an out-of-bounds index). A
            # file with *more* fields would not -- its extra columns would
            # just be silently dropped -- so check for that explicitly if
            # requested.
            if validate_schema and sample_schema is not None:
                max_fields = (
                    lf.select(_polars.col("fields").list.len().max())
                    .collect()
                    .item()
                )
                if max_fields is not None and max_fields > n_fields:
                    msg = (
                        f"field count mismatch: schema was inferred from a "
                        f"single sample file with {n_fields} fields, but at "
                        f"least one matched file has {max_fields} fields"
                    )
                    raise ValueError(msg)

        # Add each field as a separate column
        for i, field in fields.items():
            lf = lf.with_columns(_polars.col("fields").list.get(i).alias(field))
        lf = lf.drop("fields")

        # LazyFrame does not guarantee order, so the header might not be the first row
        # This can be fixed by scan_csv with include_row_index. But this seems clunky
        if has_header:
            """
            first_row = lf.head(1).collect()
            header.to_pandas().transpose()[0].to_dict()
            lf = lf.slice(offset=1, length=None)
            header = first_row.select(_polars.col(fields)).to_dict(as_series=False)
            lf = lf.rename({field: header[field][0] for field in fields})
            """
            raise NotImplementedError

        # Apply new column names if provided
        if new_columns is not None:
            for field, new_column in zip(fields.values(), new_columns):
                lf = lf.rename({field: new_column})

        # Infer dtypes?
        if infer_schema:
            if sample_schema is not None:
                inferred_schema = {
                    name: dtype
                    for name, dtype in sample_schema.items()
                    if name != "_fname"
                }
            else:
                sample = (
                    lf.head(kwargs.get("infer_schema_length", 100))
                    .collect()
                    .write_csv()
                    .encode()
                )
                inferred_schema = _polars.read_csv(sample).schema
            lf = lf.cast(inferred_schema)

    return lf
