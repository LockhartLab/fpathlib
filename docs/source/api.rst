API Reference
=============

Path
----

.. autoclass:: fpathlib.Path
   :members:
   :undoc-members:
   :show-inheritance:

FPath and ExpandedFPath
-----------------------

.. autoclass:: fpathlib.FPath
   :members:
   :undoc-members:

.. autoclass:: fpathlib.ExpandedFPath
   :members:
   :undoc-members:

Expanding paths
----------------

.. autofunction:: fpathlib.expand_fpath

.. autofunction:: fpathlib.expand_fpath_decorator

.. autofunction:: fpathlib.is_expandable

Polars extension
-----------------

.. automodule:: fpathlib.ext.polars
   :members: read_csv, read_txt, scan_csv, scan_parquet, scan_txt
