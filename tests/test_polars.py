from glob import glob
import numpy as np
from pathlib import Path
import pytest
import tarfile

from fpathlib.ext import polars as pl

testcases = sorted(glob("testcases/*.tgz"))

@pytest.fixture
def testcase(tmp_path, request):
    fname = request.param
    with tarfile.open(fname, "r:gz") as tar:
        tar.extractall(tmp_path, filter="data")
    return tmp_path / Path(fname).stem

@pytest.mark.parametrize("testcase", testcases, indirect=True)
def test_read_csv(testcase):
    df = pl.read_csv(
        testcase / "tr{trajectory:d}/output/{condition:d}/job{job:d}.{condition:d}.sort.log",
        has_header=False,
    )
    
    assert type(df) == pl.DataFrame
    assert df.select(pl.len()).item() == 12000
    assert df.select(pl.col("trajectory").unique().len()).item() == 2
    assert df.select(pl.col("condition").unique().len()).item() == 1
    assert df.select(pl.col("job").unique().len()).item() == 3

@pytest.mark.parametrize("testcase", testcases, indirect=True)
def test_read_txt(testcase):
    df = pl.read_txt(
        testcase / "tr{trajectory:d}/output/{replica:d}/job{job:d}.{replica:d}.sort.log",
        has_header=False,
        separator=r"\s+",
    )

    assert type(df) == pl.DataFrame
    assert df.select(pl.len()).item() == 12000
    assert df.select(pl.col("trajectory").unique().len()).item() == 2
    assert df.select(pl.col("replica").unique().len()).item() == 1
    assert df.select(pl.col("job").unique().len()).item() == 3

@pytest.mark.parametrize("testcase", testcases, indirect=True) 
def test_scan_csv(testcase):
    df = pl.scan_csv(
        testcase / "tr{trajectory:d}/output/{replica:d}/job{job:d}.{replica:d}.log",
        exclude_path_patterns="*.sort.log",
        has_header=False,
    )
    
    assert type(df) == pl.LazyFrame
    assert df.select(pl.len()).collect().item() == 2813646
    assert df.select(pl.col("trajectory").unique().len()).collect().item() == 2
    assert df.select(pl.col("replica").unique().len()).collect().item() == 3
    assert df.select(pl.col("job").unique().len()).collect().item() == 3
    
    df = pl.scan_csv(
        testcase / "tr{trajectory:d}/output/{condition:d}/job{job:d}.{condition:d}.sort.log",
        has_header=False,
    )
    
    assert type(df) == pl.LazyFrame
    assert df.select(pl.len()).collect().item() == 12000
    assert df.select(pl.col("trajectory").unique().len()).collect().item() == 2
    assert df.select(pl.col("condition").unique().len()).collect().item() == 1
    assert df.select(pl.col("job").unique().len()).collect().item() == 3

@pytest.mark.parametrize("testcase", testcases, indirect=True) 
def test_scan_txt(testcase):
    df = pl.scan_txt(
        testcase / "tr{trajectory:d}/output/{replica:d}/job{job:d}.{replica:d}.sort.log",
        has_header=False,
        separator=r"\s+",
    )

    assert type(df) == pl.LazyFrame
    assert df.select(pl.len()).collect().item() == 12000
    assert df.select(pl.col("trajectory").unique().len()).collect().item() == 2
    assert df.select(pl.col("replica").unique().len()).collect().item() == 1
    assert df.select(pl.col("job").unique().len()).collect().item() == 3
