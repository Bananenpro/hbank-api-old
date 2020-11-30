#!/bin/bash
current_date=$(date +"%Y-%m-%d_%H-%M")
mkdir backup
mkdir backup/uploads
mkdir backup/uploads/profile_pictures
cp /home/pi/h-bank/database.sqlite backup/
cp -r /home/pi/h-bank/uploads/profile_pictures backup/uploads/profile_pictures
tar -czpf "/home/pi/OneDrive/H-Bank/Backups/$current_date.tar.gz" backup
rm -rf backup
