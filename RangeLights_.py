#!/usr/bin/python3

if True: #import modules, it's an "if" only to make it collapsable
	# import os
	# import time
	import pygame as pg
	import math # for the trigonometry functions for the course 
	import RPi.GPIO as GPIO # for the rumble platform
	import time# for the rumble platform

if True: #set parameters
	screenW = int(2560)  # full screen is 2560 x 1080
	#screenW = int(1920)
	screenH = int(1080)
	screenHorizon = 690  # horizon is a bit below centre and these are the numbers used in vid and bmp
	screenSize = (screenW, screenH)
	screenFieldOfView = 0.89 # 51 deg in radians, as per Mark's estimate of the screen at arms length
	bgColour = (20,33,50) # bottom background (not top)
	maxFramerate = 60 #60 for pi

if not pg.font:
	print("Warning, fonts disabled")

def load_image(name):
	try:
		image = pg.image.load(name).convert_alpha()
	except pg.error:
		print("Cannot load image:", name)
		raise SystemExit(str(geterror()))
	return image, image.get_rect()

class MsgBox(pg.sprite.Sprite): 
	def __init__(self,
				messageImage = "images/Messages/Msg_Blank1.png"):
		pg.sprite.DirtySprite.__init__(self)
		self.imageBase, self.rect = load_image(messageImage)
		self.image = self.imageBase.copy()
		self.EndShowAt = -1                                 # time when to stop showing
		self.showDuration = -1                              # duration for which to show
		self.LastSteered = pg.time.get_ticks() - 10000000   # global time variable to track last steering event, used for msgbox re-hiding
		self.hideMsg()
		self.showing = False                                # set indicator variable so external code can see if showing
		self.messageImage = messageImage                    # change indicator variable so external code can see what is showing
		
	def show(self, messageImage="", showDuration=3000):
		self.showing = True                                 # change indicator variable so external code can see if showing
		self.showDuration = showDuration
		self.messageImage = messageImage                    # change indicator variable so external code can see what is showing
		
		if messageImage > "": 
			self.imageBase, self.rect = load_image(messageImage)
			self.image = self.imageBase.copy()
			self.messageImage = messageImage
		
		self.rect.centerx = screenW/2                       # move onto screen
		
		if showDuration == -1:
			self.EndShowAt = -1
		else: 
			self.EndShowAt = pg.time.get_ticks() + showDuration #time in ms
		# this method can not take care of re-hiding because msgbox will only show 
		# at next update/draw; update method  must do the re-hiding
		
	def hideMsg(self):
		self.showing = False                                # change indicator variable so external code can see if showing
		self.rect.left = screenW + 10                       # move off screen
	
	def wait(self):           # wait until done; this would happen anyway, but having this allows to suspend game flow while waiting rather than keeping game flow going and eg crashing while msg is up      
		if self.showing: 
			pg.time.delay(self.showDuration) 
			pg.event.clear() # flush event cache so any twirling of the wheel during wait gets ignored
		
	def update(self):
		if self.EndShowAt > pg.time.get_ticks() or self.EndShowAt == -1 : 
			pass                                            # keep showing msg - time hasn't elapsed or ShowDuration is -1 ie forever
		else:
			self.hideMsg()

class RudderIndicator(pg.sprite.Sprite):
	def __init__(self,arrowAngle):
		pg.sprite.Sprite.__init__(self)  # call Sprite intializer
		
		# set parameters
		self.imageDir = "images/RudderIndicator/"
		
		# set initial values
		self.imageBase, self.rectBase = load_image(self.imageDir + "IMG_RUDDER_BASE.png")
		self.imageBase.convert_alpha()
		self.imageArrow, self.rectArrow = load_image(self.imageDir + "IMG_RUDDER_ARROW.png")
		self.imageArrow.convert_alpha()
		self.rect = self.rectBase

		self.reset() # set initial values

	def update(self):
		rotatedArrow = pg.transform.rotozoom(self.imageArrow, self.arrowAngle, 1)
		rotatedArrow_rect = rotatedArrow.get_rect()
		rotatedArrow_rect.center = (300,300) # provide center of rotation
		self.image = self.imageBase.copy()
		self.image.blit(rotatedArrow, rotatedArrow_rect)
		self.rect.midbottom = (screenW/2, screenH + 350) # last is a fudge factor because the image is a lot taller than needed for easy rotating of arrow
		
	def reset(self):
		self.arrowAngle = 0

class Ship:
	def __init__(self):
		# set parameters
		self.rudderPower = .0001	# .0001 OK fudge factor with which the rudder affects the bearing
		self.speed = .01		# 0.01 OK - fudge factor at which the distance changes
		self.maxRudder = 40
		self.angleIncrement = 1
		self.steeringTime = 38000 #  target duration in ms
		self.steeringStart = 0 # clock that will be used to keep track
		self.platform = rumbler() # initialize the platform

		self.reset() # set initial values

	def steerRight(self):
		#print("right")
		if self.rudderAngle > -self.maxRudder:
			#still possible to turn harder
			self.rudderAngle = self.rudderAngle - self.angleIncrement
			self.maxRightRudder = False
		else:
			self.maxRightRudder = True # the user of the object will need to deal with the problem

	def steerLeft(self):
		#print("left")
		if self.rudderAngle < self.maxRudder:
			#still possible to turn harder
			self.rudderAngle = self.rudderAngle + self.angleIncrement
			self.maxLeftRudder = False
		else:
			self.maxLeftRudder = True # the user of the object will need to deal with the problem

	def reset(self):
		self.rudderAngle = 0	# start w rudder centered
		self.bearing = 0		# it's a relative thing, just setting a starting value
		self.maxRightRudder = False
		self.maxLeftRudder = False

	def applySteering(self):
		self.bearing = self.bearing + (self.rudderAngle * self.rudderPower)

	def outOfChannel(self,farLight, nearLight):
		channelWidth = 5.08*2 # arbitrary, set based on the two rangelights; something to run into
		# lights are in line with centre of channel
		# we know distance to each light

		# we also know the angle from ships bearing to each light, so the difference is the and angle between them
		angle_between_lights = abs(farLight.angleFromBearing - nearLight.angleFromBearing)

		# that gives an SAS triangle, solve as per
		# https://en.wikipedia.org/wiki/Solution_of_triangles#Two_sides_and_the_included_angle_given_(SAS) 

		# use law of cosines to get distance between lights
		distance_between_lights = math.sqrt(farLight.distance ** 2 + nearLight.distance ** 2 - 2 * farLight.distance * nearLight.distance * math.cos(angle_between_lights))

		# get angle from far light between ship and channel
		arccos_parameter = (nearLight.distance ** 2 + distance_between_lights ** 2 - farLight.distance ** 2) / (2 * nearLight.distance * distance_between_lights)
		if arccos_parameter < -1: # cope with rounding errors that would make the parameter bad for acos()
			arccos_parameter = -1
		if arccos_parameter > 1: 
			arccos_parameter = 1
		#print("acosParam", arccos_parameter)
		angle_between_ship_and_channel = math.acos(arccos_parameter)
		
		# get distance to channel SOH
		distance_to_channel_centre = math.sin(angle_between_ship_and_channel) * farLight.distance
		
		# print("ANF: 	" + str(round(math.degrees(angle_between_lights), 0)) +
				 # "	DNL: 	" + str(round(nearLight.distance, 2)) +
				 # "	DFL: 	" + str(round(farLight.distance, 2)) +
				 # "	ASC:	" + str(round(math.degrees(angle_between_ship_and_channel), 0)) +
				 # "	DSC:	" + str(round(distance_to_channel_centre, 2)) +
				 # "	OOC:	" + str(distance_to_channel_centre > channelWidth/2) )
		crashed = abs(distance_to_channel_centre) > channelWidth/2
		print ("distToCtr			  : ", distance_to_channel_centre) 
		
		if crashed:
			# play sound
			pg.mixer.quit()
			pg.mixer.init()
			pg.mixer.music.load("audio/crash.mp3")
			pg.mixer.music.play()
			
			time.sleep(0.6)         # delay to get to the noisy part of the clip
			self.platform.crash()   # rock platform 
			
		return crashed

	def completedPasseage(self): 
		return pg.time.get_ticks() > self.steeringStart + self.steeringTime

class RangeLight(pg.sprite.Sprite):
	def __init__(self, 
				imagePath = "images/RangeLights/IMG_LIGHT_FAR.png", 
				initialDistance = 100, 
				initialAngle = 0, 
				sideOffset = 0, 
				heightOffset = 0): 
		pg.sprite.Sprite.__init__(self)  # call intializer of parent class
		
		# set parameters
		self.zoomDistanceFactor =  .3# .5		# fudge to zoom orig image size
		self.HorizonDropFactor = 1.2 # 1			# fudge to make island look like it starts out "at horizon"
		self.sideOffset = sideOffset		# fudge to compensate for tower not in centre of island/image
		self.heightOffset = heightOffset	# fudge to drop island/image reasonably to horizon
		
		#one-time image setup
		self.imageBase, self.rectBase = load_image(imagePath)
		self.imageBase.convert_alpha()
		self.rect = self.rectBase.copy()

		#set initial values
		self.initialDistance = initialDistance
		self.initialAngle = initialAngle
		self.reset()
		
		# draw initial image
		self.update()

	def update(self):
			zoomFactor = self.initialDistance/self.distance * self.zoomDistanceFactor 
			horizonDrop = self.heightOffset + self.distance * self.HorizonDropFactor # closer things are lower
			
			# x is relative to angleFromBearing
			# screenFieldOfView angle is equivalent to screenW
			# right is + angle, left is - angle
			deviation = screenW * (self.angleFromBearing/screenFieldOfView)
			
			x_Coordinate = screenW/2 +  (zoomFactor * (deviation + self.sideOffset)) 
			y_Coordinate = screenHorizon + horizonDrop
			w = self.rectBase.width * zoomFactor
			h = self.rectBase.height * zoomFactor
			
			self.image = pg.transform.rotozoom(self.imageBase.copy(), 0, zoomFactor) # change size of image
			#no rotation, but rotozom scales by single factor and smoothly, so using 
			
			self.rect.center = (x_Coordinate, y_Coordinate) # position
			self.rect.size = (w, h)

	def travelRelativeTo(self, speed, bearingChange): 
		self.angleFromBearing = self.angleFromBearing-bearingChange
		
		# get the distance to right-angle
		distanceRightAngle = math.cos(self.angleFromBearing) * self.distance
		
		#get opposite distance that won't change with travel
		distanceOpposite = math.sin(self.angleFromBearing) * self.distance
		
		# travel against distance to right-angle
		# !!! in theory we'd need to deal with what happens when we travel away.... it should not happen in our setting, there would have to be a u-turn in the channel and there is no space. 
		distanceRightAngle = distanceRightAngle - speed
		
		# update distance based on new distanceRightAngle and unchanged distanceOpposite
		self.distance = math.sqrt(math.pow(distanceRightAngle,2) + math.pow(distanceOpposite,2))
		
		# update angleFromBearing based on atan of ratio of adjacent vs opposite
		self.angleFromBearing = math.atan(distanceOpposite/distanceRightAngle)
	
	def reset(self): 
		self.distance = self.initialDistance
		self.angleFromBearing = self.initialAngle

class backgroundVideo: 
	def __init__(self, 
				frameCount = 10, #720, 
				
				imgPath = "images/Background/blenderWaves/",
				imgFilePrefix = "waves2_", 
				
				imgFilePostfix = ".bmp"): 

		self.image_array = []
		self.frameCount = frameCount

		for x in range (1, self.frameCount):
			img_name = imgPath + imgFilePrefix + str(x) + imgFilePostfix
			self.image_array.append(pg.image.load(img_name).convert())
			# print("Loaded %d of 720 objects  " %x)
		
		self.i = 0 # start iterator

	def update(self, screen):
		# print(str(self.i))
		screen.blit(self.image_array[self.i], (0,590)) # 07-23 were testing this with 540 before but there was a gap, this moves the gap to mid screen # should really be 590 but then there is a gap at the top, not sure what to make of that quite yet
		self.i = self.i + 1
		if self.i > self.frameCount-2: self.i = 0

class rumbler:
	def __init__(self):
		GPIO.setwarnings(False)
		GPIO.setmode(GPIO.BCM)
		GPIO.setup(23, GPIO.OUT)
		GPIO.output(23, GPIO.LOW) # Want this set low since it's the state when the Pi boots
		
	def test(self):
		countUp = 0
		while True:
			GPIO.output(23, GPIO.LOW)
			time.sleep(0.8) # OFF for 800ms
			GPIO.output(23, GPIO.HIGH)
			countUp = countUp + 1
			print(countUp) # print cycle count
			time.sleep(0.2) # ON for 200ms
			
	def crash(self): 
		self.decellerate(100, 60, 0.005)
		time.sleep(0.05)
		self.decellerate(80, 40, 0.008)
		time.sleep(0.1)
		self.decellerate(60, 15, 0.013)

	def decellerate(self, startDutyCycle=80, endDutyCycle=40, timeAtStep=0.005):
		#start sequence, run briefly at 100 duty cycle to start motor reliably
		pwm = GPIO.PWM(23, 100) # channel, frequency
		pwm.start(100)		  # start at 100% dutycycle, won't start w 50
		time.sleep(0.05)
		print("decellerate from ", startDutyCycle, " to ", endDutyCycle, " waiting at each level for ", timeAtStep)
		for x in range (startDutyCycle, endDutyCycle, -1):
			pwm.ChangeDutyCycle(x)
			time.sleep(timeAtStep)
			print(x)

def main():
	if True: # do one-time stuff
		# Initialize everything
		pg.init()
		screen = pg.display.set_mode(screenSize)
		pg.display.set_caption("Range Lights")
		pg.mouse.set_visible(0)
		
		# Create the backgound
		background_top, background_top_rect = load_image("images/Background/IMG_BACKGROUND2560x690.bmp")
		background_top.convert()
		
		Waves = backgroundVideo()
		
		# Prepare Game Objects
		clock = pg.time.Clock()
		HMS_Squirrel = Ship()
		farLight = RangeLight("images/RangeLights/IMG_LIGHT_FAR.png", 25, 0.2, -12, -145) # 0.008 good start angle)
		nearLight = RangeLight("images/RangeLights/IMG_LIGHT_NEAR.png", 20, 0.24, -10, -135) #0.05 good start)
		msgBox = MsgBox("images/Messages/Msg_Intro.png")
		rudderIndicator = RudderIndicator(0)
		allsprites = pg.sprite.RenderPlain((farLight, nearLight, rudderIndicator, msgBox))
		
		pg.event.clear() # flush event cache so any twirling of the wheel during load gets ignored
	
		# Main Loop
		idling = True # True COMMENT OUT NEXT LINE WHEN SETTING TO TRUE
		#steeringStart = pg.time.get_ticks() 
		quitting = False
	
	while not quitting:
		###clock.tick(maxFramerate)
		screen.blit(background_top, (0, 0))
		Waves.update(screen)
		
		if idling:
			if msgBox.showing == False: # rather than always showing, hopefully this is faster and delays the bg video less
				msgBox.show("images/Messages/Msg_Intro.png", -1)
			
			# check if idling should be over
			for event in pg.event.get():
				if event.type == pg.QUIT:
					quitting = True
				elif event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
					quitting = True
				elif event.type == pg.KEYDOWN: # left, right any key
					idling = False
					# reset range lights and rudder
					farLight.reset()
					nearLight.reset()
					rudderIndicator.reset()
					HMS_Squirrel.reset()
					HMS_Squirrel.steeringStart = pg.time.get_ticks()
					#pg.event.clear() # flush event cache so any twirling of the wheel during load gets ignored
		
		else: # not idling
			msgBox.hideMsg()
			
			# Handle Input Events
			for event in pg.event.get():
				if event.type == pg.QUIT:
					quitting = True
				elif event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
					quitting = True
				elif event.type == pg.KEYDOWN and (event.key == pg.K_RIGHT or event.key == pg.K_r):
					HMS_Squirrel.steerRight()
					msgBox.LastSteered = pg.time.get_ticks()
				elif event.type == pg.KEYDOWN and (event.key == pg.K_LEFT or event.key == pg.K_l):
					HMS_Squirrel.steerLeft()
					msgBox.LastSteered = pg.time.get_ticks()

			# process steering input
			if HMS_Squirrel.maxLeftRudder or HMS_Squirrel.maxRightRudder:
				print("Max Rudder happened, should probably yell at visitor to smarten up...")
			prevBearing = HMS_Squirrel.bearing # if we want to build in lag it would be a FIFO / iterator or similar of this value
			HMS_Squirrel.applySteering()
			rudderIndicator.arrowAngle = HMS_Squirrel.rudderAngle
			farLight.travelRelativeTo(HMS_Squirrel.speed, prevBearing-HMS_Squirrel.bearing)
			nearLight.travelRelativeTo(HMS_Squirrel.speed, prevBearing-HMS_Squirrel.bearing)
			
			if HMS_Squirrel.outOfChannel(farLight, nearLight):
				msgBox.show("images/Messages/Msg_Crash.png", 4000)
				farLight.reset()
				nearLight.reset()
				rudderIndicator.reset()
				HMS_Squirrel.reset()
				idling = True
			
			if HMS_Squirrel.completedPasseage():
				msgBox.show("images/Messages/Msg_Success.png", 4000)
				farLight.reset()
				nearLight.reset()
				rudderIndicator.reset()
				HMS_Squirrel.reset()
				idling = True
			
		allsprites.update()
		allsprites.draw(screen)
		pg.display.flip() # this is a "go" nothing flips direction here... 
		
		msgBox.wait()     # do any delaying required for msgboxes after they have been drawn
		
	pg.quit() # Game Over

if __name__ == "__main__": # this calls the 'main' function when this script is executed
	main()
