import json
import time
import urllib.request

URL = "http://localhost:8111/hudmsg?lastEvt=0&lastDmg=0"
GameOnURL = "http://localhost:8111/map_info.json"
winLossURL = "http://localhost:8111/mission.json"
HOME = "P1KE"
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
	
	def playerVehicle(self):
		func = lambda pos: max([len(str(x.data()[pos])) for x in [*self.team1, *self.team2]])
		t1 = '\n'.join([f"{str(player.name):{func(0)}}  |  Vehicle: "
		                f"{str(player.vehicle):{func(1)}}".replace("None", "N/A ") for player in self.team1])
		t2 = '\n'.join([f"{str(player.name):{func(0)}}  |  Vehicle: "
		                f"{str(player.vehicle):{func(1)}}".replace("None", "N/A ") for player in self.team2])
		return f"{self.Tags[0]}\n{t1}\n\n{self.Tags[1]}\n{t2}"
	
	def getJSON(self):
		return {
			"t1Tag": self.Tags[0],
			"t1Players": [x.name for x in self.team1],
			"t1Vehicles": [x.vehicle for x in self.team1],
			"t1Deaths": [[x.dead for x in self.team1]],
			"t1Kills": [[[x.kills for x in self.team1]]],
			"t1WinL": False,
			"t2Tag": self.Tags[1],
			"t2Players": [x.name for x in self.team2],
			"t2Vehicles": [x.vehicle for x in self.team2],
			"t2Deaths": [[x.dead for x in self.team2]],
			"t2Kills": [[[x.kills for x in self.team2]]],
			"t2WinL": False,
		}
	
	def logKills(self):
		used = [log for log in self.logs if not log.damageCheck]
		for log in used:
			if [log.player1, log.player2] in self.recordedKills:
				log.damageCheck = True
				continue
			if log.player2 is not None:
				if True in [x in log.log for x in [" shot down ", " destroyed "]]:
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
		print(tag, name, vehicle)
		if len(tag) == 0 or len(name) == 0 or len(vehicle) == 0:
			return None
		# print(tag)
		team: list[Player] = [self.team1, self.team2][self.Tags.index(tag)]
		for player in team:
			if player.name == name and player.vehicle == vehicle:
				return player
		newPlayer = Player(tag, name, vehicle)
		# print(newPlayer)
		if vehicle != "(Recon Micro)":
			team.append(newPlayer)
		return newPlayer
	
	# get tags from a log and also sets global logs
	def getTags(self, log):
		tags = [log[1:log.find(" ") - 1]]
		index = [x[0] + len(x[1]) for x in
		         [[log.find(i), i] for i in [" shot down ", " damaged ", " destroyed ", "set afire "]] if x[0] != -1]
		if len(index) > 0 and "ai" not in log:
			tags.append(log[index[0] + 1:log[index[0]:].find(" ") + index[0] - 1])
		# print(tags)
		tags = [tag for tag in tags if 2 < len(tag) < 7]
		for t in tags:
			if None not in self.Tags:
				return [tag for tag in tags if tag is not None]
			if t not in self.Tags:
				self.Tags[self.Tags.index(None)] = t
		return [tag for tag in tags if tag is not None]
	
	# refines a section a log to find the tag, the player name, and the player vehicle
	
	def refinePlayer(self, unref):
		# print(unref)
		# unref = ''.join(x for x in unref if x in legalChars)
		# print("refine player")
		# print(unref, unref.count("("), unref.count(")"))
		place = unref.find("(")
		front, back = unref[0:place - 1], unref[place:]
		ind1 = front.find(" ")
		dat = [front[0:ind1 - 1], front[ind1 + 1:], back]
		# count = -1 if dat[2].count(")") > dat[2].count("(") else None
		# if count is not None:
		# 	dat[2] = dat[2]
		return dat
	
	def end_finder(self, log, index):
		# print(log, index)
		if log[index] != " " and index < len(log) - 1:
			return self.end_finder(log, index + 1)
		return index
	
	# first stage of processing, assigns metadata to logs and adds them to battle
	def setMetadata(self, unref):
		tags = self.getTags(unref)
		# print("setmetadataTags: ", tags, unref)
		# print("setMetadata")
		place = self.end_finder(unref, unref.find(")"))
		splitPoint = unref[place:].find(tags[1]) + place if len(tags) == 2 else -1
		players = []
		
		# count = unref[:splitPoint].count("(") - 1
		count = [0, 0]
		index = None
		for index1, letter in enumerate(unref[:splitPoint]):
			# t = unref[:index1+2]
			if letter == "(":
				count[0] +=1
			elif letter == ")":
				count[1] +=1
			if count[0] == count[1] and 0 not in count:
				index = index1+1
				break
		if index is None:
			players.append(self.refinePlayer(
				unref[unref.index(tags[0]): self.end_finder(unref, unref[:splitPoint].index(")"))]))
		else:
			players.append(self.refinePlayer(unref[unref.index(tags[0]):index]))
		if len(tags) == 2:
			# count = unref[unref[splitPoint:].find(tags[1]) + splitPoint:].count("(") - 1
			players.append(self.refinePlayer(unref[splitPoint:]))
			# players.append(self.refinePlayer(unref[unref[splitPoint:].index(tags[1]) + splitPoint:
			#                                        unref[splitPoint:].find(")") + splitPoint+1]))
		# print("Players: ", players)
		payload = [None, None]
		if len(players) > 0:
			payload[0] = self.playerSearch(players[0][0], players[0][1], players[0][2])
		if len(players) == 2:
			payload[1] = self.playerSearch(players[1][0], players[1][1], players[1][2])
		log = Log(unref, payload[0], payload[1])
		# print(log)
		self.logs.append(log)
		return log
	
	def update(self, log):
		self.setMetadata(log)
		self.logKills()
	
	'''
	def check(self):
		for team in [self.team1, self.team2]:
			for i in range(1, len(team)):
				p = team[i-1]
				for player in team[i::]:
					if p.name == player.name:
	'''


# implement error check


if __name__ == "__main__":
	
	with urllib.request.urlopen(URL) as f:
	# with open("Set22.json", "rb") as f:  # set 11
		json_info = json.loads(f.read().decode('utf-8'))['damage'][::-1]
		
		prev = json_info[0]
		data = []
		for i in json_info[1::]:
			if i['time'] <= prev['time']:
				data.insert(0, i['msg']) if "_DISCONNECT_" not in i['msg'] and "disconnected" not in i['msg'] else None
				prev = i
			else:
				break
	# data = ["╊P1KE╋ zonedilluzionz (M4A3E2 (76) W) destroyed [AproX] Pot009 (Flakpanzer 341)"]
	battle = Battle()
	for test in data:
		# print(battle)
		# print("test: ", test)
		battle.update(test)
	print(battle)
	# print(battle.playerVehicle())
# set13, I should be dead. FIXED
# set17, ZSU should be dead
# set 18, M4a3e2 counted twice, one missing part of vehicle name. FIXED
# set19, counts 2 spacedog, one is drone. FIXED
# set20, counting tkx twice, one missing a parenthesis. FIXED
# set21, all should be dead
# set22, error invloving f-5c