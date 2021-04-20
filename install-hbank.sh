#!/bin/bash
echo Installing updates...
sudo apt update && sudo apt upgrade
echo Installing system dependencies
sudo apt install python3-pip python3-dev python3-rpi.gpio rclone git vim htop libopenjp2-7 libtiff5
echo Copying data...
cp ./data/* ~/h-bank
cd ~/h-bank
touch password
echo "Please change the default password with 'python ~/h-bank/change_password.py [new_password]/"
touch parent_password
echo "Please change the default parent password with 'python ~/h-bank/change_parent_password.py [new_password]/"
echo Installing python dependencies...
pip3 install Flask pony Pillow pytz waitress gpiozero psutil python-dateutil
echo Setting up system services...
sudo echo "[Unit]
Description=The H-Bank Server
After=network.target

[Service]
ExecStart=/usr/bin/python3 -u main.py
WorkingDirectory=$HOME/h-bank
StandardOutput=inherit
StandardError=inherit
Restart=always
User=$USER

[Install]
WantedBy=multi-user.target" > /etc/systemd/system/hbank.service

sudo systemctl enable hbank.service

sudo echo "[Unit]
Description=H-Bank Payment Plans
After=network.target

[Service]
ExecStart=/usr/bin/python3 -u payment_plans.py
WorkingDirectory=$HOME/h-bank
StandardOutput=inherit
StandardError=inherit
User=$USER
Type=oneshot" > /etc/systemd/system/hbank-payment-plans.service

sudo mv system/hbank-payment-plans.timer /etc/systemd/system/
sudo systemctl enable hbank-payment-plans.timer

echo Configuring rclone
echo Choose the OneDrive option and name the remote \"onedrive\"
mkdir ~/OneDrive
rclone config
(crontab -l; echo "@reboot sleep 10 ; rclone --vfs-cache-mode writes mount onedrive: $HOME/OneDrive";) | crontab -
echo Enabling H-Bank backup
echo "#!/bin/bash
current_date=$(date +"%Y-%m-%d_%H-%M")
mkdir backup
mkdir backup/uploads
cp $HOME/h-bank/database.sqlite backup/
cp -r $HOME/h-bank/uploads/profile_pictures backup/uploads/
tar -czpf '$HOME/OneDrive/Backups/HBank/$current_date.tar.gz' backup
rm -rf backup" > system/backup.sh
chmod +x system/backup.sh

sudo echo "[Unit]
Description=H-Bank Backup
After=network.target

[Service]
ExecStart=$HOME/h-bank/system/backup.sh
WorkingDirectory=$HOME/h-bank
StandardOutput=inherit
StandardError=inherit
User=$USER
Type=oneshot
" > /etc/systemd/system/hbank-backup.service

sudo mv system/hbank-backup.timer /etc/systemd/system/
sudo systemctl enable hbank-backup.timer

echo Rebooting...
sudo reboot
