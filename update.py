from datetime import datetime
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import json
import os.path
import pickle
import re
import time

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/gmail-python-quickstart.json
SCOPES = 'https://www.google.com/m8/feeds/'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Ward Contacts Sync'


def get_creds():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return creds


class Lds(object):

    def __init__(self):
        self.members = []

    def parse_directory(self):
        with open('directory.json') as f:
            return json.loads(f.read())

    def get_first_last(self, name):
        num = name.count(' ')
        if num >= 1:
            first = name.index(' ')
            last = name.rfind(' ')
            return name[:first], name[last+1:]
        else:
            return name, ""

    def take_household(self, h, m, v):
        if (
            m['head'] and
            v not in m and
            v in h and
            h[v] not in [m_[v] for m_ in h['members'] if v in m_]
        ):
            m[v] = h[v]

    def augment(self, member):
        first, last = self.get_first_last(member['displayName'])
        member['first'] = first
        member['last'] = last
        h_id = member['householdUuid']
        household = self.households[h_id]
        # make the member's info the household info if the member is a
        # household head and no other member has the same info
        self.take_household(household, member, 'phone')
        self.take_household(household, member, 'email')

    def get_members(self):
        if len(self.members) == 0:
            directory = self.parse_directory()
            self.households = {h['uuid']: h for h in directory}
            self.members = [m for h in directory for m in h['members']]
            for m in self.members:
                self.augment(m)
        return self.members


class ContactsManager(object):

    def __init__(self):
        self.groupResourceName = None
        self.service = build('people', 'v1', credentials=get_creds())

    def list(self):
        return self.service.people().connections().list(
            resourceName='people/me',
            pageSize=1000,
            personFields='names,emailAddresses,phoneNumbers'
        ).execute().get('connections', [])

    def refresh_group(self):
        groups = [
            g for g in
            self.service
                .contactGroups()
                .list()
                .execute()
                .get('contactGroups', [])
            if g.get('name') == 'Ward'
        ]
        if groups:
            self.service.contactGroups().delete(
                resourceName=groups[0]['resourceName'],
                deleteContacts=True
            ).execute()
        self.groupResourceName = self.service.contactGroups().create(body={
            "contactGroup": {
                "name": "Ward",
            },
        }).execute()['resourceName']

    def create(self, first, last, email, phone):
        self.service.people().createContact(body={
            "emailAddresses": [{
                "value": email,
                },
            ],
            "names": [{
                "familyName": last,
                "givenName": first,
                },
            ],
            "phoneNumbers": [{
                "value": phone,
                "type": "mobile",
                },
            ],
            "memberships": [{
                "contactGroupMembership": {
                    "contactGroupResourceName": self.groupResourceName,
                },
            }],
        }).execute()


def numberify(contacts):
    nums = {}
    for c in contacts:
        if 'phoneNumbers' in c:
            for n in c['phoneNumbers']:
                nums[n['value']] = c['names'][0]['displayNameLastFirst']
    return nums


def partify(m):
    first = m['first']
    last = m['last']
    email = m['email'] if 'email' in m else ""
    phone = m['phone'] if 'phone' in m else ""
    phone = re.sub("[^0-9]", "", phone)
    return first, last, email, phone


def report(members):
    print("ward contacts: {}".format(len(members)))
    numbers = sum(1 for m in members if 'phone' in m)
    print('members with phone numbers: {}'.format(numbers))
    emails = sum(1 for m in members if 'email' in m)
    print('members with email addresses: {}'.format(emails))


def main():
    # try to get the members first so we don't delete what we already have just
    # to fail
    members = Lds().get_members()
    report(members)
    manager = ContactsManager()
    manager.refresh_group()  # recreate a fresh contacts group
    time.sleep(3)  # wait for eventual consistency
    phones = numberify(manager.list())
    print('phone numbers in contacts: {}'.format(len(phones)))
    contacts = []
    for i, m in enumerate(members):
        first, last, email, phone = partify(m)
        # if contact method exists and I don't already have them
        if (email or phone) and phone not in phones:
            if phone not in phones:
                contacts.append(manager.create(first, last, email, phone))
    now = datetime.now().strftime("%B %d, %Y %I:%M %p")
    print(f"finished adding {len(contacts)} contacts: {now}")


if __name__ == '__main__':
    main()
