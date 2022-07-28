#!/bin/bash

# This script should be run by a scheduled task at reboot through crontab. 
# To do this, run sudo crontab -e and add the following line to it
# @reboot ___________what does this need to be? ________________

echo "Range Light Simulator for Manitoba Marine Museum"
echo "by your friends at The Squirrel's Lair!"
echo "www.squirrelslair.ca"
echo
echo "If you intend to run an update, please insert the update USB stick"
echo "into one of the available USB ports on the small grey box behind the"
echo "display (Raspberry Pi) within the next 5 seconds."
echo
sleep 5s
echo "Attempting to mount update USB stick."

#commandLine=$(mount /dev/sda1 /home/pi/mnt)

mount /dev/sda1 /home/pi/mnt
if [ $? -eq  0 ]; then
	# If we're here, then the mount was successful, go ahead and
	# try to do the update
	echo "USB stick found, will attempt an update. Depending on the update,"
	echo "this can take up to 20 minutes to complete. The simulation will"
	echo "start automatically once the update is complete."
	/home/pi/mnt/SL_update.sh
	echo "Returned from update script, unmounting USB stick."
	umount /dev/sda1
	sleep 2s
	echo "You may now remove the USB stick at any time."
else
	echo "Error mounting USB stick, continuing with normal boot."
fi

echo "starting RangeLights simulation"
python3 /pi/home/RL/RangeLights_.py
