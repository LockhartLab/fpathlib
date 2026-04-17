python -m build
twine upload dist/*
rm -r dist
rm -r src/fpathlib.egg-info
