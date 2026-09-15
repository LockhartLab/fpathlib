fpathlib
========

A Python package for adding metadata to file paths.

`fpathlib` combines file paths with the metadata encoded in their names. It
does this with an f-string-like path pattern -- `FPath` -- whose
`{variable}` fields are captured out of every matching path on disk.

```python
from fpathlib import expand_fpath

# Given files like data/tr1/output/0/job2.log, data/tr2/output/1/job0.log, ...
expanded = expand_fpath("data/tr{trajectory:d}/output/{replica:d}/job{job:d}.log")

for path in expanded:
    print(path, path.metadata)
# data/tr1/output/0/job2.log {'trajectory': 1, 'replica': 0, 'job': 2}
# data/tr2/output/1/job0.log {'trajectory': 2, 'replica': 1, 'job': 0}
```

Combine the metadata for every matched path into a single table:

```python
df = expanded.to_polars()
```

`fpathlib.ext.polars` goes a step further: it wraps `polars`'s own
`read_csv`/`scan_csv`/`read_txt`/`scan_txt` so that an expandable path
pattern is accepted directly, and the resulting DataFrame or LazyFrame comes
back with the metadata already joined in.

```python
import fpathlib.ext.polars as pl

df = pl.read_csv(
    "data/tr{trajectory:d}/output/{replica:d}/job{job:d}.log",
    has_header=False,
)
# df has columns "column_1", ..., plus "trajectory", "replica", "job"
```

Installation
------------

```shell
pip install fpathlib
```

The `fpathlib.ext.polars` extension additionally requires `polars`, which
is not installed by `fpathlib` itself:

```shell
pip install polars
```

Documentation
-------------

Full API documentation is in `docs/`; build it locally with
`scripts/docs.sh` (requires the `dev` extras: `pip install -e .[dev]`).
