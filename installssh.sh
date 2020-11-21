#!/bin/bash
cd ~
git config --global credential.helper store
git clone https://gitlab.com/Bananenpro05/h-bank.git
cd h-bank
pip3 install Flask pony Pillow
sudo cp system/hbank.service /etc/systemd/system/
sudo systemctl enable hbank.service
sudo cp system/hbank-payment-plans.service /etc/systemd/system/
sudo cp system/hbank-payment-plans.timer /etc/systemd/system/
sudo systemctl enable hbank-payment-plans.timer
mkdir ~/OneDrive
rclone config
(crontab -l; echo "@reboot sleep 10 ; rclone --vfs-cache-mode writes mount onedrive: /home/pi/OneDrive";) | crontab -
sudo cp system/hbank-backup.service /etc/systemd/system/
sudo cp system/hbank-backup.timer /etc/systemd/system/
sudo systemctl enable hbank-backup.timer
sudo reboot