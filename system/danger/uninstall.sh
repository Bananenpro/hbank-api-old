#!/bin/bash
cd ~
echo Creating backup...
./h-bank/system/backup.sh
echo Stopping system services...
sudo systemctl stop hbank.service
sudo systemctl stop hbank-backup.timer
sudo systemctl stop hbank-payment-plans.timer
echo Disabling system services...
sudo systemctl disable hbank.service
sudo systemctl disable hbank-backup.timer
sudo systemctl disable hbank-payment-plans.timer
echo Uninstalling system services...
sudo rm /etc/systemd/system/hbank.service
sudo rm /etc/systemd/system/hbank-backup.timer
sudo rm /etc/systemd/system/hbank-backup.service
sudo rm /etc/systemd/system/hbank-payment-plans.timer
sudo rm /etc/systemd/system/hbank-payment-plans.service
echo Stopping rclone
killall rclone
crontab -r
rm -rf OneDrive
echo Uninstalling...
rm -rf h-bank
echo Done.