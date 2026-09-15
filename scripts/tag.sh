# Bumps the version tag and pushes it. This MUST leave HEAD on a commit that
# is not shared with any older tag, or setuptools_scm can't tell the new tag
# apart from the old one and pypi.sh will build a .devN version instead of a
# clean release (see the 0.1.3/0.1.2 incident: both tags landed on the same
# commit because there was nothing new to commit, so setuptools_scm treated
# the checkout as ambiguous).
set -e

m=$1

tag=$(git describe --tags --abbrev=0)
parts=(${tag//./ })
if [ "$m" == "major" ]
then
  parts[0]=$((parts[0]+1))
  parts[1]=0
  parts[2]=0
elif [ "$m" == "minor" ]
then
  parts[1]=$((parts[1]+1))
  parts[2]=0
elif [ "$m" == "patch" ]
then
  parts[2]=$((parts[2]+1))
else
  echo "must specify major, minor, or patch"
  return
fi
tag="${parts[0]}.${parts[1]}.${parts[2]}"

# Fail loudly instead of leaving a stale/misplaced tag if $tag already exists
# (locally or on origin) -- creating it again would either error out partway
# through or, worse, silently retag the wrong commit.
if git rev-parse -q --verify "refs/tags/$tag" >/dev/null
then
  echo "tag $tag already exists locally -- delete it first (git tag -d $tag) if you really want to redo this release"
  return
fi
if git ls-remote --exit-code --tags origin "$tag" >/dev/null 2>&1
then
  echo "tag $tag already exists on origin -- delete it first (git push origin :refs/tags/$tag) if you really want to redo this release"
  return
fi

git add -A
# --allow-empty is required: if there's nothing to commit (working tree
# already clean), a plain `git commit` would no-op and this tag would end up
# pointing at the SAME commit as the previous tag, confusing setuptools_scm.
git commit --allow-empty -m "tag $tag"
git push origin main

git checkout main
git pull origin main

git tag $tag
git push origin $tag
