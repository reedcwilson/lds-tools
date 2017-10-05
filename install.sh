#!/bin/bash

name=synclds

filename=com.reedcwilson.${name}.plist
pyinstaller -y update.spec
launchctl unload ~/Library/LaunchAgents/${filename}
cp ${filename} ~/Library/LaunchAgents
launchctl load ~/Library/LaunchAgents/${filename}
launchctl list | grep ${name}
