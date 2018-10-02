#!/usr/bin/env python
# -*- coding: utf-8 -*-

import atom
import os
import requests
import regex
import datetime
import gdata.contacts.data
import gdata.contacts.client
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage


try:
    import argparse
    parser = argparse.ArgumentParser(parents=[tools.argparser])
    parser.add_argument('--path')
    parser.add_argument('--token')
    flags = parser.parse_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/gmail-python-quickstart.json
SCOPES = 'https://www.google.com/m8/feeds/'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Ward Contacts Sync'
USERNAME = 'reedcwilson'

DIRPATH = os.sep + os.path.join('Volumes', 'Secrets')


def get_embedded_filename(filename):
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller >= 1.6
        os.chdir(sys._MEIPASS)
        filename = os.path.join(sys._MEIPASS, filename)
    elif '_MEIPASS2' in os.environ:
        # PyInstaller < 1.6 (tested on 1.5 only)
        os.chdir(os.environ['_MEIPASS2'])
        filename = os.path.join(os.environ['_MEIPASS2'], filename)
    else:
        os.chdir(os.path.dirname(sys.argv[0]))
        filename = os.path.join(os.path.dirname(sys.argv[0]), filename)
    return filename


def chunks(arr, n):
    """Yield successive n-sized chunks from arr."""
    for i in xrange(0, len(arr), n):
        yield arr[i:i + n]


def get_credentials():
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'lds_contacts_sync.json')
    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(
            get_embedded_filename(CLIENT_SECRET_FILE),
            SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else:
            # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials


class Lds(object):

    def __init__(self):
        self.members = []

    def get_password(self, filename):
        with open(filename, 'r') as f:
            return f.read()

    def lds_login(self, session):
        filename = os.path.join(DIRPATH, 'ldspass')
        data = {
                "username": USERNAME,
                'password': self.get_password(filename)
                }
        session.post(
                'https://signin.lds.org/login.html',
                data=data)

    def get_profile_user(self, session):
        resp = session.get(
                'https://www.lds.org/mobiledirectory/services/v2/ldstools/current-user-detail')
        my_id = resp.json()["individualId"]
        unit_id = resp.json()["homeUnitNbr"]
        return my_id, unit_id

    def get_ward_directory(self, s, unit_id):
        resp = s.get(
                "https://www.lds.org/mobiledirectory/services/v2/ldstools/member-detaillist-with-callings/%s" % unit_id)
        return resp.json()

    def normalize_name(self, name):
        idx = name.index(',')
        return ('%s %s' % (name[idx+1:], name[:idx])).strip()

    def get_first_last(self, name):
        num = name.count(' ')
        if num > 1:
            first = name.index(' ')
            last = name.rfind(' ')
            return name[:first], name[last+1:]
        elif num == 1:
            parts = name.split()
            return parts[0], parts[1]
        else:
            return name, ""

    def add_member(self, member, household):
        if member in household:
            person = household[member]
            name = 'fullName'
            preferred = 'preferredName'
            phone = 'phone'
            if name in person:
                person[name] = self.normalize_name(person[name])
                first, last = self.get_first_last(person[name])
                person['firstLast'] = u'{} {}'.format(first, last)
            if preferred in person:
                person[preferred] = self.normalize_name(person[preferred])
            if phone not in person and phone in household:
                person[phone] = household[phone]
            self.members.append(person)

    def get_members(self):
        if len(self.members) == 0:
            with requests.Session() as s:
                self.lds_login(s)
                my_id, unit_id = self.get_profile_user(s)
                directory = self.get_ward_directory(s, unit_id)
                spouse = 'spouse'
                head = 'headOfHouse'
                for household in directory['households']:
                    self.add_member(head, household)
                    self.add_member(spouse, household)
        return self.members

    def get_member_parts(self, member):
        backupFirstLast = member['first_last'].replace(',', '') if 'first_last' in member else ""
        givenName = member['givenName'] if 'givenName' in member else ""
        surname = member['surname'] if 'surname' in member else ""
        first = None
        last = None
        if 'preferredName' in member:
            first, last = self.get_first_last(member['preferredName'])
        else:
            first, last = givenName, surname
        first_last = u"{} {}".format(first, last) if 'preferredName' in member else backupFirstLast
        email = member['email'] if 'email' in member else ""
        phone = member['phone'] if 'phone' in member else ""
        phone = regex.sub("[^0-9]", "", phone)
        return first_last, first, last, email, phone


def patched_post(client, entry, uri, auth_token=None, converter=None, desired_class=None, **kwargs):
    if converter is None and desired_class is None:
        desired_class = entry.__class__
    http_request = atom.http_core.HttpRequest()
    entry_string = entry.to_string(
        gdata.client.get_xml_version(client.api_version))
    entry_string = entry_string.replace('ns1', 'gd')
    http_request.add_body_part(
        entry_string,
        'application/atom+xml')
    return client.request(
        method='POST',
        uri=uri,
        auth_token=auth_token,
        http_request=http_request,
        converter=converter,
        desired_class=desired_class,
        **kwargs)


class ContactsManager(object):

    def __init__(self):
        token = gdata.gauth.OAuth2TokenFromCredentials(get_credentials())
        self.client = gdata.contacts.client.ContactsClient()
        self.client = token.authorize(self.client)

    def get_contacts(self):
        query = gdata.contacts.client.ContactsQuery()
        query.max_results = 2000
        feed = self.client.GetContacts(q=query)
        return feed.entry

    def delete_group_contacts(self, name, contacts):
        feed = self.client.GetGroups()
        group = None
        for g in feed.entry:
            if g.title.text.lower() == name.lower():
                group = g
                break
        if not group:
            raise Exception("Group does not exist")
        contacts_to_delete = []
        for contact in contacts:
            for group_membership_info in contact.group_membership_info:
                if group_membership_info.href == group.id.text:
                    contacts_to_delete.append(contact)
                    break
        batches = chunks(contacts_to_delete, 50)
        for batch in batches:
            request_feed = gdata.contacts.data.ContactsFeed()
            for contact in batch:
                request_feed.AddDelete(
                    entry=contact,
                    batch_id_string="delete")
            patched_post(
                self.client,
                request_feed,
                'https://www.google.com/m8/feeds/contacts/default/full/batch')
        return group

    def create_contact(self, first_last, first, last, email, phone, group):
        contact = gdata.contacts.data.ContactEntry()
        contact.name = gdata.data.Name(
            given_name=gdata.data.GivenName(text=first),
            family_name=gdata.data.FamilyName(text=last),
            full_name=gdata.data.FullName(text=first_last))
        # Set the contact's email addresses.
        if email:
            contact.email.append(
                gdata.data.Email(
                    address=email,
                    primary='true',
                    rel=gdata.data.HOME_REL,
                    display_name=first_last))
        # Set the contact's phone numbers.
        if phone:
            contact.phone_number.append(
                gdata.data.PhoneNumber(
                    text=phone,
                    rel=gdata.data.MOBILE_REL,
                    primary='true'))
        # Set the contact's group membership
        contact.group_membership_info.append(
            gdata.contacts.data.GroupMembershipInfo(href=group.id.text))
        return contact

    def add_contacts(self, contact_entries):
        batches = chunks(contact_entries, 50)
        for batch in batches:
            request_feed = gdata.contacts.data.ContactsFeed()
            for contact in batch:
                request_feed.AddInsert(entry=contact, batch_id_string="create")
            patched_post(
                self.client,
                request_feed,
                'https://www.google.com/m8/feeds/contacts/default/full/batch')


def numberify(contacts):
    numbers = {}
    for contact in contacts:
        for number in contact.phone_number:
            numbers[number.text] = contact.name.full_name.text
    return numbers


def main():
    manager = ContactsManager()
    lds = Lds()
    google_contacts = manager.get_contacts()
    group = manager.delete_group_contacts('ward', google_contacts)
    google_contacts = manager.get_contacts()
    phone_numbers = numberify(google_contacts)
    members = lds.get_members()
    contacts = []
    for member in members:
        first_last, first, last, email, phone = lds.get_member_parts(member)
        if phone not in phone_numbers:
            new_contact = manager.create_contact(
                first_last,
                first,
                last,
                email,
                phone,
                group)
            contacts.append(new_contact)
    manager.add_contacts(contacts)
    print("finished: {}".format(datetime.datetime.now().strftime("%B %d, %Y %I:%M %p")))


if __name__ == '__main__':
    main()
