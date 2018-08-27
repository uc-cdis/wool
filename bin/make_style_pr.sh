#!/bin/bash

set -e

if [[ -z $GITHUB_TOKEN ]]; then
    echo '$GITHUB_TOKEN is unset; exiting'
    exit 1
fi

org="$1"
repo="$2"
clone_url="git@github.com:$org/$repo.git"
username="PlanXCyborg"
email="<planxdemo@gmail.com>"
author="$username $email"

git clone --depth 1 $clone_url
cd $repo
git config credential.username $username
git config github.user $username
git config github.token $GITHUB_TOKEN
git config user.name $username
git config user.email $email
git checkout master
git checkout -b style/blacken
black .
git add --update
git commit -m 'style(blacken): update style for all files' --author "$author"
git push -u origin style/blacken
hub pull-request -m "style/blacken: update style for all files\n\nThis pull request was generated automatically."
