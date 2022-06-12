#!/usr/bin/python3

if True: #import modules, it's an "if" only to make it collapsable
	# import os
	# import time
	import pygame as pg
	import math # for the trigonometry functions for the course 

if True: #set parameters
	#screenW = int(2560)  # full screen is 2560 x 1080
	screenW = int(1920)
	screenH = int(1080)
	screenHorizon = screenH/2
	screenSize = (screenW, screenH)
	screenFieldOfView = 0.89 # 51 deg in radians, as per Mark's estimate of the screen at arms length
	bgColour = (20,33,50)
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
		self.EndShow = 0
		self.LastSteered = pg.time.get_ticks() - 10000000 # global time variable to track last steering event, used for msgbox re-hiding
		self.hide()

	def show(self, messageImage="", showDuration = 3000):
		if messageImage > "": 
			self.imageBase, self.rect = load_image(messageImage)
			self.image = self.imageBase.copy()
		
		# move onto screen
		###self.rect.centerx = pg.display.get_window_size()[0]/2
		self.rect.centerx = 2560/2
		self.EndShow = pg.time.get_ticks() + showDuration #time in ms
		# this can not take care of re-hiding because msgbox will only show 
		# at next update/draw; update must do the re-hiding
		
	def hide(self):
		# move off screen
		self.rect.left = screenW + 10

	def update(self):
		if self.EndShow > pg.time.get_ticks(): 
			# print("show time not passed yet: ES: ",self.EndShow, "   curr: ", pg.time.get_ticks())
			pass # if time hasn't elapsed keep showing msg
		
		else:
			# print("show time has passed-----------------------------")
			# print("LastSteered: ", self.LastSteered, "pgt-100: ", pg.time.get_ticks() - 100)
			if self.LastSteered > pg.time.get_ticks() - 100:   # if there is a recent steering event
				# print("steering input received, now hiding")
				self.hide()

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
		print ("distToCtr              : ", distance_to_channel_centre) 
		
		if crashed:
			# play sound
			pg.mixer.quit()
			pg.mixer.init()
			pg.mixer.music.load("audio/crash.mp3")
			pg.mixer.music.play()
			
			# rock platform (still need to set that up)
		
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
		self.zoomDistanceFactor =  .5		# fudge to zoom orig image size
		self.HorizonDropFactor = 1			# fudge to make island look like it starts out "at horizon"
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
				frameCount = 2, # should be 720, mem err if > 680 for 1920
				imgPath = "images/Background/IMG_2560x490/", # IMG_1920x490/", # "IMG_2560x490/"
				imgFilePrefix = "IMG_WAVE", 
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
		screen.blit(self.image_array[self.i], (0,540)) # should really be 590 but then there is a gap at the top, not sure what to make of that quite yet
		self.i = self.i + 1
		if self.i > self.frameCount-2: self.i = 0

def main():
	if True: # do one-time stuff
		# Initialize everything
		pg.init()
		screen = pg.display.set_mode(screenSize)
		pg.display.set_caption("Range Lights")
		pg.mouse.set_visible(0)

		# Create the backgound(s)
		background_bottom = pg.Surface((screenW, int(screenH/2)))
		background_bottom.fill(bgColour)
		background_bottom = background_bottom.convert()
		background_top, background_top_rect = load_image("images/Background/IMG_BACKGROUND.bmp")
		background_top.convert()
		Waves = backgroundVideo()
		
		# Put text on the background, centered
		if pg.font:
			font = pg.font.Font(None, 36)
			text = font.render("use left and right arrow to turn rudder indicator; ESC to quit", 1, (10, 10, 10))
			textpos = text.get_rect(centerx=screenW / 2)
			background_top.blit(text, textpos)

		# Prepare Game Objects
		clock = pg.time.Clock()
		HMS_Squirrel = Ship()
		farLight = RangeLight("images/RangeLights/IMG_LIGHT_FAR.png", 25, 0.2, -12, -50) # 0.008 good start angle)
		nearLight = RangeLight("images/RangeLights/IMG_LIGHT_NEAR.png", 20, 0.24, -10, -40) #0.05 good start)
		msgBox = MsgBox("images/Messages/Msg_Intro.png")
		rudderIndicator = RudderIndicator(0)
		allsprites = pg.sprite.RenderPlain((farLight, nearLight, rudderIndicator, msgBox))

	# Main Loop
	idling = False # True COMMENT OUT NEXT LINE WHEN SETTING TO TRUE
	steeringStart = pg.time.get_ticks() 
	quitting = False
	
	while not quitting:
		###clock.tick(maxFramerate)
		screen.blit(background_top, (0, 0))
		screen.blit(background_bottom, (0, screenH/2))
		Waves.update(screen)
		
		if idling:
			pg.time.delay(5000) # this allows the final message of the last run to 
								# remain visible for a time before showing intro
			msgBox.show("images/Messages/Msg_Intro.png", 0)
			
			# reset range lights and rudder
			farLight.reset()
			nearLight.reset()
			rudderIndicator.reset()
			HMS_Squirrel.reset()
			
			# check if idling should be over
			for event in pg.event.get():
				if event.type == pg.QUIT:
					quitting = True
				elif event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
					quitting = True
				elif event.type == pg.KEYDOWN: # left, right any key
					idling = False
					HMS_Squirrel.steeringStart = pg.time.get_ticks()
		
		else: # not idling
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
			
			print ("foo2") # without this the distToCtr never displays
			if HMS_Squirrel.outOfChannel(farLight, nearLight):
				# print("out of channel")
				msgBox.show("images/Messages/Msg_Crash.png")
				idling = True
			
			if HMS_Squirrel.completedPasseage():
				# print("completed passage")
				msgBox.show("images/Messages/Msg_Success.png")
				idling = True
			
		allsprites.update()
		allsprites.draw(screen)
		
		pg.display.flip() # this is a "go" nothing flips direction here... 

	pg.quit() # Game Over

if __name__ == "__main__": # this calls the 'main' function when this script is executed
	main()
