from importlib import import_module


def import_optional_dependency(package):
    """
    Try to import `package`. If it is not installed, raise an ImportError.

    Parameters
    ----------
    package : :obj:`str`
            The name of the package to import.

    Returns
    -------
    :obj:`module`
    """

    try:
        return import_module(package)
    except ModuleNotFoundError:
        msg = f"optional dependency '{package}' is not installed; please install it and try again."
        raise ModuleNotFoundError(msg) from None
