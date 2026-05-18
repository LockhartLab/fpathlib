import numpy as np
from fpathlib.ext import polars as pl


def test_scan_csv():
    df = pl.scan_csv(
        "testcase1/tr{trajectory:d}/output/{replica:d}/job{job:d}.{replica:d}.log",
        exclude_path_patterns="*.sort.log",
        has_header=False,
    )

    assert type(df) == pl.LazyFrame
    assert df.select(pl.len()).collect().item() == 35167482
    assert df.select(pl.col("trajectory").unique().len()).collect().item() == 3
    assert df.select(pl.col("replica").unique().len()).collect().item() == 3
    assert df.select(pl.col("job").unique().len()).collect().item() == 25

    df = pl.scan_csv(
        "testcase1/tr{trajectory:d}/output/{condition:d}/job{job:d}.{condition:d}.sort.log",
        has_header=False,
    )

    assert type(df) == pl.LazyFrame
    assert df.select(pl.len()).collect().item() == 150000
    assert df.select(pl.col("trajectory").unique().len()).collect().item() == 3
    assert df.select(pl.col("condition").unique().len()).collect().item() == 1
    assert df.select(pl.col("job").unique().len()).collect().item() == 25

def test_scan_txt():
    df = pl.scan_txt(
        "testcase1/tr{trajectory:d}/output/{replica:d}/job{job:d}.{replica:d}.sort.log",
        has_header=False,
        separator=r"\s+",
    )

    assert type(df) == pl.LazyFrame
    assert df.select(pl.len()).collect().item() == 150000
    assert df.select(pl.col("trajectory").unique().len()).collect().item() == 3
    assert df.select(pl.col("replica").unique().len()).collect().item() == 1
    assert df.select(pl.col("job").unique().len()).collect().item() == 25
