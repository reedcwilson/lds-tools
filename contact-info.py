#!/usr/bin/env python

import requests
import json
import regex
import sys
import os


def get_password(filename):
    with open(filename, 'r') as f:
        return f.read()


def login(session):
    data = {"username": 'reedcwilson', 'password': get_password('ldspass')}
    resp = session.post(
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
    with open('members', 'w') as f:
        f.write(json.dumps(members))


def get_cached_members():
    filename = 'members'
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.loads(f.read())


def normalize_name(name):
    idx = name.index(',')
    return ('%s %s' % (name[idx+1:], name[:idx])).strip()


def get_first_last(name):
    if name.count(' ') > 1:
        first = name.index(' ')
        last = name.rfind(' ')
        return '%s %s' % (name[:first], name[last+1:])
    return name


def add_member(member, members, household):
    if member in household:
        person = household[member]
        name = 'fullName'
        preferred = 'preferredName'
        if name in person:
            person[name] = normalize_name(person[name])
            person['firstLast'] = get_first_last(person[name])
        if preferred in person:
            person[preferred] = normalize_name(person[preferred])
        members.append(person)


def get_members(directory):
    members = []
    spouse = 'spouse'
    head = 'headOfHouse'
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


def main(name, error_length):
    members = get_cached_members()
    if not members:
        with requests.Session() as s:
            login(s)
            my_id, unit_id = get_me(s)
            directory = get_directory(s, unit_id)
            members = get_members(directory)
            write_members(members)
    matches = find_member(name, members, error_length)
    print json.dumps(matches)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print "You must supply a name to search for"
        sys.exit()
    error_length = 3
    if len(sys.argv) == 3:
        error_length = sys.argv[2]
    main(sys.argv[1], error_length)
