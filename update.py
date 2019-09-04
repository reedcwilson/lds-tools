#!/usr/bin/env python
# -*- coding: utf-8 -*-

import atom
import json
import os
import sys
# import requests
import regex
import datetime
import gdata.contacts.data
import gdata.contacts.client
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
# from selenium import webdriver
# from selenium.webdriver.chrome.options import Options

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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

#
# NOTE: because of a difference in the way that the site does authentication
# now I can't figure out how to do the automatic fetching of the ward directory

    # def get_driver(self):
    #     options = Options()
    #     options.add_argument('--headless')
    #     exe = os.path.join(
    #         os.path.dirname(os.path.realpath(__file__)),
    #         'chromedriver'
    #     )
    #     return webdriver.Chrome(exe, chrome_options=options)

    # def login(self, s):
    #     filename = os.path.join(DIRPATH, 'ldspass')
    #     password = self.get_password(filename)
    #     driver = self.get_driver()
    #     driver.get('https://ident.churchofjesuschrist.org/sso/UI/Login')
    #     driver.find_element_by_id('IDToken1').send_keys(USERNAME)
    #     driver.find_element_by_id('IDToken2').send_keys(password)
    #     driver.find_element_by_id('login-submit-button').click()
    #     excludes = ['httpOnly', 'expiry']
    #     for c in driver.get_cookies():
    #         # print('{}:{}'.format(c["name"], c["value"]))
    #         for value in excludes:
    #             if value in c:
    #                 del(c[value])
    #         s.cookies.set(**c)

    # def get_unit(self, s):
    #     r = s.get(
    #         'https://directory.churchofjesuschrist.org/api/v4/user',
    #         verify=False
    #     )
    #     return r.json()["homeUnits"][0]

    # def get_directory(self, s, unit_id):
    #     return s.get(
    #         'https://directory.churchofjesuschrist.org/api/v4/households',
    #         params={
    #             'unit': unit_id
    #         },
    #         verify=False
    #     ).json()

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

    def augment_first_last(self, member):
        first, last = self.get_first_last(member['displayName'])
        member['first_last'] = u'{} {}'.format(first, last)
        member['first'] = first
        member['last'] = last

    # def get_members(self):
    #     if len(self.members) == 0:
    #         with requests.Session() as s:
    #             self.login(s)
    #             # directory = self.get_directory(s, self.get_unit(s))
    #             directory = self.parse_directory()
    #             self.members = [m for h in directory for m in h['members']]
    #             for m in self.members:
    #                 self.augment_first_last(m)
    #     return self.members

    def get_members(self):
        if len(self.members) == 0:
            directory = self.parse_directory()
            self.members = [m for h in directory for m in h['members']]
            for m in self.members:
                self.augment_first_last(m)
        return self.members

    def get_member_parts(self, m):
        fl = m['first_last']
        first = m['first']
        last = m['last']
        email = m['email'] if 'email' in m else ""
        phone = m['phone'] if 'phone' in m else ""
        phone = regex.sub("[^0-9]", "", phone)
        return fl, first, last, email, phone


def patched_post(
        client,
        entry,
        uri,
        auth_token=None,
        converter=None,
        desired_class=None,
        **kwargs
):
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
    # try to get the members first so we don't delete what we already have just
    # to fail
    lds = Lds()
    members = lds.get_members()

    manager = ContactsManager()
    google_contacts = manager.get_contacts()
    group = manager.delete_group_contacts('ward', google_contacts)
    google_contacts = manager.get_contacts()
    phone_numbers = numberify(google_contacts)
    contacts = []
    for member in members:
        first_last, first, last, email, phone = lds.get_member_parts(member)
        # if they have contact method
        if email or phone:
            # if we don't already have them as a contact
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
    print("finished adding {} contacts: {}".format(
        len(contacts),
        datetime.datetime.now().strftime("%B %d, %Y %I:%M %p"))
    )


if __name__ == '__main__':
    main()
