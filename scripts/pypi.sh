allow_dev=0
if [ "$1" = "dev" ]
then
  allow_dev=1
fi

commits_ahead=$(git describe --tags | awk -F- '{print $2}')
if [ $allow_dev -eq 0 ] && [ "$commits_ahead" != "" ]
then
  echo "current commit ahead of latest tag, not uploading to pypi"
  return 
fi

python -m build
twine upload --verbose dist/*
rm -r dist
rm -r src/fpathlib.egg-info
