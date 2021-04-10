import sys

try:
	import launchpad_py as launchpad
except ImportError:
	try:
		import launchpad
	except ImportError:
		sys.exit("error loading launchpad.py")

import random
from pygame import time
import lichess.api as lichess

import asyncio
from lichess_client import APIClient

from config import lichessToken

import threading
import json

userName = 'pethor'
currentGameId =""
terminateAllThreads=False

# here are some animations
def animateGameStart(lp):
	lp.LedCtrlRaw(11, 0, 0, 63)
	lp.LedCtrlRaw(18, 0, 0, 63)
	lp.LedCtrlRaw(81, 0, 0, 63)
	lp.LedCtrlRaw(88, 0, 0, 63)
	
def animateGameStop(lp):
	lp.LedCtrlRaw(44, 0, 0, 63)
	lp.LedCtrlRaw(45, 0, 0, 63)
	lp.LedCtrlRaw(54, 0, 0, 63)
	lp.LedCtrlRaw(55, 0, 0, 63)	

def convertLetterToDigit(letter):
	if letter == 'a':
		return 1
	if letter == 'b':
		return 2
	if letter == 'c':
		return 3
	if letter == 'd':
		return 4
	if letter == 'e':
		return 5
	if letter == 'f':
		return 6
	if letter == 'g':
		return 7
	if letter == 'h':
		return 8
	return 9

def animateLastMove(lp, moves):
	# moves are in this format: d2d4 d7d5 c2c4 e7e6 b1c3 g8f6 c4d5
	moveTokens = moves.split()
	if len(moveTokens) > 0:
		lp.Reset()
		lastMove = moveTokens[-1]
		firstLetter = lastMove[0:1]
		firstDigit = lastMove[1:2]
		secondLetter = lastMove[2:3]
		secondDigit = lastMove[3:4]
		firstLetterAsDigit = convertLetterToDigit(firstLetter)
		secondLetterAsDigit = convertLetterToDigit(secondLetter)
		
		firstLed = 10 * int(firstDigit) + int(firstLetterAsDigit)
		lp.LedCtrlRaw(firstLed, 63, 63, 0)
		secondLed = 10 * int(secondDigit) + int(secondLetterAsDigit)
		lp.LedCtrlRaw(secondLed, 10, 10, 0)

async def asyncEventGet(lp):
	global currentGameId
	client = APIClient(token=lichessToken)
	async for response in client.boards.stream_incoming_events():
		
		jsonString = response.entity.content
		eventDict = json.loads(jsonString)
		type = eventDict["type"]
		if type == "gameStart":
			animateGameStart(lp)
			currentGameId = eventDict["game"]["id"]

		elif type == "gameFinish":
			animateGameStop(lp)
			currentGameId = ""
		print(response)
		print("type: ", type, " id: ", currentGameId)

async def asyncGameEventGet(lp):
	global currentGameId
	client = APIClient(token="***REMOVED***")
	while 1:
		# asking each half second for a game id seams to be good enough
		time.wait(500)
		if currentGameId != "":
			async for response in client.boards.stream_game_state(currentGameId):
				print(response)
				jsonString = response.entity.content
				eventDict = json.loads(jsonString)
				if "error" in eventDict:
					#reset game id in case of error and wait for next move
					currentGameId=""
				if "moves" in eventDict:
					moves = eventDict["moves"]
					animateLastMove(lp, moves)
					print("moves: ", moves)

def someLoop(lp):
	global terminateAllThreads

	rgbValue = 0
	step = 1
	while 1:
		if terminateAllThreads == True:
			return
		time.wait( 40 )
		lp.LedCtrlRaw(88, 0, 0, rgbValue)
		rgbValue += step
		if rgbValue == 63:
			step = -1
		if rgbValue == 0:
			step = 1


def connectToLaunchPad():
	connected = 0

	#launchpad.Launchpad().ListAll("Launch")
	
	if launchpad.LaunchpadMiniMk3().Check( 1 , "Mini MK3"):
		lp = launchpad.LaunchpadMiniMk3()
		if lp.Open( 1, "Mini MK3" ):
			print("Launchpad Mini Mk3 found")
			connected = 1

	if connected == 0:
		print("Did not find any Launchpads, meh...")
		return

	lp.LedCtrlString( "OK!", 0, 63, 0, -1, waitms = 30 )
	return lp

def lightRandomLed(lp):
	lp.LedCtrlRaw( random.randint(0,127), random.randint(0,63), random.randint(0,63), random.randint(0,63) )

def handleButtons(lp):
	while 1:
		time.wait( 20 )
		but = lp.ButtonStateRaw()

		if but != []:
			# bottom right: exit
			if but[0] == 19:
				break

			# user button: get rapid rating
			if but[0] == 98 and but[1] > 0:
				user = lichess.user(userName)
				rating = user['perfs']['rapid']['rating']
				lp.LedCtrlString("Rating: " + str(rating), 0, 63, 0, -1, waitms = 30 )

			# enable led green and log to output
			lp.LedCtrlRaw(but[0], 0, 63, 0)
			print(" button pressed: ", but )

def startEventLoop(lp):
	loop = asyncio.new_event_loop()
	loop.run_until_complete(asyncEventGet(lp))

def startGameEventLoop(lp):
	loop = asyncio.new_event_loop()
	loop.run_until_complete(asyncGameEventGet(lp))

def main():
	global terminateAllThreads

	# connect to launchpad
	lp = connectToLaunchPad()

	# Clear the buffer because the Launchpad remembers everything :-)
	lp.Reset()
	lp.ButtonFlush()

	t1 = threading.Thread(target=lambda: handleButtons(lp))
	t2 = threading.Thread(target=lambda: someLoop(lp))
	t3 = threading.Thread(target=lambda: startEventLoop(lp))
	t4 = threading.Thread(target=lambda: startGameEventLoop(lp))

	t1.start()
	t2.start()
	t3.start()
	t4.start()

	t1.join()
	terminateAllThreads = True
	t2.join()

	# now quit...
	time.wait( 100 ) # for terminating all threads (access to launchpads)
	lp.Reset() # turn all LEDs off
	lp.Close() # close the Launchpad (will quit with an error due to a PyGame bug)

	
if __name__ == '__main__':
	main()

