#!/usr/bin/env bash
fasLogin=timlau
repoLocalDir=~/udv/repos
repoName=yumex
declare -a branch=(fedora-19 fedora-20 fedora-21)
declare -a rpmdir=(i386 x86_64 SRPMS)
declare -a rsyncParam=(-avtz --delete)

cd $repoLocalDir
for dir2 in "${branch[@]}"
do
    echo -e "\033[31mUpdate $dir2 repos:\033[0m"
    cd $dir2
    for dir3 in "${rpmdir[@]}"
    do
        echo -e "\033[34m\t* $dir3:\033[0m"
        cd $dir3
        createrepo ./
        ssh $fasLogin.fedorapeople.org rm -f /srv/repos/$fasLogin/$repoName/$dir2/$dir3/*.rpm
        rsync "${rsyncParam[@]}" ./* $fasLogin@fedorapeople.org:/srv/repos/$fasLogin/$repoName/$dir2/$dir3
        cd ..
    done
    cd ..
done
cd ..
