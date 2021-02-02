#!/bin/bash
current_date=$(date +"%Y-%m-%d_%H-%M")
mkdir backup
mkdir backup/uploads
cp /home/pi/h-bank/database.sqlite backup/
cp -r /home/pi/h-bank/uploads/profile_pictures backup/uploads/
tar -czpf "/home/pi/OneDrive/Backups/HBank/$current_date.tar.gz" backup
rm -rf backup
