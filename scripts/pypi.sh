python -m build
twine upload --verbose dist/*
rm -r dist
rm -r src/fpathlib.egg-info
