#!/bin/bash
current_date=$(date +"%Y-%m-%d-%H-%M")
mkdir backup
cp /home/pi/h-bank/database.sqlite backup/
cp -r /home/pi/h-bank/uploads/* backup/uploads/
tar -czpf "/home/pi/OneDrive/H-Bank/Backups/$current_date.tar.gz" backup
rm -rf backup
