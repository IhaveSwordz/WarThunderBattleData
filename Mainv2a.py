import copy
import json
import time
import urllib.request
import unicodedata
from DataCollectorMk4 import Battle

URL = "http://localhost:8111/hudmsg?lastEvt=0&lastDmg=0"
GameOnURL = "http://localhost:8111/map_info.json"
winLossURL = "http://localhost:8111/mission.json"
timeout = 10
saveFile = "battles.json"


class Main:
	def __init__(self):
		self.Battle = Battle()
	
	def updateBattle(self, logs):
		for log in logs:
			self.Battle.update(log)
	
	def logFile(self):
		print("logfile called")
		print(self.Battle.getJSON())
		if self.Battle.getJSON()['players'] == []:
			print("logfile aborted")
			return
		with open("saveFile.json", "rb") as f:
			data: dict = json.load(f)
			data["battles"].append(self.Battle.getJSON())
		with open("saveFile.json", "wb") as f:
			f.write(bytes(json.dumps(data).encode("utf-8")))
		self.Battle = Battle()
	
	@staticmethod
	def GetGameData():
		with urllib.request.urlopen(URL) as f:
			json_info = json.loads(f.read().decode('utf-8'))['damage'][::-1]
			data = [dat for dat in json_info if "_DISCONNECT_" not in dat['msg'] and "disconnected" not in dat['msg']]
			return data[:100]
	
	@staticmethod
	def getGameState():
		with urllib.request.urlopen(GameOnURL) as f:
			dat = json.loads(f.read().decode('utf-8'))
			# print(dat['valid'])
			return dat['valid'] is not False
	
	def reset(self):
		self.logFile()
		print("------------------------------------------------------")
		print("BATTLE END")
		print("------------------------------------------------------")
	
	def getData(self, data):
		prev = data[0]
		for i in data[1::]:
			if i['time'] <= prev['time']:
				prev = i
				self.Battle.update(unicodedata.normalize("NFC", i['msg']).replace("⋇ ", "^"))
			else:
				break
		print(self.Battle)
	
	
	def mainLoop(self):
		recent = 0
		gameInSession = True
		count = timeout.__int__()
		collected = []
		while True:
			if gameInSession:
				data = self.GetGameData()
				# print(self.getGameState(), 11111111111111, gameInSession)
				if not self.getGameState():
					# print(count)
					if count > 0:
						# print(count)
						count -= 1
					else:
						gameInSession = False
						count = timeout.__int__()
						self.reset()
						continue
				# print(data)
				if recent <= data[0]['time']:
					recent = data[0]['time']
				else:
					
					gameInSession = False
					recent = data[0]['time']
					count = timeout.__int__()
					self.reset()
					continue
				prev = data[0]
				updated = False
				for i in data[1::]:
					if i['time'] <= prev['time'] and i['msg'] not in collected:
						collected.append(i['msg'])
						prev = i
						updated = True
					else:
						break
				# self.Battle = Battle()
				if updated:
					self.getData(data)
			else:
				if Main.getGameState():
					gameInSession = True


b = Main()
b.mainLoop()
# print(len(stuff))
# print(stuff)