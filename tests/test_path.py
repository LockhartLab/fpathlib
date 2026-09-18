import pathlib

import pytest

import inspect

from fpathlib import (
    Path,
    FPath,
    ExpandedFPath,
    expand_fpath,
    iexpand_fpath,
    expand_fpath_decorator,
    is_expandable,
)


@pytest.fixture
def tree(tmp_path):
    for trajectory in (1, 2):
        for job in (1, 2):
            d = tmp_path / f"tr{trajectory}"
            d.mkdir(exist_ok=True)
            (d / f"job{job}.log").write_text("data\n")
    return tmp_path


class TestPath:
    def test_is_pathlib_path(self, tmp_path):
        p = Path(tmp_path / "foo.txt")
        assert isinstance(p, pathlib.Path)

    def test_metadata_defaults_to_none(self, tmp_path):
        p = Path(tmp_path / "foo.txt")
        assert p.metadata is None

    def test_metadata_is_stored(self, tmp_path):
        p = Path(tmp_path / "foo.txt", metadata={"a": 1})
        assert p.metadata == {"a": 1}

    def test_match_single_pattern(self):
        p = Path("dir/foo.txt")
        assert list(p.match("*.txt")) == [True]
        assert list(p.match("*.csv")) == [False]

    def test_match_multiple_patterns(self):
        p = Path("dir/foo.txt")
        assert list(p.match(["*.txt", "dir/*"])) == [True, True]

    def test_match_all_true(self):
        p = Path("dir/foo.txt")
        assert p.match_all(["*.txt", "dir/*"]) is True

    def test_match_all_false(self):
        p = Path("dir/foo.txt")
        assert p.match_all(["*.txt", "*.csv"]) is False

    def test_match_any_true(self):
        p = Path("dir/foo.txt")
        assert p.match_any(["*.csv", "*.txt"]) is True

    def test_match_any_false(self):
        p = Path("dir/foo.txt")
        assert p.match_any(["*.csv", "*.log"]) is False


class TestFPath:
    def test_repr(self):
        assert repr(FPath("{a}/b")) == "FPath('{a}/b')"

    def test_expand_finds_matches_and_metadata(self, tree):
        fpath = FPath(str(tree / "tr{trajectory:d}/job{job:d}.log"))
        expanded = fpath.expand()

        assert isinstance(expanded, ExpandedFPath)
        assert len(expanded) == 4

        metas = sorted(
            expanded.metadata.values(), key=lambda m: (m["trajectory"], m["job"])
        )
        assert metas == [
            {"trajectory": 1, "job": 1},
            {"trajectory": 1, "job": 2},
            {"trajectory": 2, "job": 1},
            {"trajectory": 2, "job": 2},
        ]

    def test_expand_exclude_path_patterns(self, tree):
        fpath = FPath(str(tree / "tr{trajectory:d}/job{job:d}.log"))
        expanded = fpath.expand(exclude_path_patterns="*job2.log")

        assert len(expanded) == 2
        assert all(p.metadata["job"] == 1 for p in expanded)

    def test_expand_require_metadata_raises(self, tree):
        (tree / "trX").mkdir()
        (tree / "trX" / "jobY.log").write_text("bad\n")

        fpath = FPath(str(tree / "tr{trajectory:d}/job{job:d}.log"))
        with pytest.raises(AttributeError):
            fpath.expand()

    def test_expand_require_metadata_false_keeps_unmatched(self, tree):
        (tree / "trX").mkdir()
        (tree / "trX" / "jobY.log").write_text("bad\n")

        fpath = FPath(str(tree / "tr{trajectory:d}/job{job:d}.log"))
        expanded = fpath.expand(require_metadata=False)

        assert len(expanded) == 5
        assert sum(p.metadata is None for p in expanded) == 1

    def test_expand_no_matches_raises_by_default(self, tmp_path):
        fpath = FPath(str(tmp_path / "nope{x:d}.log"))
        with pytest.raises(IOError):
            fpath.expand()

    def test_expand_no_matches_warns(self, tmp_path):
        fpath = FPath(str(tmp_path / "nope{x:d}.log"))
        with pytest.warns(UserWarning):
            expanded = fpath.expand(errors="warn")
        assert len(expanded) == 0

    def test_expand_no_matches_ignore(self, tmp_path):
        fpath = FPath(str(tmp_path / "nope{x:d}.log"))
        expanded = fpath.expand(errors="ignore")
        assert len(expanded) == 0

    def test_expand_invalid_errors_value(self, tmp_path):
        fpath = FPath(str(tmp_path / "nope{x:d}.log"))
        with pytest.raises(ValueError):
            fpath.expand(errors="bogus")

    def test_expand_rejects_wildcard_mixed_with_capture(self, tree):
        # "*" outside a {} capture is glob syntax to glob() but a literal
        # character to `parse` -- mixing them is not supported, and should
        # fail clearly rather than silently returning metadata=None or a
        # confusing "metadata not found" error.
        fpath = FPath(str(tree / "tr{trajectory:d}/*"))
        with pytest.raises(ValueError, match=r"\*"):
            fpath.expand()

    def test_expand_rejects_qmark_mixed_with_capture(self, tree):
        fpath = FPath(str(tree / "tr{trajectory:d}/job?.log"))
        with pytest.raises(ValueError, match=r"\?"):
            fpath.expand()

    def test_expand_rejects_bracket_mixed_with_capture(self, tree):
        fpath = FPath(str(tree / "tr{trajectory:d}/job[12].log"))
        with pytest.raises(ValueError, match=r"\["):
            fpath.expand()

    def test_expand_allows_wildcard_with_no_capture(self, tree):
        # A plain glob (no {} at all) is a separate, unaffected case --
        # metadata=None is expected there, not an error.
        fpath = FPath(str(tree / "tr1/*.log"))
        expanded = fpath.expand(require_metadata=False)
        assert len(expanded) == 2
        assert all(p.metadata is None for p in expanded)


class TestFPathIexpand:
    def test_returns_a_generator(self, tree):
        fpath = FPath(str(tree / "tr{trajectory:d}/job{job:d}.log"))
        result = fpath.iexpand()
        assert inspect.isgenerator(result)

    def test_yields_same_paths_and_metadata_as_expand(self, tree):
        fpath = FPath(str(tree / "tr{trajectory:d}/job{job:d}.log"))

        expanded = fpath.expand()
        iexpanded = list(fpath.iexpand())

        assert len(iexpanded) == len(expanded)
        assert {str(p) for p in iexpanded} == {str(p) for p in expanded}
        assert {str(k): v for k, v in expanded.metadata.items()} == {
            str(p): p.metadata for p in iexpanded
        }

    def test_expand_is_built_on_iexpand(self, tree):
        # expand() should just be list(iexpand()) wrapped in ExpandedFPath --
        # confirm it actually delegates rather than duplicating the walk.
        fpath = FPath(str(tree / "tr{trajectory:d}/job{job:d}.log"))
        calls = []
        real_iexpand = FPath.iexpand

        def spy(self, *args, **kwargs):
            calls.append((args, kwargs))
            return real_iexpand(self, *args, **kwargs)

        FPath.iexpand = spy
        try:
            fpath.expand()
        finally:
            FPath.iexpand = real_iexpand

        assert len(calls) == 1

    def test_exclude_path_patterns(self, tree):
        fpath = FPath(str(tree / "tr{trajectory:d}/job{job:d}.log"))
        result = list(fpath.iexpand(exclude_path_patterns="*job2.log"))
        assert len(result) == 2
        assert all(p.metadata["job"] == 1 for p in result)

    def test_require_metadata_raises_mid_iteration(self, tree):
        (tree / "trX").mkdir()
        (tree / "trX" / "jobY.log").write_text("bad\n")

        fpath = FPath(str(tree / "tr{trajectory:d}/job{job:d}.log"))
        with pytest.raises(AttributeError):
            list(fpath.iexpand())

    def test_require_metadata_false_keeps_unmatched(self, tree):
        (tree / "trX").mkdir()
        (tree / "trX" / "jobY.log").write_text("bad\n")

        fpath = FPath(str(tree / "tr{trajectory:d}/job{job:d}.log"))
        result = list(fpath.iexpand(require_metadata=False))
        assert len(result) == 5
        assert sum(p.metadata is None for p in result) == 1

    def test_no_matches_raises_by_default(self, tmp_path):
        fpath = FPath(str(tmp_path / "nope{x:d}.log"))
        with pytest.raises(IOError):
            list(fpath.iexpand())

    def test_no_matches_warns(self, tmp_path):
        fpath = FPath(str(tmp_path / "nope{x:d}.log"))
        with pytest.warns(UserWarning):
            result = list(fpath.iexpand(errors="warn"))
        assert result == []

    def test_no_matches_ignore(self, tmp_path):
        fpath = FPath(str(tmp_path / "nope{x:d}.log"))
        result = list(fpath.iexpand(errors="ignore"))
        assert result == []

    def test_invalid_errors_value_raises_on_iteration(self, tmp_path):
        # Like any generator function, validation happens lazily on first
        # iteration, not when iexpand() is merely called.
        fpath = FPath(str(tmp_path / "nope{x:d}.log"))
        gen = fpath.iexpand(errors="bogus")
        with pytest.raises(ValueError):
            next(gen)

    def test_wildcard_mixed_with_capture_raises_on_iteration(self, tree):
        fpath = FPath(str(tree / "tr{trajectory:d}/*"))
        gen = fpath.iexpand()
        with pytest.raises(ValueError, match=r"\*"):
            next(gen)


class TestIexpandFpath:
    def test_returns_a_generator(self, tree):
        result = iexpand_fpath(str(tree / "tr{trajectory:d}/job{job:d}.log"))
        assert inspect.isgenerator(result)

    def test_yields_expected_paths(self, tree):
        result = list(iexpand_fpath(str(tree / "tr{trajectory:d}/job{job:d}.log")))
        assert len(result) == 4
        assert all(isinstance(p.metadata, dict) for p in result)


class TestExpandedFPath:
    def test_duplicate_paths_raise(self):
        p = Path("foo.txt", metadata={})
        with pytest.raises(AttributeError):
            ExpandedFPath(paths=[p, p], fpath=FPath("foo.txt"))

    def test_len_and_getitem(self, tree):
        expanded = expand_fpath(str(tree / "tr{trajectory:d}/job{job:d}.log"))
        assert len(expanded) == 4
        assert expanded[0] in list(expanded)

    def test_repr_contains_fpath_and_count(self, tree):
        expanded = expand_fpath(str(tree / "tr{trajectory:d}/job{job:d}.log"))
        text = repr(expanded)
        assert repr(expanded.fpath) in text
        assert "4 matches found" in text

    def test_metadata_property(self, tree):
        expanded = expand_fpath(str(tree / "tr{trajectory:d}/job{job:d}.log"))
        metadata = expanded.metadata
        assert set(metadata.keys()) == set(expanded.paths)
        assert all(isinstance(v, dict) for v in metadata.values())


class TestExpandFpath:
    def test_returns_expanded_fpath(self, tree):
        expanded = expand_fpath(str(tree / "tr{trajectory:d}/job{job:d}.log"))
        assert isinstance(expanded, ExpandedFPath)
        assert len(expanded) == 4


class TestIsExpandable:
    def test_true_for_named_fields(self):
        assert is_expandable("tr{a}/job{b}.log") is True

    def test_false_for_no_fields(self):
        assert is_expandable("tr1/job2.log") is False

    def test_false_for_non_string(self):
        assert is_expandable(123) is False


class TestExpandFpathDecorator:
    def test_wraps_plain_string(self, tree):
        @expand_fpath_decorator
        def f(expanded_fpath):
            return expanded_fpath

        result = f(str(tree / "tr{trajectory:d}/job{job:d}.log"))
        assert isinstance(result, ExpandedFPath)
        assert len(result) == 4

    def test_passthrough_expanded_fpath(self, tree):
        @expand_fpath_decorator
        def f(expanded_fpath):
            return expanded_fpath

        expanded = expand_fpath(str(tree / "tr{trajectory:d}/job{job:d}.log"))
        assert f(expanded) is expanded

    def test_require_expandable_false_is_the_default(self):
        @expand_fpath_decorator
        def f(fpath):
            return fpath

        assert f("plain/no/fields.log") == "plain/no/fields.log"

    def test_require_expandable_true_raises(self):
        @expand_fpath_decorator(require_expandable=True)
        def f(expanded_fpath):
            return expanded_fpath

        with pytest.raises(ValueError):
            f("plain/no/fields.log")

    def test_exclude_and_require_metadata_kwargs_are_consumed(self, tree):
        (tree / "trX").mkdir()
        (tree / "trX" / "jobY.log").write_text("bad\n")

        @expand_fpath_decorator
        def f(expanded_fpath):
            return expanded_fpath

        result = f(
            str(tree / "tr{trajectory:d}/job{job:d}.log"),
            require_metadata=False,
        )
        assert len(result) == 5
