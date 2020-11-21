#!/bin/bash
cd ~
sudo systemctl enable dhcpcd
sudo systemctl start dhcpcd
echo "interface wlan0" | sudo tee -a /etc/dhcpcd.conf > /dev/null
echo "static ip_address=192.168.0.200/24" | sudo tee -a /etc/dhcpcd.conf > /dev/null
echo "static routers=192.168.0.1" | sudo tee -a /etc/dhcpcd.conf > /dev/null
echo "static domain_name_servers=192.168.0.1" | sudo tee -a /etc/dhcpcd.conf > /dev/null
sudo raspi-config
sudo apt update && sudo apt upgrade
sudo apt install python3-pip rclone git vim
sudo reboot

