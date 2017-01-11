#!/bin/sh

set -x
set -e

. ./environment.sh

python3 gerrit_ssh_migrator.py --gerrit-key=${REDMINE_KEY} --gitlab-key=${GITLAB_KEY} $GERRIT_HOST ${GITLAB_HOST}
