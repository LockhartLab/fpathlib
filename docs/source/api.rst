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

.. autofunction:: fpathlib.expand

.. autofunction:: fpathlib.iexpand

.. autofunction:: fpathlib.expand_arg

.. autofunction:: fpathlib.is_expandable

Polars extension
-----------------

.. automodule:: fpathlib.ext.polars
   :members: read_csv, read_txt, scan_csv, scan_parquet, scan_txt
