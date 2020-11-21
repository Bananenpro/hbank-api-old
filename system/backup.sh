#!/bin/bash
current_date=$(date +"%Y-%m-%d-%H-%M")
cp /home/pi/h-bank/database.sqlite "/home/pi/OneDrive/H-Bank/Backups/database-$current_date-.sqlite"
