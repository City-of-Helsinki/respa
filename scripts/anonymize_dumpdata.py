import random
import uuid
import sys
import json
from faker import Factory
from faker.providers.person.fi_FI import Provider as PersonProvider


def anonymize_users(users):
    fake = Factory.create('fi_FI')
    usernames = set()
    emails = set()
    for user in users:
        if user['model'] != 'users.user':
            continue

        user = user['fields']

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


data = json.load(sys.stdin)
anonymize_users(data)
json.dump(data, sys.stdout)
