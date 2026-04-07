python -m build
twine upload dist/*
rm -r dist
rm -r src/metapath.egg-info
