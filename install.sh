#!/bin/bash
echo Installing updates...
sudo apt update && sudo apt upgrade
echo Installing system dependencies
sudo apt install python3-pip python3-dev python3-rpi.gpio rclone git vim htop libopenjp2-7 libtiff5
cd ~
git config --global credential.helper store
git clone https://gitlab.com/Bananenpro05/h-bank.git
cd h-bank/
touch password
echo "Please change the default password with 'python ~/h-bank/change_password.py [new_password]/"
touch parent_password
echo "Please change the default parent password with 'python ~/h-bank/change_parent_password.py [new_password]/"
echo Installing python dependencies...
pip3 install Flask pony Pillow pytz waitress gpiozero psutil python-dateutil
echo Setting up system services...
echo "[Unit]
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
WantedBy=multi-user.target" > hbank.service
sudo mv hbank.service /etc/systemd/system/

sudo systemctl enable hbank.service

echo "[Unit]
Description=H-Bank Payment Plans
After=network.target

[Service]
ExecStart=/usr/bin/python3 -u payment_plans.py
WorkingDirectory=$HOME/h-bank
StandardOutput=inherit
StandardError=inherit
User=$USER
Type=oneshot" > hbank-payment-plans.service
sudo mv hbank-payment-plans.service /etc/systemd/system/

sudo mv system/hbank-payment-plans.timer /etc/systemd/system/
sudo systemctl enable hbank-payment-plans.timer

echo Configuring rclone
echo Choose the OneDrive option and name the remote \"onedrive\"
mkdir ~/OneDrive
rclone config
(crontab -l; echo "@reboot /bin/sleep 10 ; /usr/bin/rclone --vfs-cache-mode writes mount onedrive: $HOME/OneDrive";) | crontab -
echo Enabling H-Bank backup
echo "#!/bin/bash
current_date=\$(date +'%Y-%m-%d_%H-%M')
mkdir backup
mkdir backup/uploads
cp $HOME/h-bank/database.sqlite backup/
cp -r $HOME/h-bank/uploads/profile_pictures backup/uploads/
tar -czpf \"$HOME/OneDrive/Backups/HBank/\$current_date.tar.gz\" backup
rm -rf backup" > system/backup.sh

echo "[Unit]
Description=H-Bank Backup
After=network.target

[Service]
ExecStart=$HOME/h-bank/system/backup.sh
WorkingDirectory=$HOME/h-bank
StandardOutput=inherit
StandardError=inherit
User=$USER
Type=oneshot
" > hbank-backup.service
sudo mv hbank-backup.service /etc/systemd/system/

sudo mv system/hbank-backup.timer /etc/systemd/system/
sudo systemctl enable hbank-backup.timer

echo Configuring permissions...
chmod +x system/backup.sh
chmod +x system/restart.sh
chmod +x system/update.sh
chmod +x system/danger/reset.sh
chmod +x system/danger/uninstall.sh

echo Rebooting...
sudo reboot
