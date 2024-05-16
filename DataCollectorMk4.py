import copy
import json
import time
import unicodedata
import urllib.request

URL = "http://localhost:8111/hudmsg?lastEvt=0&lastDmg=0"  # url of all gamedata, ie the important stuffs
GameOnURL = "http://localhost:8111/map_info.json"  # url of info needed to determine if the current game is still active
winLossURL = "http://localhost:8111/mission.json"  # url of info needed to determine which team won.
HOME = "P1KE"  # supposed to be used in conjuction with winLoss to determine which team won, currently not in use
legalChars = "abcdefghijklmnopqrstuvwxyzAАBCDEFGHIJKLMNOPQRSТTUVWXYZ_1234567890()/-. 'Éòôéöüß"
tagchars = "abcdefghijklmnopqrstuvwxyzAАBCDEFGHIJKLMNOPQRSТTUVWXYZ_1234567890()/. 'Éòôéöüß"


class Log:
	def __init__(self, log, player1, player2):
		self.log = log
		self.player1: Player = player1
		self.player2: Player = player2
		self.damageCheck = False
	
	def __str__(self):
		return f"({self.log}, (p1: {self.player1}), (p2: {self.player2})"


class Player:
	def __init__(self, tag, name, vehicle):
		self.tag = tag
		self.name = name
		self.vehicle = vehicle
		self.kills = []
		self.dead = True
	
	def __str__(self):
		return f"{self.name}, {self.vehicle}, {self.tag}"
	
	def json(self):
		return {
			"name": self.name,
			"vehicle": self.vehicle,
			"tag": self.tag
		}
	
	def data(self):
		return self.name, self.vehicle, self.tag


class Battle:
	def __init__(self):
		self.logs: list[Log] = []
		self.team1: list[Player] = []
		self.team2: list[Player] = []
		self.Tags = [None, None]
		self.winLoss = [False, False]
		self.recordedKills = []
	
	'''
	the __str__ is supposed to be used with console to return a neatly formatted log of battle
	'''
	
	def __str__(self):
		func = lambda pos: max([len(str(x.data()[pos])) for x in [*self.team1, *self.team2]])
		temp = "survived", "died"
		t1 = '\n'.join([f"{str(player.name):{func(0)}} {temp[0] if player.dead else temp[1]:8}  |  Vehicle: "
		                f"{str(player.vehicle):{func(1)}} |  Kills:  {[x.data() for x in player.kills]}".replace("None",
		                                                                                                         "N/A ")
		                for player in self.team1])
		t2 = '\n'.join([f"{str(player.name):{func(0)}} {temp[0] if player.dead else temp[1]:8}  |  Vehicle: "
		                f"{str(player.vehicle):{func(1)}} |  Kills:  {[x.data() for x in player.kills]}".replace("None",
		                                                                                                         "N/A ")
		                for player in self.team2])
		
		return f"{self.Tags[0]}\n{t1}\n\n{self.Tags[1]}\n{t2}"
	
	'''
	currently not used by anything, dont know why this is still here
	'''
	
	def playerVehicle(self):
		func = lambda pos: max([len(str(x.data()[pos])) for x in [*self.team1, *self.team2]])
		t1 = '\n'.join([f"{str(player.name):{func(0)}}  |  Vehicle: "
		                f"{str(player.vehicle):{func(1)}}".replace("None", "N/A ") for player in self.team1])
		t2 = '\n'.join([f"{str(player.name):{func(0)}}  |  Vehicle: "
		                f"{str(player.vehicle):{func(1)}}".replace("None", "N/A ") for player in self.team2])
		return f"{self.Tags[0]}\n{t1}\n\n{self.Tags[1]}\n{t2}"
	
	@staticmethod
	def test(obj1, obj2):
		try:
			obj1.index(obj2)
			return True
		except ValueError:
			return False
	'''
	returns a data usable version of the battle in the JSON format
	currently in dictionary format, should update to return a json.
	'''
	def getJSON(self):
		players = [player.json() for player in [*self.team1, *self.team2]]
		teamName = [player["name"] for player in players]
		team1 = [player.json() for player in self.team1]
		team2 = [player.json() for player in self.team2]
		team1Name = [player.name for player in self.team1]
		team2Name = [player.name for player in self.team2]
		return {
			"players": players,
			"team1Data": {
				"tag": self.Tags[0],
				"players" : [{
					"player": index,
					"alive": player.dead,
					"kills": [teamName.index(p.name) if self.test(players, p.json()) else p.json() for p in player.kills]
				} for index, player in enumerate(self.team1)],
			},
			"team2Data": {
				"tag": self.Tags[1],
				"players" : [{
					"player": index,
					"alive": player.dead,
					"kills": [teamName.index(p.name) if self.test(players, p.json()) else p.json() for p in player.kills]
				} for index, player in enumerate(self.team2)],
			},
		}
	
	def logKills(self):
		used = [log for log in self.logs if not log.damageCheck]
		for log in used:
			if [log.player1, log.player2] in self.recordedKills:
				log.damageCheck = True
				continue
			if log.player2 is not None:
				if True in [x in log.log for x in [" shot down ", " destroyed ", "critically damaged"]]:
					if log.player2 not in log.player1.kills:
						self.setKillsDeaths(killer=log.player1, killed=log.player2)
					log.damageCheck = True
			elif True in [x in log.log for x in ["crashed", "wrecked"]]:
				log.player1.dead = False
				for log1 in [log for log in self.logs if not log.damageCheck]:
					if log1.player2 == log.player1:
						log1.player1.kills.append(log1.player2)
						log.damageCheck = True
					if log == log1:
						log.player1.kills.append(log.player1)
						log.damageCheck = True
	
	def setKillsDeaths(self, killer: Player = None, killed: Player = None):
		killed.dead = False
		if killer is not None:
			killer.kills.append(killed)
	
	# looks for player based on inputted information and returns player, if no matching player found, creates a player and returns them
	def playerSearch(self, tag, name, vehicle):
		if tag == "GH1234GH":
			return Player(tag, name, vehicle)
		# print(tag, name, vehicle)
		if len(tag) == 0 or len(name) == 0 or len(vehicle) == 0:
			return None
		# print(tag)
		# print(self.Tags, *tag, sep="|")
		# print(tag, name, vehicle)
		#print(self.team1, self.team2)
		team: list[Player] = [self.team1, self.team2][self.Tags.index(tag)]
		for player in team:
			if player.name == name and player.vehicle == vehicle:
				return player
		newPlayer = Player(tag, name, vehicle)
		if vehicle != "(Recon Micro)":
			team.append(newPlayer)
		return newPlayer
	
	# get tags from a log and also sets global logs
	def getTags(self, log):
		tags = [log[1:log.find(" ") - 1]]
		index = [x[0] + len(x[1]) for x in
		         [[log.find(i), i] for i in
		          [" shot down ", " damaged ", " destroyed ", "set afire ", " critically damaged "]] if x[0] != -1]
		if len(index) > 0 and "ai" not in log:
			tags.append(log[index[0] + 1:log[index[0]:].find(" ") + index[0] - 1])
		tags = [tag for tag in tags if 2 < len(tag) < 7]
		for t in tags:
			if None not in self.Tags:
				return [tag for tag in tags if tag is not None]
			if t not in self.Tags:
				self.Tags[self.Tags.index(None)] = t
		return [tag for tag in tags if tag is not None]
	
	def refinePlayer(self, unref):
		place = unref.find("(")
		front, back = unref[0:place - 1], unref[place:]
		ind1 = front.find(" ")
		dat = [front[0:ind1 - 1], front[ind1 + 1:], back.rstrip().lstrip()]
		return dat
	
	def end_finder(self, log, index):
		# print(" endinfder ", log, index, log[index])
		# print(log, index)
		if log[index] != " " and index < len(log) - 1:
			return self.end_finder(log, index + 1)
		# print(index)
		return index
	
	# first stage of processing, assigns metadata to logs and adds them to battle
	def setMetadata(self, unref):
		tags = self.getTags(unref)
		# print("first: ", unref)
		if "Recon Micro" in unref and "(Recon Micro)" not in unref:
			unref = unref.replace("Recon Micro", f"╀GH1234GH╀ LIGHT TANK (RECON MICRO)")
			tags.append("GH1234GH")
		# print(unref)
		place = self.end_finder(unref, unref.find(")"))
		# print("After: ", unref, place)
		splitPoint = unref[place:].find(tags[1]) + place if len(tags) == 2 else -1
		# print("sploitpoint: ", splitPoint, unref[splitPoint-1 : splitPoint+1])
		players: [Player] = []
		count = [0, 0]
		index = None
		for index1, letter in enumerate(unref[:splitPoint]):
			if letter == "(":
				count[0] += 1
			elif letter == ")":
				count[1] += 1
			if count[0] == count[1] and 0 not in count:
				index = index1 + 1
				break
		if index is None:
			print(unref[:splitPoint])
			players.append(self.refinePlayer(
				
				unref[unref.index(tags[0]): self.end_finder(unref, unref[:splitPoint].index(")"))]))
		else:
			players.append(self.refinePlayer(unref[unref.index(tags[0]):index]))
		if len(tags) == 2:
			players.append(self.refinePlayer(unref[splitPoint:]))
		payload = [None, None]
		if len(players) > 0:
			payload[0] = self.playerSearch(players[0][0], players[0][1], players[0][2])
		if len(players) == 2:
			payload[1] = self.playerSearch(players[1][0], players[1][1], players[1][2])
		log = Log(unref, payload[0], payload[1])
		self.logs.append(log)
		if payload[1] is not None and payload[1].tag == "NoneNone":
			self.setKillsDeaths(killer=payload[0], killed=payload[1])
		return log
	
	def update(self, log):
		self.setMetadata(log)
		self.logKills()
	
	'''
	def check(self):r
		for team in [self.team1, self.team2]:
			for i in range(1, len(team)):
				p = team[i-1]
				for player in team[i::]:
					if p.name == player.name:
	'''


if __name__ == "__main__":
	# print("weee")
	# with urllib.request.urlopen(URL) as f:
	with open("TestData\\Set30.json", "rb") as f:  # set 11
		json_info = json.loads(f.read().decode('utf-8'))['damage'][::-1]
		
		prev = json_info[0]
		data: [str] = []
		for i in json_info[1::]:
			if i['time'] <= prev['time']:
				data.insert(0, i['msg']) if "_DISCONNECT_" not in i['msg'] and "disconnected" not in i['msg'] else None
				prev = i
			else:
				break
	battle = Battle()
	for test in data:
		test = str(test)
		# print(battle)
		# print("test: ", test)
		# print("stuff")
		# print("Test: ", test)
		battle.update(unicodedata.normalize("NFC", test).replace("⋇ ", "^"))
	# print(json.dumps(battle.getJSON()))
	print(battle.__str__())
	with open("saveFile.json", "rb") as f:
		data: dict = json.load(f)
		data["battles"].append(battle.getJSON())
		print(data)
	with open("saveFile.json", "wb") as f:
		f.write(bytes(json.dumps(data).encode("utf-8")))
# set13, I should be dead. FIXED
# set17, ZSU should be dead
# set 18, M4a3e2 counted twice, one missing part of vehicle name. FIXED
# set19, counts 2 spacedog, one is drone. FIXED
# set20, counting tkx twice, one missing a parenthesis. FIXED
# set21, all should be dead
# set22, error invloving f-5c
# set27, missing one
'''
Set28
  File "C:\\Users\jgola\PycharmProjects\WarThunderBattleData\DataCollectorMk4.py", line 132, in playerSearch
    team: list[Player] = [self.team1, self.team2][self.Tags.index(tag)]
                                                  ^^^^^^^^^^^^^^^^^^^^
ValueError: 'eco' is not in list
'''
'''
Set29, problems regestering recon micro with no player owner
  File "C:\\Users\jgola\PycharmProjects\WarThunderBattleData\DataCollectorMk4.py", line 132, in playerSearch
    team: list[Player] = [self.team1, self.team2][self.Tags.index(tag)]
                                                  ^^^^^^^^^^^^^^^^^^^^
ValueError: 'eco' is not in list
'''
'''
set 30
  File "C:\\Users\jgola\PycharmProjects\WarThunderBattleData\DataCollectorMk4.py", line 191, in setMetadata
    count[1] +=1
    
IndexError: list index out of range
'''
# set 31, Clickbait sohuld be dead
# set 32, XXAndreBrXX should be dead
# set 33, play should be dead
# set 34, ASRAD should be dead
# set, 35 / 36, substring not found
