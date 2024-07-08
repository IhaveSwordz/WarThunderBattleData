import json
playz = {

}
with open("saveFile.json", "rb") as f:
	data: dict = json.load(f)['battles']
	for battle in data:
		players = battle["players"]
		for player in players:
			if playz.get(player["name"]) is None:
				playz.update({player["name"]: 1})
			else:
				playz[player["name"]] += 1
	print(playz)
