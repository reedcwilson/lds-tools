#!/usr/bin/env python

import requests
import json
import regex
import sys
import os
import getopt


DIRPATH = os.path.dirname(os.path.realpath(__file__))


def get_password(filename):
    with open(filename, 'r') as f:
        return f.read()


def login(session):
    filename = os.path.join(DIRPATH, 'ldspass')
    data = {"username": 'reedcwilson', 'password': get_password(filename)}
    session.post(
            'https://signin.lds.org/login.html',
            data=data
            )


def get_me(session):
    resp = session.get(
            'https://www.lds.org/mobiledirectory/services/v2/ldstools/current-user-detail')
    my_id = resp.json()["individualId"]
    unit_id = resp.json()["homeUnitNbr"]
    return my_id, unit_id


def get_directory(s, unit_id):
    resp = s.get("https://www.lds.org/mobiledirectory/services/v2/ldstools/member-detaillist-with-callings/%s" % unit_id)
    return resp.json()


def write_members(members):
    with open(os.path.join(DIRPATH, 'members'), 'w') as f:
        f.write(json.dumps(members))


def write_csv(members):
    with open(os.path.join(DIRPATH, 'contacts.csv'), 'w') as f:
        f.write("Name,Given Name,Family Name,Group Membership,E-mail 1 - Value,Phone 1 - Type,Phone 1 - Value\n")
        for member in members:
            backupFirstLast = member['firstLast'].replace(',', '') if 'firstLast' in member else ""
            givenName = member['givenName'] if 'givenName' in member else ""
            surname = member['surname'] if 'surname' in member else ""
            first = None
            last = None
            if 'preferredName' in member:
                first, last = get_first_last(member['preferredName'])
            else:
                first, last = givenName, surname
            firstLast = "{} {}".format(first, last) if 'preferredName' in member else backupFirstLast
            email = member['email'] if 'email' in member else ""
            phone = member['phone'] if 'phone' in member else ""
            phone = regex.sub("[^0-9]", "", phone)
            try:
                # f.write("%s,%s,,%s,,,,,,,,,,,,,,,,,,,,,,,Grove 9th Ward,* ,%s,,,,,Mobile,%s,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,\n"
                f.write("%s,%s,%s,Grove 9th Ward,%s,Mobile,%s,\n"
                        % (firstLast, first, last, email, phone))
            except Exception as e:
                print(firstLast, phone, email)


def get_cached_members():
    filename = 'members'
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.loads(f.read())


def normalize_name(name):
    idx = name.index(',')
    return ('%s %s' % (name[idx+1:], name[:idx])).strip()


def get_first_last(name):
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


def add_member(member, members, household):
    if member in household:
        person = household[member]
        name = 'fullName'
        preferred = 'preferredName'
        phone = 'phone'
        if name in person:
            person[name] = normalize_name(person[name])
            first, last = get_first_last(person[name])
            person['firstLast'] = '{} {}'.format(first, last)
        if preferred in person:
            person[preferred] = normalize_name(person[preferred])
        if phone not in person and phone in household:
            person[phone] = household[phone]
        members.append(person)


def get_members(directory):
    members = []
    spouse = 'spouse'
    head = 'headOfHouse'
    with open('directory.json', 'w') as f:
        f.write(json.dumps(directory))
    for household in directory['households']:
        add_member(head, members, household)
        add_member(spouse, members, household)
    return members


def get_match(name, member, error_length):
    regex_str = r"(?bi)(?:%s){e<=%s}" % (name, error_length)
    match = regex.search(regex_str, member['preferredName'])
    if match:
        return match
    return regex.search(regex_str, member['firstLast'])


def find_member(name, members, error_length):
    matches = []
    for member in members:
        match = get_match(name, member, error_length)
        if match:
            matches.append(member)
    return matches


def strip_matches(matches):
    new_matches = []
    for match in matches:
        new_match = {}
        for param in ['firstLast', 'phone', 'email']:
            if param in match:
                new_match[param] = match[param]
        new_matches.append(new_match)
    return new_matches


def main(names, error_length, full_contact, csv):
    members = get_cached_members()
    if not members:
        with requests.Session() as s:
            login(s)
            my_id, unit_id = get_me(s)
            directory = get_directory(s, unit_id)
            members = get_members(directory)
            write_members(members)
    if csv:
        write_csv(members)
        return
    for name in names:
        matches = find_member(name, members, error_length)
        if full_contact:
            print(json.dumps(matches))
        else:
            matches = strip_matches(matches)
            print(json.dumps(matches))


def print_usage(exit):
    print((
            "./contact-info.py "
            "[-e <errorlevel> (default: 3)] "
            "[-c create contacts.csv (default: False)] "
            "[-f full contact info (default: False)]"
            ))
    sys.exit(exit)


def get_args(argv):
    errorlevel = 3
    fullcontact = False
    csv = False
    try:
        opts, args = getopt.getopt(argv[1:], "he:fc")
    except getopt.GetoptError:
        print_usage(2)
    for opt, arg in opts:
        if opt == '-h':
            print_usage(0)
        elif opt in ("-e"):
            errorlevel = arg
        elif opt in ("-f"):
            fullcontact = True
        elif opt in ("-c"):
            csv = True
    return errorlevel, fullcontact, csv, args


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print_usage(2)
    error_length, full_contact, csv, names = get_args(sys.argv)
    main(names, error_length, full_contact, csv)
