from functools import wraps
import parse

from .fpath import ExpandedFPath, FPath


def expand(fpath, *, exclude_path_patterns=None, require_metadata=True):
    """
    Use an f-string to extract out a collection of paths, where the f-string variables
    are captured and stored along the path name. This is a convenience function that
    simply creates an :obj:`FPath` and calls its :meth:`.expand` method.

    Parameters
    ----------
    fpath : :obj:`str`
        An f-string path, where the variables are captured and stored along the path
        name.
    exclude_path_patterns : :obj:`str` or :obj:`Iterable`[:obj:`str`]
        Exclude paths that match the supplied pattern. (Default: None).
    require_metadata : :obj:`bool`
        Require that all paths identified must have found metadata. (Default: True).

    Returns
    -------
    :obj:`.ExpandedFPath`
    """

    return FPath(fpath).expand(
        exclude_path_patterns=exclude_path_patterns,
        require_metadata=require_metadata,
    )


def iexpand(fpath, *, exclude_path_patterns=None, require_metadata=True, errors="raise"):
    """
    Generator equivalent of :func:`.expand` -- lazily yields each
    matching :obj:`.Path` instead of building the whole
    :obj:`.ExpandedFPath` up front. This is a convenience function that
    simply creates an :obj:`FPath` and calls its :meth:`.FPath.iexpand`
    method.

    Parameters
    ----------
    fpath : :obj:`str`
        An f-string path, where the variables are captured and stored along the path
        name.
    exclude_path_patterns : :obj:`str` or :obj:`Iterable`[:obj:`str`]
        Exclude paths that match the supplied pattern. (Default: None).
    require_metadata : :obj:`bool`
        Require that all paths identified must have found metadata. (Default: True).
    errors : :obj:`str`
        How to handle the "no matches" case. See :meth:`.FPath.iexpand`. (Default: "raise").

    Yields
    ------
    :obj:`.Path`
    """

    return FPath(fpath).iexpand(
        exclude_path_patterns=exclude_path_patterns,
        require_metadata=require_metadata,
        errors=errors,
    )


def expand_arg(f=None, require_expandable=False):
    """
    Decorator for :func:`.expand`. Expands `fpath` (if it has {}
    named captures) before calling the wrapped function with the result;
    otherwise calls it with `fpath` unchanged. Callers that need to react
    differently depending on whether expansion actually happened (e.g. to
    join in captured metadata) should check `isinstance(expanded_fpath,
    ExpandedFPath)` themselves, inside the wrapped function -- this
    decorator doesn't hook into that, it only handles expansion.

    Parameters
    ----------
    f : :obj:`callable`
        A function that takes an :obj:`.ExpandedFPath` (or, if not
        expandable and `require_expandable` is False, the original `fpath`)
        as its first argument.
    require_expandable : :obj:`bool`
        Whether to require `fpath` to have {} named captures, raising
        ValueError otherwise. If False (the default), a plain literal path
        or glob is passed straight through to `f` unexpanded. (Default: False)
    """

    def decorator(f):
        @wraps(f)
        def wrapper(fpath, *args, **kwargs):
            # If fpath is already an :obj:`ExpandedFPath`, just call f with it.
            if isinstance(fpath, ExpandedFPath):
                return f(fpath, *args, **kwargs)

            # Expand fpath if it is expandable.
            if is_expandable(fpath):
                exclude_path_patterns = kwargs.pop("exclude_path_patterns", None)
                require_metadata = kwargs.pop("require_metadata", True)
                expanded_fpath = expand(
                    fpath,
                    exclude_path_patterns=exclude_path_patterns,
                    require_metadata=require_metadata,
                )
                return f(expanded_fpath, *args, **kwargs)

            # fpath has no {} captures.
            if require_expandable:
                msg = f"fpath not expandable: '{fpath}'"
                raise ValueError(msg)
            return f(fpath, *args, **kwargs)

        return wrapper

    if f is None:
        return decorator
    else:
        return decorator(f)

def is_expandable(fpath):
    """
    Check whether `fpath` has fpathlib's own named f-string captures (e.g.
    `{name}`).

    Parameters
    ----------
    fpath : :obj:`str`

    Returns
    -------
    :obj:`bool`
    """

    try:
        parser = parse.compile(str(fpath))
        return bool(parser.named_fields)
    except TypeError:
        return False
