# Builds and (usually) uploads to PyPI. setuptools_scm derives the version
# purely from git: exactly on a tag with a clean tree -> "X.Y.Z"; ahead of
# the last tag, or a dirty tree -> "X.Y.Z.devN". Run this on its own (e.g.
# `source scripts/pypi.sh dev`) to intentionally publish an interim dev
# build while iterating; deploy.sh runs tag.sh first so that by the time
# this script runs, HEAD should be exactly on the new tag and produce a
# clean release -- if it doesn't, something upstream is wrong (see below).
allow_dev=0
if [ "$1" = "dev" ]
then
  allow_dev=1
fi

# Stale dist/ or egg-info from a previous failed run can leak into `twine
# upload dist/*` (multiple versions at once) or shadow a fresh build.
rm -rf dist src/fpathlib.egg-info

python3 -m build

# Belt-and-suspenders check: rather than trust git state ahead of time (the
# 0.1.3/0.1.2 tag-collision incident slipped past a git-describe check even
# though the build itself came out as a .devN), inspect what actually got
# built. This is the real signal of whether the release is clean.
dev_artifacts=$(ls dist/ | grep -c '\.dev[0-9]')
if [ $allow_dev -eq 0 ] && [ "$dev_artifacts" != "0" ]
then
  echo "built version is a dev version (tag doesn't point at a clean, distinct commit -- check 'git describe --tags --long' and 'git status'), not uploading to pypi"
  rm -r dist
  rm -r src/fpathlib.egg-info
  return
fi

twine upload --verbose dist/*
rm -r dist
rm -r src/fpathlib.egg-info
