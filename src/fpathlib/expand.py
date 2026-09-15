from functools import wraps
import parse

from .fpath import ExpandedFPath, FPath


def expand_fpath(fpath, *, exclude_path_patterns=None, require_metadata=True):
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


def expand_fpath_decorator(f=None, require_expandable=True, post_process=None):
    """
    Decorator for :func:`.expand_fpath`.

    Parameters
    ----------
    f : :obj:`callable`
        A function that takes an :ref:`.ExpandedFPath` as its first argument.
    post_process : :obj:`callable`
        A function that takes the output of `f` and the :ref:`.ExpandedFPath`.
        (Default: None).
    """

    def decorator(f):
        @wraps(f)
        def wrapper(fpath, *args, **kwargs):
            # If fpath is an :obj:`ExpandedFPath`, just call f with it.
            if isinstance(fpath, ExpandedFPath):
                expanded_fpath = fpath
                result = f(fpath, *args, **kwargs)

            # Otherwise, expand fpath and call f with the result.
            else:
                # What happens if fpath is not expandable?
                # If require_expandable is True, raise an error.
                # Otherwise, just call f with the original fpath.
                if not is_expandable(fpath):
                    if require_expandable:
                        msg = f"fpath not expandable: '{fpath}'"
                        raise ValueError(msg)
                    return f(fpath, *args, **kwargs)

                # We know fpath is expandable, so we can expand it and call f
                exclude_path_patterns = kwargs.pop("exclude_path_patterns", None)
                require_metadata = kwargs.pop("require_metadata", True)
                expanded_fpath = expand_fpath(
                    fpath,
                    exclude_path_patterns=exclude_path_patterns,
                    require_metadata=require_metadata,
                )
                result = f(expanded_fpath, *args, **kwargs)

            # If post_process is provided, call it with the result and the expanded_fpath.
            if post_process is not None:
                result = post_process(result, expanded_fpath)

            return result

        return wrapper

    if f is None:
        return decorator
    else:
        return decorator(f)

def is_expandable(fpath):
    """
    Check if expandable.

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
