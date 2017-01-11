import argparse
import datetime
import json

import requests
from requests.auth import HTTPDigestAuth


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gerrit-username', required=True)
    parser.add_argument('--gerrit-password', required=True)
    parser.add_argument('--gitlab-key', required=True)
    parser.add_argument('gerrit_url')
    parser.add_argument('gitlab_url')
    return parser.parse_args()


def get_ssh_key_for_user_form_gitlab(user_id):
    return [ssh_key.get('key')
            for ssh_key in
            requests.get(args.gitlab_url + '/api/v3/users/' + str(user_id) + '/keys', headers={"PRIVATE-TOKEN": args.gitlab_key}).json()]


def get_ssh_key_for_user_from_gerrit(username):
    fck_gerrit_json_resp = requests.get(args.gerrit_url + '/a/accounts/' + username + '/sshkeys', auth=HTTPDigestAuth(args.gerrit_username, args.gerrit_password))._content[4:]
    try:
        resp = json.loads(fck_gerrit_json_resp.decode("utf-8"))
        return [{'key': data.get('ssh_public_key'), 'title': data.get('comment')} for data in resp]
    except ValueError:
        return []


def create_new_ssh_key(user_id, new_ssh_key):
    if new_ssh_key.get('title') is None:
        new_ssh_key['title'] = 'Anonym key Imported from Gerrit at: ' + str(datetime.datetime.now())
    resp = requests.post(args.gitlab_url + '/api/v3/users/' + str(user_id) + '/keys', json={"key": new_ssh_key['key'].strip(), "title": new_ssh_key['title']}, headers={"PRIVATE-TOKEN": args.gitlab_key}).json()
    print(resp)
    pass


def gerrit_ssh_migration():
    users = get_gitlab_users(args)
    for user in users:
        print('migrating: ' + user.get('username'))
        ssh_keys_in_gitlab = get_ssh_key_for_user_form_gitlab(user.get('id'))
        ssh_keys_in_gerrit = get_ssh_key_for_user_from_gerrit(user.get('username'))
        for new_ssh_key in [x for x in ssh_keys_in_gerrit if x['key'] not in ssh_keys_in_gitlab]:
            create_new_ssh_key(user.get('id'), new_ssh_key)


def get_gitlab_users(args):
    return requests.get(args.gitlab_url + '/api/v3/users', headers={"PRIVATE-TOKEN": args.gitlab_key}).json()


args = parse_args()
if __name__ == '__main__':
    gerrit_ssh_migration()