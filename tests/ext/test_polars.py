import re
import tarfile
from pathlib import Path

import pytest

from fpathlib.ext import polars as pl

testcases = sorted((Path(__file__).parent / "testcases").glob("*.tgz"))


@pytest.fixture
def testcase(tmp_path, request):
    fname = request.param
    with tarfile.open(fname, "r:gz") as tar:
        tar.extractall(tmp_path, filter="data")
    return tmp_path / Path(fname).stem


def _count_lines(path):
    with open(path, "rb") as f:
        return sum(1 for _ in f)


def _expected(testcase, glob_pattern, name_pattern, exclude_suffix=None):
    """
    Independently derive the expected row count and unique metadata values
    by walking the extracted testcase on disk, rather than hardcoding
    numbers tied to the current fixture contents (see TODO.txt).
    """

    regex = re.compile(name_pattern)
    total_lines = 0
    uniques = {}

    for path in testcase.glob(glob_pattern):
        if exclude_suffix and path.name.endswith(exclude_suffix):
            continue

        rel = str(path.relative_to(testcase))
        match = regex.search(rel)
        assert match, rel

        for key, value in match.groupdict().items():
            uniques.setdefault(key, set()).add(int(value))

        total_lines += _count_lines(path)

    return total_lines, {key: len(values) for key, values in uniques.items()}


@pytest.mark.parametrize("testcase", testcases, indirect=True)
def test_read_csv(testcase):
    expected_lines, expected_uniques = _expected(
        testcase,
        "tr*/output/*/job*.*.sort.log",
        r"tr(?P<trajectory>\d+)/output/(?P<condition>\d+)/job(?P<job>\d+)\.\d+\.sort\.log$",
    )

    df = pl.read_csv(
        testcase / "tr{trajectory:d}/output/{condition:d}/job{job:d}.{condition:d}.sort.log",
        has_header=False,
    )

    assert type(df) == pl.DataFrame
    assert df.select(pl.len()).item() == expected_lines
    assert (
        df.select(pl.col("trajectory").unique().len()).item()
        == expected_uniques["trajectory"]
    )
    assert (
        df.select(pl.col("condition").unique().len()).item()
        == expected_uniques["condition"]
    )
    assert df.select(pl.col("job").unique().len()).item() == expected_uniques["job"]


@pytest.mark.parametrize("testcase", testcases, indirect=True)
def test_read_txt(testcase):
    expected_lines, expected_uniques = _expected(
        testcase,
        "tr*/output/*/job*.*.sort.log",
        r"tr(?P<trajectory>\d+)/output/(?P<replica>\d+)/job(?P<job>\d+)\.\d+\.sort\.log$",
    )

    df = pl.read_txt(
        testcase / "tr{trajectory:d}/output/{replica:d}/job{job:d}.{replica:d}.sort.log",
        has_header=False,
        separator=r"\s+",
    )

    assert type(df) == pl.DataFrame
    assert df.select(pl.len()).item() == expected_lines
    assert (
        df.select(pl.col("trajectory").unique().len()).item()
        == expected_uniques["trajectory"]
    )
    assert (
        df.select(pl.col("replica").unique().len()).item()
        == expected_uniques["replica"]
    )
    assert df.select(pl.col("job").unique().len()).item() == expected_uniques["job"]


@pytest.mark.parametrize("testcase", testcases, indirect=True)
def test_scan_csv(testcase):
    expected_lines, expected_uniques = _expected(
        testcase,
        "tr*/output/*/job*.*.log",
        r"tr(?P<trajectory>\d+)/output/(?P<replica>\d+)/job(?P<job>\d+)\.\d+\.log$",
        exclude_suffix=".sort.log",
    )

    df = pl.scan_csv(
        testcase / "tr{trajectory:d}/output/{replica:d}/job{job:d}.{replica:d}.log",
        exclude_path_patterns="*.sort.log",
        has_header=False,
    )

    assert type(df) == pl.LazyFrame
    assert df.select(pl.len()).collect().item() == expected_lines
    assert (
        df.select(pl.col("trajectory").unique().len()).collect().item()
        == expected_uniques["trajectory"]
    )
    assert (
        df.select(pl.col("replica").unique().len()).collect().item()
        == expected_uniques["replica"]
    )
    assert (
        df.select(pl.col("job").unique().len()).collect().item()
        == expected_uniques["job"]
    )

    expected_lines, expected_uniques = _expected(
        testcase,
        "tr*/output/*/job*.*.sort.log",
        r"tr(?P<trajectory>\d+)/output/(?P<condition>\d+)/job(?P<job>\d+)\.\d+\.sort\.log$",
    )

    df = pl.scan_csv(
        testcase / "tr{trajectory:d}/output/{condition:d}/job{job:d}.{condition:d}.sort.log",
        has_header=False,
    )

    assert type(df) == pl.LazyFrame
    assert df.select(pl.len()).collect().item() == expected_lines
    assert (
        df.select(pl.col("trajectory").unique().len()).collect().item()
        == expected_uniques["trajectory"]
    )
    assert (
        df.select(pl.col("condition").unique().len()).collect().item()
        == expected_uniques["condition"]
    )
    assert (
        df.select(pl.col("job").unique().len()).collect().item()
        == expected_uniques["job"]
    )


@pytest.mark.parametrize("testcase", testcases, indirect=True)
def test_scan_txt(testcase):
    expected_lines, expected_uniques = _expected(
        testcase,
        "tr*/output/*/job*.*.sort.log",
        r"tr(?P<trajectory>\d+)/output/(?P<replica>\d+)/job(?P<job>\d+)\.\d+\.sort\.log$",
    )

    df = pl.scan_txt(
        testcase / "tr{trajectory:d}/output/{replica:d}/job{job:d}.{replica:d}.sort.log",
        has_header=False,
        separator=r"\s+",
    )
    assert type(df) == pl.LazyFrame
    assert df.select(pl.len()).collect().item() == expected_lines
    assert (
        df.select(pl.col("trajectory").unique().len()).collect().item()
        == expected_uniques["trajectory"]
    )
    assert (
        df.select(pl.col("replica").unique().len()).collect().item()
        == expected_uniques["replica"]
    )
    assert (
        df.select(pl.col("job").unique().len()).collect().item()
        == expected_uniques["job"]
    )
