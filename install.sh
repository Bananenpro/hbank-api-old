#!/bin/bash
cd ~
echo Setting up the network...
sudo systemctl enable dhcpcd
sudo systemctl start dhcpcd
echo "interface wlan0" | sudo tee -a /etc/dhcpcd.conf > /dev/null
echo "static ip_address=192.168.0.200/24" | sudo tee -a /etc/dhcpcd.conf > /dev/null
echo "static routers=192.168.0.1" | sudo tee -a /etc/dhcpcd.conf > /dev/null
echo "static domain_name_servers=192.168.0.1" | sudo tee -a /etc/dhcpcd.conf > /dev/null
echo Starting raspi-config...
sudo raspi-config
echo Installing updates...
sudo apt update && sudo apt upgrade
echo Installing dependencies
sudo apt install python3-pip rclone git vim libopenjp2-7 libtiff5
echo Rebooting...
sudo reboot

