#!/bin/bash
cd ~
sudo systemctl stop hbank.service
sudo systemctl stop hbank-backup.timer
sudo systemctl stop hbank-payment-plans.timer
sudo systemctl disable hbank.service
sudo systemctl disable hbank-backup.timer
sudo systemctl disable hbank-payment-plans.timer
sudo rm /etc/systemd/system/hbank.service
sudo rm /etc/systemd/system/hbank-backup.timer
sudo rm /etc/systemd/system/hbank-backup.service
sudo rm /etc/systemd/system/hbank-payment-plans.timer
sudo rm /etc/systemd/system/hbank-payment-plans.service
killall rclone
crontab -r
rm -rf OneDrive
rm -rf h-bank