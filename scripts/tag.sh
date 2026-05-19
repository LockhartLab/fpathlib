tag="0.1.5"

git add -A
git commit -m "tag $tag"
git push origin main

git checkout main
git pull origin main

git tag $tag
git push origin $tag
