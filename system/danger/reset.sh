#!/bin/bash
cd ~/h-bank
sudo systemctl stop hbank.service
sudo systemctl stop hbank-backup.timer
sudo systemctl stop hbank-payment-plans.timer
rm database.sqlite
cp uploads/profile_pictures/empty.png uploads/
rm uploads/profile_pictures/*
cp uploads/empty.png uploads/profile_pictures/
sudo systemctl start hbank.service
sudo systemctl start hbank-backup.timer
sudo systemctl start hbank-payment-plans.timer