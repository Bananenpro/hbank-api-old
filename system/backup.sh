#!/bin/bash
current_date=$(date +"%Y-%m-%d-%H-%M")
mkdir backup
cp /home/pi/h-bank/database.sqlite backup/
cp -r /home/pi/h-bank/uploads/profile_pictures backup/uploads/profile_pictures
tar -czpf "/home/pi/OneDrive/H-Bank/Backups/$current_date.tar.gz" backup
rm -rf backup
