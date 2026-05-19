m=$1

tag=$(git tag)
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

git add -A
git commit -m "tag $tag"
git push origin main

git checkout main
git pull origin main

git tag $tag
git push origin $tag
