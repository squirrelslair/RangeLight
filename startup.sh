#!/bin/bash

# FOR UPDATES TO WORK, THE USB STICK MUST BE FORMATTED WITH EXFAT
# AND HAVE AN EXECUTABLE FILE CALLED SL_update.sh IN ITS ROOT DIRECTORY



echo "Range Light Simulator for Manitoba Marine Museum"
echo "by your friends at The Squirrel's Lair!"
echo "www.squirrelslair.ca"
echo
echo "If you intend to run an update, please insert the update USB stick"
echo "into one of the available USB ports on the small grey box behind the"
echo "display (Raspberry Pi) within the next 30 seconds."
echo
sleep 30s
echo "Attempting to mount update USB stick."



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

echo "starting the rangelights simulation next"
cd /home/pi/RL
python3 RangeLights_.py
