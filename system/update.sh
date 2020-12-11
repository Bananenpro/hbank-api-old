#!/bin/bash
cd ~/h-bank
./system/backup.sh
echo Updating...
git pull
echo Restarting...
sudo systemctl restart hbank.service
sudo systemctl restart hbank-backup.timer
sudo systemctl restart hbank-payment-plans.timer
echo Done.