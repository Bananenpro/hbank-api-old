#!/bin/bash
current_date=$(date +"%Y-%m-%d-%H-%M")
mkdir backup
cp /home/pi/h-bank/database.sqlite backup/
cp -r /home/pi/h-bank/uploads/* backup/uploads/
tar -czpf backup.tar.gz backup
mkdir "/home/pi/OneDrive/H-Bank/Backups/$current_date"
mv backup.tar.gz "/home/pi/OneDrive/Backups/$current_date/"
rm -rf backup
