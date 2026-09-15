import pathlib


class Path(pathlib.Path):
    """
    :obj:`Path` is simply :obj:`pathlib.Path` with metadata.

    Parameters
    ----------
    *pathsegments
    """

    def __init__(self, *pathsegments, metadata=None):
        super().__init__(*pathsegments)
        self.metadata = metadata

    def match(self, path_patterns, case_sensitive=None):
        """
        Perform :meth:`pathlib.Path.match` on several `path_patterns`.

        Parameters
        ----------
        path_patterns : :obj:`str` or :obj:`Iterable`[:obj:`str`]
            One or more path patterns to match against. (Default: None).
        case_sensitive : :obj:`bool`
            Whether to perform case-sensitive matching. If None, the default, then the
            behavior is determined by the operating system. (Default: None).

        Returns
        -------
        :obj:`generator`[:obj:`bool`]
        """

        if isinstance(path_patterns, str):
            path_patterns = [path_patterns]

        for path_pattern in path_patterns:
            yield super().match(path_pattern, case_sensitive=case_sensitive)

    def match_all(self, path_patterns, case_sensitive=None):
        """
        Perform :meth:`pathlib.Path.match` on several `path_patterns`. All patterns
        must match.

        Parameters
        ----------
        path_patterns : :obj:`str` or :obj:`Iterable`[:obj:`str`]
            One or more path patterns to match against. (Default: None).
        case_sensitive : :obj:`bool`
            Whether to perform case-sensitive matching. If None, the default, then the
            behavior is determined by the operating system. (Default: None).

        Returns
        -------
        :obj:`bool`
        """

        for match in self.match(path_patterns, case_sensitive=case_sensitive):
            if not match:
                return False

        return True

    def match_any(self, path_patterns, case_sensitive=None):
        """
        Perform :meth:`pathlib.Path.match` on several `path_patterns`. Any pattern
        must match.

        Parameters
        ----------
        path_patterns : :obj:`str` or :obj:`Iterable`[:obj:`str`]
            One or more path patterns to match against. (Default: None).
        case_sensitive : :obj:`bool`
            Whether to perform case-sensitive matching. If None, the default, then the
            behavior is determined by the operating system. (Default: None).

        Returns
        -------
        :obj:`bool`
        """

        for match in self.match(path_patterns):
            if match:
                return True

        return False
