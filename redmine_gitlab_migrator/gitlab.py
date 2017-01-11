import re

from . import APIClient, Project


class GitlabClient(APIClient):
    # see http://doc.gitlab.com/ce/api/#pagination
    MAX_PER_PAGE = 100

    def __init__(self, api_key):
        super().__init__(api_key)
        self.headers = {"PRIVATE-TOKEN": self.api_key}
        self.url = None

    def get(self, *args, **kwargs):
        kwargs['params'] = kwargs.get('params', {})
        kwargs['params']['per_page'] = self.MAX_PER_PAGE
        kwargs['params']['page'] = 1

        results = []
        while True:
            data = super().get(*args, **kwargs)
            if len(data) == 0:
                break;

            results += data
            kwargs['params']['page'] = kwargs['params']['page'] + 1

        return results

    def post(self, *args, **kwargs):
        data = kwargs['data']
        sudo_user = data.get('sudo', None)
        is_sudo_user = sudo_user is not None
        original_headers = self.headers
        if is_sudo_user:
            self.set_temp_headers(sudo_user)
        post_value = super(GitlabClient, self).post(*args, **kwargs)
        if is_sudo_user:
            self.reset_temp_headers(original_headers)
        return post_value

    def put(self, *args, **kwargs):
        data = kwargs['data']
        sudo_user = data.get('sudo', None)
        is_sudo_user = sudo_user is not None
        original_headers = self.headers
        if is_sudo_user:
            self.set_temp_headers(sudo_user)
        post_value = super(GitlabClient, self).put(*args, **kwargs)
        if is_sudo_user:
            self.reset_temp_headers(original_headers)
        return post_value

    def get_auth_headers(self):
        return self.headers

    def check_is_admin(self):
        pass

    def set_temp_headers(self, user):
        self.headers["SUDO"] = user
        user_data = super(GitlabClient, self).get('{}/user'.format(self.url)) # we do not want pagination on this request
        self.headers = {"PRIVATE-TOKEN": user_data["private_token"], "SUDO": user}

    def reset_temp_headers(self, original_headers):
        self.headers = original_headers


class GitlabInstance:
    def __init__(self, url, client):
        self.url = url.strip('/')  # normalize URL
        self.api = client
        self.api.url = self.url
        self.all_users = None
        self.users = None

    def get_all_users(self):
        if self.all_users is None:
            self.all_users = self.api.get('{}/users'.format(self.url))
        return self.all_users

    def get_users_index(self):
        """ Returns dict index of users (by login)
        """
        if self.users is None:
            self.users = {i['username']: i for i in self.get_all_users()}
        return self.users

    def check_users_exist(self, usernames):
        """ Returns True if all users exist
        """
        gitlab_user_names = set([i['username'] for i in self.get_all_users()])
        return all((i in gitlab_user_names for i in usernames))

    def create_user(self, data):
        self.api.post(
            '%(base_url)s/users/' % {'base_url': self.url},
            data
        )

    def update_users_to_admin(self, users):
        updated_users = []
        for login in users:
            user = self.users[login]
            if not user['is_admin']:
                updated_users.append(login)
                self.make_admin(user, True)
        return updated_users

    def downgrade_users_from_admin(self, updated_users):
        for login in updated_users:
            self.make_admin(self.users[login], False)
        pass

    def make_admin(self, user, is_admin):
        return self.api.put('{}/users/{}?admin={}'.format(self.url, user['id'], 'true' if is_admin else 'false'), {})

class GitlabProject(Project):
    REGEX_PROJECT_URL = re.compile(
        r'^(?P<base_url>https?://.*/)(?P<namespace>[\w_-]+)/(?P<project_name>[\w_-]+)$')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_url = (
            '{base_url}api/v3/projects/{namespace}%2F{project_name}'.format(
                **self._url_match.groupdict()))
        self.instance_url = '{}/api/v3'.format(
            self._url_match.group('base_url'))

    def is_repository_empty(self):
        """ Heuristic to check if repository is empty
        """
        return self.api.get(self.api_url)['default_branch'] is None

    def create_issue(self, data, meta):
        """ High-level issue creation

        :param meta: dict with "sudo_user", "should_close" and "notes" keys
        :param data: dict formatted as the gitlab API expects it
        :return: the created issue (without notes)
        """
        altered_data = data.copy()
        altered_data['sudo'] = meta['sudo_user']
        issues_url = '{}/issues'.format(self.api_url)
        issue = self.api.post(
            issues_url, data=altered_data)

        issue_url = '{}/{}'.format(issues_url, issue['id'])
        issue_notes_url = '{}/notes'.format(issue_url, 'notes')

        issue_closed = False

        for note_data, note_meta in meta['notes']:
            if note_meta.get('must_close', False):
                issue_closed = True
                altered_issue = {
                    'id': issue['project_id'],
                    'issue_id': issue['id'],
                    'updated_at': note_data['updated_at'],
                    'state_event': note_data['state_event'],
                    'sudo': note_meta['sudo_user']
                }
                self.api.put(issue_url, data=altered_issue)
            else:
                altered_note = note_data.copy()
                altered_note['sudo'] = note_meta['sudo_user']
                self.api.post(
                    issue_notes_url, data=altered_note)

        # Handle closed status
        if not issue_closed and meta['must_close']:
            altered_issue = {
                'id': issue['project_id'],
                'issue_id': issue['id'],
                'updated_at': meta['closed_at'],
                'state_event': 'close',
                'sudo': meta['sudo_user']
            }
            self.api.put(issue_url, data=altered_issue)

        return issue

    def create_milestone(self, data, meta):
        """ High-level milestone creation

        :param meta: dict with "should_close"
        :param data: dict formatted as the gitlab API expects it
        :return: the created milestone
        """
        milestones_url = '{}/milestones'.format(self.api_url)
        milestone = self.api.post(milestones_url, data=data)

        if meta['must_close']:
            milestone_url = '{}/{}'.format(milestones_url, milestone['id'])
            altered_milestone = milestone.copy()
            altered_milestone['state_event'] = 'close'

            self.api.put(milestone_url, data=altered_milestone)
        return milestone

    def get_issues(self):
        return self.api.get('{}/issues'.format(self.api_url))

    def get_members(self):
        return self.api.get('{}/members'.format(self.api_url))

    def get_milestones(self):
        if not hasattr(self, '_cache_milestones'):
            self._cache_milestones = self.api.get(
                '{}/milestones'.format(self.api_url))
        return self._cache_milestones

    def get_milestones_index(self):
        return {i['title']: i for i in self.get_milestones()}

    def get_milestone_by_id(self, _id):
        milestones = self.get_milestones()
        for i in milestones:
            if i['id'] == _id:
                return i
        raise ValueError('Could not get milestone')

    def has_members(self, usernames):
        gitlab_user_names = set([i['username'] for i in self.get_members()])
        return all((i in gitlab_user_names for i in usernames))

    def get_id(self):
        return self.api.get(self.api_url)['id']

    def get_instance(self):
        """ Return a GitlabInstance
        """
        return GitlabInstance(self.instance_url, self.api)
