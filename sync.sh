cd ../usgs_gspy
git checkout master
git fetch gspy master
git merge gspy/master
git push origin master
git checkout develop
git fetch gspy develop
git merge gspy/develop
git push origin develop
