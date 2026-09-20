from functools import wraps
import polars as _polars
from fpathlib import expand_arg, is_expandable, ExpandedFPath


def __getattr__(name):
    # Delegates any attribute this module doesn't define itself to the real
    # polars module, so `fpathlib.ext.polars` remains a drop-in replacement for
    # `import polars` (pl.DataFrame, pl.col, pl.List, etc. all still resolve).
    # Unlike `from polars import *`, this only kicks in for names Python didn't
    # already find defined here, so it can't silently shadow builtins like
    # `list` or `len` for this module's own implementation code.
    return getattr(_polars, name)


def join_metadata(f):
    """
    Wraps a scan_csv-shaped function `f(source, *args, **kwargs) ->
    LazyFrame` with metadata-joining and "_fname" cleanup, applied
    automatically to whatever `f` returns. Must be applied *inside*
    @expand_arg (i.e. listed closer to `def`), so `source`
    here is always the already-expanded value, not the raw caller-supplied
    pattern:

        @expand_arg
        @join_metadata
        def scan_csv(source, ...): ...

    Guards against getting that order backwards: if `source` still looks
    like an unexpanded {} pattern at this point, expansion can only have
    failed to run (wrong decorator order, or this decorator used without
    @expand_arg at all) -- raise immediately rather than
    silently joining no metadata.
    """

    @wraps(f)
    def wrapper(source, *args, **kwargs):
        lf = f(source, *args, **kwargs)
        if not isinstance(source, ExpandedFPath) and is_expandable(source):
            msg = (
                f"join_metadata received an unexpanded pattern "
                f"{source!r} -- @expand_arg must be the outer "
                "decorator, applied above (not below) @join_metadata"
            )
            raise RuntimeError(msg)

        # Join captured {} metadata into `lf`, keyed on the reserved
        # "_fname" column scan_csv/scan_parquet always create, then always
        # drop "_fname" itself. Callers that want to keep the file path
        # under a different name must alias it to that name *before* this
        # runs (inside `f`'s own body) -- by the time this returns,
        # "_fname" is gone either way.
        if isinstance(source, ExpandedFPath):
            # "fname" is ExpandedFPath.to_polars()'s normal, public column
            # name; rename it to the same reserved "_fname" scan_csv/
            # scan_parquet use, so the join key can never collide with an
            # `include_file_paths` name a caller chose (including "fname"
            # itself).
            metadata = source.to_polars(lazy=isinstance(lf, _polars.LazyFrame))
            metadata = metadata.rename({"fname": "_fname"})
            lf = lf.join(metadata, on="_fname")

        return lf.drop("_fname")

    return wrapper


def read_csv(fpath, *args, **kwargs):
    """
    Read the paths in the collection as CSV files, and return a
    :obj:`polars.DataFrame` along with the metadata captured from the path
    variables.

    Parameters
    ----------
    fpath : :obj:`str` or :obj:`fpathlib.ExpandedFPath`
        An f-string path, or an already-expanded one.
    *args
        Positional arguments to pass to :meth:`polars.read_csv`.
    **kwargs
        Keyword arguments to pass to :meth:`polars.read_csv`.

    Returns
    -------
    :obj:`polars.DataFrame`
    """

    return scan_csv(fpath, *args, **kwargs).collect()


def read_txt(
    fpath,
    line_filter=None,
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
    fpath : :obj:`str` or :obj:`fpathlib.ExpandedFPath`
        An f-string path, or an already-expanded one.
    line_filter : :obj:`callable`, optional
        A function that takes a :obj:`polars.Expr` for the line's text and
        returns a boolean :obj:`polars.Expr`, used to filter lines before
        splitting by the separator. E.g.
        `lambda line: line.str.starts_with("#").not_()`.
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

    return scan_txt(
        fpath,
        line_filter=line_filter,
        separator=separator,
        new_columns=new_columns,
        has_header=has_header,
        *args,
        **kwargs,
    ).collect()


@expand_arg
@join_metadata
def scan_csv(source, include_file_paths=None, *args, **kwargs):
    """
    Scan the paths in the collection as CSV files, and return a
    :obj:`polars.LazyFrame` along with the metadata captured from the path
    variables.

    Parameters
    ----------
    source : :obj:`fpathlib.ExpandedFPath`, or any type accepted by :obj:`polars.scan_csv`
        An expanded f-string path, or a plain path/glob.
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
        source,
        include_file_paths="_fname",
        *args,
        **kwargs,
    )
    if include_file_paths is not None:
        lf = lf.with_columns(_polars.col("_fname").alias(include_file_paths))
    return lf


@expand_arg
@join_metadata
def scan_parquet(source, include_file_paths=None, *args, **kwargs):
    """
    Scan the paths in the collection as a parquet file, and return a
    :obj:`polars.LazyFrame` along with the metadata captured from the path
    variables.

    Parameters
    ----------
    source : :obj:`fpathlib.ExpandedFPath`, or any type accepted by :obj:`polars.scan_parquet`
        An expanded f-string path, or a plain path/glob.
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
        source,
        include_file_paths="_fname",
        *args,
        **kwargs,
    )
    if include_file_paths is not None:
        lf = lf.with_columns(_polars.col("_fname").alias(include_file_paths))
    return lf


@expand_arg
def scan_txt(
    source,
    line_filter=None,
    separator=None,
    new_columns=None,
    has_header=False,
    include_line=None,
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
    source : :obj:`fpathlib.ExpandedFPath`, or any type accepted by :obj:`polars.scan_csv`
        An expanded f-string path, or a plain path/glob.
    line_filter : :obj:`callable`, optional
        A function that takes a :obj:`polars.Expr` for the line's text and
        returns a boolean :obj:`polars.Expr`, used to filter lines before
        splitting by the separator. E.g.
        `lambda line: line.str.starts_with("#").not_()`.
    separator : :obj:`str`, optional
        Deliminatorg to split each line into fields.
    new_columns : :obj:`list`[:obj:`str`], optional
        List of new column names to rename the fields after splitting by the separator.
        If not provided, the fields are named as `field_0`, `field_1`, etc.
    has_header : :obj:`bool`
        Whether the text files have a header line that should be skipped. The header
        must have the same delimiter as the separator provided in `separator`.
        (Default: False)
    include_line : :obj:`str`, optional
        Name to give a column of each row's original, unsplit line text in
        the output. Without this, it isn't kept in the result. (Default: None)
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

    # TODO there are forbidden variables that should not be in source
    # such as '_line' and 'fields' and '_fname'

    # TODO schema and schema_overrides is probably broken

    # Delegates to scan_csv (rather than calling _polars.scan_csv and
    # doing the metadata-join/include_file_paths handling directly) so
    # that handling -- including the recursive single-file sample call
    # below, since source[0] is a plain Path, not an ExpandedFPath --
    # isn't duplicated here. scan_csv's own @expand_arg is a
    # no-op on `source` at this point: it's already been resolved by
    # scan_txt's decorator, so scan_csv just sees an ExpandedFPath or an
    # already-unexpandable literal/glob, either way with nothing left to
    # expand.
    lf = scan_csv(
        source,
        include_file_paths=include_file_paths,
        separator="\n",
        new_columns=["_line"],
        has_header=False,
        **kwargs,
    )

    # Can filter lines before doing any further processing
    # This could be to remove lines with comments, etc.
    if line_filter is not None:
        lf = lf.filter(line_filter(_polars.col("_line")))

    if include_line is not None:
        lf = lf.with_columns(_polars.col("_line").alias(include_line))

    # Separate lines into fields using `separator`
    if separator is not None:
        # Separate line into fields by separator
        lf = lf.with_columns(
            _polars.col("_line").str.split(separator, literal=False).alias("fields")
        )
        lf = lf.drop("_line")

        # With many matched files, inferring the field count/dtypes directly
        # against the full glob is extremely slow (every file has to be opened
        # before a `.head()` takes effect). Instead, recurse on a single
        # representative file -- source[0] -- and reuse its already-cheap
        # (single-file) inference below instead of duplicating it here. Computed
        # once here since it's needed by both the field-count branch below and
        # the dtype-inference branch further down.
        infer_schema = kwargs.get("infer_schema", True)
        sample_schema = None
        if (
            isinstance(source, ExpandedFPath)
            and len(source) > 1
            and (usecols is None or infer_schema)
        ):
            sample_schema = scan_txt(
                source[0],
                line_filter=line_filter,
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
                # The recursive sample call above is always non-expandable
                # (source[0] is a plain Path), so it already drops "_fname"
                # itself -- no adjustment needed here.
                n_fields = len(sample_schema)
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
                # The recursive sample call already drops "_fname" (see
                # above), so no need to filter it back out here.
                inferred_schema = dict(sample_schema.items())
            else:
                sample = (
                    lf.head(kwargs.get("infer_schema_length", 100))
                    .collect()
                    .write_csv()
                    .encode()
                )
                inferred_schema = _polars.read_csv(sample).schema
            lf = lf.cast(inferred_schema)

    elif include_line is None:
        # No separator means each row is just the raw line -- that's the
        # whole point of this mode, so it has to stay visible somehow.
        # Fall back to the traditional "line" name rather than leaking the
        # internal "_line" name, since the caller didn't ask for a specific
        # one via include_line.
        lf = lf.rename({"_line": "line"})
    else:
        # include_line was given, so the alias was already created above
        # (before this if/elif/else) -- drop the internal "_line" itself so
        # it doesn't also leak into the output alongside it.
        lf = lf.drop("_line")

    return lf
