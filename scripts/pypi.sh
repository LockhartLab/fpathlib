allow_dev=0
if [ "$1" = "dev" ]
then
  allow_dev=1
fi

python3 -m build

dev_artifacts=$(ls dist/ | grep -c '\.dev[0-9]')
if [ $allow_dev -eq 0 ] && [ "$dev_artifacts" != "0" ]
then
  echo "built version is a dev version (tag likely doesn't point at a distinct commit), not uploading to pypi"
  rm -r dist
  rm -r src/fpathlib.egg-info
  return
fi

twine upload --verbose dist/*
rm -r dist
rm -r src/fpathlib.egg-info
