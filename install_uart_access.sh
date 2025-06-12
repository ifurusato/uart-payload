#!/bin/bash
#
# this is used if your pi user doesn't have the necessary permissions to gain
# access to the /dev/serial0 device.

USER_NAME=$(whoami)

echo "Adding user '$USER_NAME' to dialout and tty groups..."
sudo usermod -a -G dialout "$USER_NAME"
sudo usermod -a -G tty "$USER_NAME"

UDEV_RULE_FILE="/etc/udev/rules.d/99-serial.rules"

echo "Creating udev rule to set permissions on /dev/ttyS0..."
sudo bash -c "cat > $UDEV_RULE_FILE" << EOF
# Set group tty and permissions 660 for /dev/ttyS0
KERNEL==\"ttyS0\", GROUP=\"tty\", MODE=\"0660\"
EOF

echo "Reloading udev rules..."
sudo udevadm control --reload-rules
sudo udevadm trigger

echo "Temporarily setting permissions on /dev/ttyS0 for this session..."
sudo chmod 660 /dev/ttyS0

echo "Setup complete!"
echo "Please reboot your system or log out and log back in for changes to take effect."
echo "After that, you should be able to run your UART program without sudo."

#EOF
