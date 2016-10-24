#!/usr/bin/env python

import requests


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


def main():
    with requests.Session() as s:
        login(s)
        my_id, unit_id = get_me(s)
        directory = get_directory(s, unit_id)
        print directory


if __name__ == '__main__':
    main()
