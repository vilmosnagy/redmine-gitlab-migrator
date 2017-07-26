#!/bin/sh

set -x

. ./environment.sh

if [ -z "$1" -o -z "$2" ];
then
	echo "Usage: $0 [redmine_project] [gitlab_project]"
	exit 1
else
	REDMINE_NAME="$1"
	GITLAB_NAME="$2"
fi

REDMINE_PROJECT="${REDMINE_HOST}/${REDMINE_NAME}"
GITLAB_PROJECT="${GITLAB_HOST}/${GITLAB_NAME}"

python3 migrate_rg.py ldap-users --redmine-key=${REDMINE_KEY} --gitlab-key=${GITLAB_KEY} "--extern-uid=uid=%(login)s,ou=users,dc=webvalto,dc=hu" "${REDMINE_PROJECT}" "${GITLAB_PROJECT}" || exit 1
python3 migrate_rg.py roadmap --debug --redmine-key=${REDMINE_KEY} --gitlab-key=${GITLAB_KEY} "${REDMINE_PROJECT}" "${GITLAB_PROJECT}"                                                    || exit 1
python3 migrate_rg.py issues --debug --redmine-key=${REDMINE_KEY} --gitlab-key=${GITLAB_KEY} "${REDMINE_PROJECT}" "${GITLAB_PROJECT}"                                                     || exit 1
python3 migrate_rg.py update-iid --debug --redmine-key=${REDMINE_KEY} --gitlab-key=${GITLAB_KEY} "${REDMINE_PROJECT}" "${GITLAB_PROJECT}"                                                 || exit 1

git clone "${GITLAB_PROJECT}.wiki.git" wiki                                                                                                                                               || exit 1
python3 migrate_rg.py pages --redmine-key=${REDMINE_KEY} --gitlab-wiki wiki "${REDMINE_PROJECT}"                                                                                          || exit 1
cd wiki && git push && cd .. && rm -rf wiki
