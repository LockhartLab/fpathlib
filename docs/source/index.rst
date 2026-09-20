fpathlib
========

fpathlib combines file paths with the metadata encoded in their names.

The core idea is an f-string-like path pattern -- an :class:`~fpathlib.FPath`
-- whose ``{variable}`` fields are captured out of every matching path on
disk, producing an :class:`~fpathlib.ExpandedFPath`: a collection of
:class:`~fpathlib.Path` objects, each carrying the metadata parsed from its
own filename.

.. code-block:: python

    from fpathlib import expand

    # Given files like data/tr1/output/0/job2.log, data/tr2/output/1/job0.log, ...
    expanded = expand("data/tr{trajectory:d}/output/{replica:d}/job{job:d}.log")

    for path in expanded:
        print(path, path.metadata)
    # data/tr1/output/0/job2.log {'trajectory': 1, 'replica': 0, 'job': 2}
    # data/tr2/output/1/job0.log {'trajectory': 2, 'replica': 1, 'job': 0}

Combine the metadata for every matched path into a single table with
:meth:`~fpathlib.ExpandedFPath.to_polars`:

.. code-block:: python

    df = expanded.to_polars()

:mod:`fpathlib.ext.polars` goes a step further: it wraps ``polars``'s own
``read_csv``/``scan_csv``/``read_txt``/``scan_txt`` so that an expandable
path pattern is accepted directly, and the resulting DataFrame or LazyFrame
comes back with the metadata already joined in.

.. code-block:: python

    import fpathlib.ext.polars as pl

    df = pl.read_csv(
        "data/tr{trajectory:d}/output/{replica:d}/job{job:d}.log",
        has_header=False,
    )
    # df has columns "column_1", ..., plus "trajectory", "replica", "job"

Installation
------------

.. code-block:: shell

    pip install fpathlib

The ``fpathlib.ext.polars`` extension additionally requires ``polars``,
which is not installed by :mod:`fpathlib` itself:

.. code-block:: shell

    pip install polars

API Reference
-------------

.. toctree::
   :maxdepth: 2

   api
