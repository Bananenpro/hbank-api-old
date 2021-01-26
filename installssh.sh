#!/bin/bash
cd ~
git config --global credential.helper store
echo Cloning git repo
git clone https://gitlab.com/Bananenpro05/h-bank.git
cd h-bank
echo Setting up directories...
mkdir app
mkdir app/android
echo "10" > app/android/version
echo "password" > password
echo "Please change the default password in '~/h-bank/password'"
echo Installing dependencies...
pip3 install Flask pony Pillow pytz waitress gpiozero psutil python-dateutil
echo Setting up system services...
sudo cp system/hbank.service /etc/systemd/system/
sudo systemctl enable hbank.service
sudo cp system/hbank-payment-plans.service /etc/systemd/system/
sudo cp system/hbank-payment-plans.timer /etc/systemd/system/
sudo systemctl enable hbank-payment-plans.timer
echo Configuring rclone
mkdir ~/OneDrive
rclone config
(crontab -l; echo "@reboot sleep 10 ; rclone --vfs-cache-mode writes mount onedrive: /home/pi/OneDrive";) | crontab -
echo Enabling H-Bank backup
sudo cp system/hbank-backup.service /etc/systemd/system/
sudo cp system/hbank-backup.timer /etc/systemd/system/
sudo systemctl enable hbank-backup.timer
echo Rebooting...
sudo reboot