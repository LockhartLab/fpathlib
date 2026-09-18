import re
import tarfile
from pathlib import Path

import pytest

import fpathlib
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


class TestIncludeFilePaths:
    def test_scan_csv_omits_fname_by_default(self, tmp_path):
        (tmp_path / "tr1").mkdir()
        (tmp_path / "tr1" / "x.csv").write_text("a,b,c\n")
        (tmp_path / "tr2").mkdir()
        (tmp_path / "tr2" / "x.csv").write_text("d,e,f\n")

        df = pl.scan_csv(
            str(tmp_path / "tr{n:d}/x.csv"), has_header=False
        ).collect()
        assert "fname" not in df.columns

    def test_scan_csv_include_file_paths(self, tmp_path):
        (tmp_path / "tr1").mkdir()
        (tmp_path / "tr1" / "x.csv").write_text("a,b,c\n")
        (tmp_path / "tr2").mkdir()
        (tmp_path / "tr2" / "x.csv").write_text("d,e,f\n")

        df = pl.scan_csv(
            str(tmp_path / "tr{n:d}/x.csv"),
            has_header=False,
            include_file_paths="source_file",
        ).collect()
        assert "source_file" in df.columns
        assert "fname" not in df.columns
        assert set(df["source_file"]) == {
            str(tmp_path / "tr1" / "x.csv"),
            str(tmp_path / "tr2" / "x.csv"),
        }

    def test_scan_parquet_include_file_paths(self, tmp_path):
        (tmp_path / "tr1").mkdir()
        pl.DataFrame({"x": [1]}).write_parquet(tmp_path / "tr1" / "x.parquet")
        (tmp_path / "tr2").mkdir()
        pl.DataFrame({"x": [2]}).write_parquet(tmp_path / "tr2" / "x.parquet")

        df = pl.scan_parquet(str(tmp_path / "tr{n:d}/x.parquet")).collect()
        assert "fname" not in df.columns

        df2 = pl.scan_parquet(
            str(tmp_path / "tr{n:d}/x.parquet"), include_file_paths="source_file"
        ).collect()
        assert "source_file" in df2.columns

    def test_scan_txt_include_file_paths(self, tmp_path):
        (tmp_path / "tr1").mkdir()
        (tmp_path / "tr1" / "x.log").write_text("a b c\n")
        (tmp_path / "tr2").mkdir()
        (tmp_path / "tr2" / "x.log").write_text("d e f\n")

        df = pl.scan_txt(
            str(tmp_path / "tr{n:d}/x.log"), separator=" ", has_header=False
        ).collect()
        assert "fname" not in df.columns

        df2 = pl.scan_txt(
            str(tmp_path / "tr{n:d}/x.log"),
            separator=" ",
            has_header=False,
            include_file_paths="source_file",
        ).collect()
        assert "source_file" in df2.columns

    def test_include_file_paths_named_fname_is_not_lost(self, tmp_path):
        # include_file_paths="fname" used to silently vanish: aliasing
        # "fname" -> "fname" was a no-op, so join_metadata's unconditional
        # drop("fname") deleted the caller's only copy. The internal join
        # key is now reserved as "_fname" specifically so this can't happen.
        (tmp_path / "tr1").mkdir()
        (tmp_path / "tr1" / "x.log").write_text("a b c\n")
        (tmp_path / "tr2").mkdir()
        (tmp_path / "tr2" / "x.log").write_text("d e f\n")

        df = pl.scan_txt(
            str(tmp_path / "tr{n:d}/x.log"),
            separator=" ",
            has_header=False,
            include_file_paths="fname",
        ).collect()

        assert "fname" in df.columns
        assert "_fname" not in df.columns
        assert set(df["fname"]) == {
            str(tmp_path / "tr1" / "x.log"),
            str(tmp_path / "tr2" / "x.log"),
        }

    def test_fname_not_leaked_for_non_expandable_input(self, tmp_path):
        # join_metadata (which normally drops the internal "_fname") never
        # runs for non-expandable input (a literal path or plain glob --
        # no metadata to join), so scan_csv/scan_parquet/scan_txt have to
        # drop it themselves in that case instead.
        (tmp_path / "x.csv").write_text("a,b,c\n")
        (tmp_path / "x.log").write_text("a b c\n")

        df_csv = pl.scan_csv(str(tmp_path / "x.csv"), has_header=False).collect()
        assert "_fname" not in df_csv.columns

        df_txt = pl.scan_txt(
            str(tmp_path / "x.log"), separator=" ", has_header=False
        ).collect()
        assert "_fname" not in df_txt.columns

    def test_include_file_paths_works_for_non_expandable_input(self, tmp_path):
        (tmp_path / "x.csv").write_text("a,b,c\n")

        df = pl.scan_csv(
            str(tmp_path / "x.csv"), has_header=False, include_file_paths="source"
        ).collect()

        assert "source" in df.columns
        assert "_fname" not in df.columns
        assert df["source"].item() == str(tmp_path / "x.csv")


class TestLineFilterAndIncludeLine:
    def _write(self, tmp_path, name, text):
        (tmp_path / name).write_text(text)

    def test_line_filter(self, tmp_path):
        self._write(tmp_path, "tr1.log", "# comment\na b c\n")
        self._write(tmp_path, "tr2.log", "# comment\nd e f\n")

        df = pl.scan_txt(
            str(tmp_path / "tr{n:d}.log"),
            separator=" ",
            has_header=False,
            line_filter=lambda line: line.str.starts_with("#").not_(),
        ).collect()

        assert df.height == 2
        assert set(df["field_0"]) == {"a", "d"}

    def test_line_filter_receives_line_expr(self, tmp_path):
        # confirms fpathlib calls line_filter(pl.col("_line")) itself,
        # rather than the caller needing to reference any column by name
        self._write(tmp_path, "tr1.log", "keep\ndrop\n")

        calls = []

        def predicate(line):
            calls.append(line)
            return line != "drop"

        df = pl.scan_txt(
            str(tmp_path / "tr1.log"), has_header=False, line_filter=predicate
        ).collect()

        assert len(calls) == 1
        assert isinstance(calls[0], pl.Expr)
        assert list(df["line"]) == ["keep"]

    def test_include_line_with_separator(self, tmp_path):
        self._write(tmp_path, "tr1.log", "a b c\n")

        df = pl.scan_txt(
            str(tmp_path / "tr1.log"),
            separator=" ",
            has_header=False,
            include_line="raw",
        ).collect()

        assert "raw" in df.columns
        assert "_line" not in df.columns
        assert df["raw"].item() == "a b c"

    def test_no_separator_no_include_line_defaults_to_line(self, tmp_path):
        self._write(tmp_path, "tr1.log", "hello\n")

        df = pl.scan_txt(str(tmp_path / "tr1.log"), has_header=False).collect()

        assert "line" in df.columns
        assert "_line" not in df.columns
        assert df["line"].item() == "hello"

    def test_no_separator_include_line_custom_name(self, tmp_path):
        self._write(tmp_path, "tr1.log", "hello\n")

        df = pl.scan_txt(
            str(tmp_path / "tr1.log"), has_header=False, include_line="raw"
        ).collect()

        assert "raw" in df.columns
        assert "line" not in df.columns
        assert "_line" not in df.columns
        assert df["raw"].item() == "hello"

    def test_include_line_and_include_file_paths_together(self, tmp_path):
        # Uses an expandable pattern (not a plain literal path) so
        # join_metadata actually runs and drops "_fname" -- see the
        # separate, pre-existing "_fname leaks for non-expandable input"
        # issue this surfaced, which is unrelated to include_line/
        # line_filter and not fixed here.
        (tmp_path / "tr1").mkdir()
        self._write(tmp_path / "tr1", "x.log", "a b\n")

        df = pl.scan_txt(
            str(tmp_path / "tr{n:d}/x.log"),
            separator=" ",
            has_header=False,
            include_line="raw",
            include_file_paths="source",
        ).collect()

        assert set(df.columns) >= {"raw", "source", "field_0", "field_1", "n"}
        assert "_line" not in df.columns
        assert "_fname" not in df.columns


class TestExpandedFPathToPolars:
    def test_none_metadata_becomes_empty_columns(self, tmp_path):
        # expand_fpath(..., require_metadata=False) on a pattern with no
        # named captures leaves metadata=None for every match -- to_polars()
        # used to crash on `**None` there; it should just produce a frame
        # with no metadata columns instead.
        (tmp_path / "a.log").write_text("data\n")
        (tmp_path / "b.log").write_text("data\n")

        ex = fpathlib.expand_fpath(str(tmp_path / "*.log"), require_metadata=False)
        df = ex.to_polars()

        assert df.columns == ["fname"]
        assert df.height == 2

    def test_mixed_none_and_real_metadata(self, tmp_path):
        (tmp_path / "trX").mkdir()
        (tmp_path / "trX" / "jobY.log").write_text("bad\n")
        (tmp_path / "tr1").mkdir()
        (tmp_path / "tr1" / "job1.log").write_text("good\n")

        ex = fpathlib.expand_fpath(
            str(tmp_path / "tr{trajectory:d}/job{job:d}.log"),
            require_metadata=False,
        )
        df = ex.to_polars()

        assert set(df.columns) == {"fname", "trajectory", "job"}
        assert df["trajectory"].null_count() == 1


class TestScanTxtValidateSchema:
    def _write(self, tmp_path, name, line):
        (tmp_path / name).write_text(line + "\n")

    def test_default_raises_on_extra_fields(self, tmp_path):
        # sample file (tr1) has 3 fields; tr3 has 4 -- without validation
        # the extra field would be silently dropped instead of erroring.
        self._write(tmp_path, "tr1.log", "a b c")
        self._write(tmp_path, "tr2.log", "a b c")
        self._write(tmp_path, "tr3.log", "p q r s")

        with pytest.raises(ValueError, match="field count mismatch"):
            pl.scan_txt(
                str(tmp_path / "tr{n:d}.log"),
                separator=" ",
                has_header=False,
            ).collect()

    def test_validate_schema_false_silently_truncates(self, tmp_path):
        self._write(tmp_path, "tr1.log", "a b c")
        self._write(tmp_path, "tr2.log", "a b c")
        self._write(tmp_path, "tr3.log", "p q r s")

        df = pl.scan_txt(
            str(tmp_path / "tr{n:d}.log"),
            separator=" ",
            has_header=False,
            validate_schema=False,
        ).collect()

        assert set(df.columns) == {"field_0", "field_1", "field_2", "n"}
        row = df.filter(pl.col("n") == 3)
        assert row["field_2"].item() == "r"  # "s" silently dropped

    def test_consistent_fields_do_not_raise(self, tmp_path):
        self._write(tmp_path, "tr1.log", "a b c")
        self._write(tmp_path, "tr2.log", "d e f")

        df = pl.scan_txt(
            str(tmp_path / "tr{n:d}.log"),
            separator=" ",
            has_header=False,
        ).collect()

        assert df.height == 2

    def test_fewer_fields_raises_regardless_of_validate_schema(self, tmp_path):
        # A file with fewer fields than the sample already fails via
        # polars' own out-of-bounds list access -- confirm that still
        # happens with validate_schema explicitly disabled too.
        self._write(tmp_path, "tr1.log", "a b c")
        self._write(tmp_path, "tr2.log", "a b")

        with pytest.raises(pl.exceptions.ComputeError):
            pl.scan_txt(
                str(tmp_path / "tr{n:d}.log"),
                separator=" ",
                has_header=False,
                validate_schema=False,
            ).collect()

    def test_usecols_bypasses_validate_schema(self, tmp_path):
        # Known limitation, not (yet) a bug: the validate_schema check only
        # runs when the field set comes from schema inference (usecols is
        # None). When usecols is given, n_fields/fields are built directly
        # from it instead, so the check is structurally unreachable -- a
        # real mismatch goes uncaught even with validate_schema=True.
        self._write(tmp_path, "tr1.log", "a b c")
        self._write(tmp_path, "tr2.log", "a b c")
        self._write(tmp_path, "tr3.log", "p q r s")

        df = pl.scan_txt(
            str(tmp_path / "tr{n:d}.log"),
            separator=" ",
            has_header=False,
            usecols=[0, 1],
            validate_schema=True,
        ).collect()

        assert set(df.columns) == {"field_0", "field_1", "n"}
        assert df.height == 3
