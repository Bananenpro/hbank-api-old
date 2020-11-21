#/bin/bash
cd ~
sudo apt update && sudo apt upgrade
sudo apt install python3-pip rclone
git clone https://gitlab.com/Bananenpro05/h-bank.git
cd h-bank
pip3 install Flask pony Pillow
sudo cp system/hbank.service /etc/systemd/system/hbank.service
sudo systemctl enable hbank.service
sudo cp system/hbank-payment-plans.service /etc/systemd/system/hbank-payment-plans.service
sudo cp system/hbank-payment-plans.timer /etc/systemd/system/hbank-payment-plans.timer
sudo systemctl enable hbank-payment-plans.timer
mkdir ~/OneDrive
rclone config
sudo cp system/onedrive.service /etc/systemd/system/onedrive.service
sudo systemctl enable onedrive.service
sudo reboot
