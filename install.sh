#!/bin/bash

name=synclds

filename=com.reedcwilson.${name}.plist
path=$(dirname $(realpath $0))
launchctl unload ~/Library/LaunchAgents/${filename}
cat $filename | sed "s|#HOME|${HOME}|g" | sed "s|#PROJECT|${path}|g" > ~/Library/LaunchAgents/${filename}
launchctl load ~/Library/LaunchAgents/${filename}
launchctl list | grep ${name}
