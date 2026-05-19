allow_dev=0
if [ "$1" = "dev" ]
then
  allow_dev=1
fi

if [ $allow_dev -eq 0 ]
then
  is_dev=
fi

python -m build
twine upload --verbose dist/*
rm -r dist
rm -r src/fpathlib.egg-info
