import random
import uuid
import sys
import json
from faker import Factory
from faker.providers.person.fi_FI import Provider as PersonProvider

fake = Factory.create('fi_FI')

email_by_user = {}
users_by_id = {}

def anonymize_users(users):
    usernames = set()
    emails = set()
    for data in users:
        if data['model'] != 'users.user':
            continue

        user = data['fields']

        user['password'] = "!"
        username = fake.user_name()
        while username in usernames:
            username = fake.user_name()
        usernames.add(username)
        user['username'] = username
        user['uuid'] = str(uuid.uuid4())
        if user['first_name']:
            user['first_name'] = fake.first_name()
        if user['last_name']:
            user['last_name'] = fake.last_name()
        user['email'] = fake.email()
        email_by_user[data['pk']] = user['email']
        users_by_id[data['pk']] = user

def remove_secrets(data):
    for model in data:
        fields = model['fields']
        if model['model'] == 'socialaccount.socialapp':
            fields['client_id'] = fake.md5()
            fields['secret'] = fake.md5()
        elif model['model'] == 'socialaccount.socialapp':
            fields['token_secret'] = fake.md5()
            fields['token'] = fake.md5()
        elif model['model'] == 'account.emailaddress':
            fields['email'] = email_by_user[fields['user']]
        elif model['model'] == 'socialaccount.socialaccount':
            fields['extra_data'] = '{}'
            fields['uid'] = users_by_id[fields['user']]['uuid']
        elif model['model'] == 'sessions.session':
            fields['session_data'] = "!"
            model['pk'] = fake.md5()


def main():
    data = json.load(sys.stdin)
    anonymize_users(data)
    remove_secrets(data)
    json.dump(data, sys.stdout, indent=4)


if __name__ == '__main__':
    main()
