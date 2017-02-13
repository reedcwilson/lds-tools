#!/usr/bin/env python

import subprocess
import json


people = [
        "Matthew Petersen",
          ]

for person in people:
    args = ["./contact-info.py",
            "-e",
            "1",
            person]
    results = json.loads(subprocess.check_output(args))
    if len(results) > 0:
        print '%s,' % person,
        if 'email' in results[0]:
            print "%s," % results[0]['email'],
        if 'phone' in results[0]:
            print results[0]['phone'],
        print
    else:
        print '"%s"' % person
