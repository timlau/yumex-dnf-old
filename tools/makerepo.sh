#!/usr/bin/env bash
repoLocalDir=~/udv/repos
declare -a branches=(fedora-19 fedora-20 fedora-21)
declare -a rpmdir=(i386 x86_64 SRPMS mock-build)

IFS=",$IFS"
eval mkdir -pv $repoLocalDir/{"${branches[*]}"}/{"${rpmdir[*]}"}
