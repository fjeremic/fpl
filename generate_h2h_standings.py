import itertools
import json
import os
import requests

def generate_standings(file, players, gameweeks, gameweek_range):
    """Generates the FPL quarter standings in ``file`` for a given ``gameweek_range``.
    Information for the ``players`` and ``gameweeks`` are gathered from:
        https://fantasy.premierleague.com/api/leagues-h2h/{:d}/standings
        https://fantasy.premierleague.com/api/leagues-h2h-matches/league/{:d}/?page={{:d}}
    respectively.
    """
    standings = []
    for player in players:        
        # Initialize the standings where each player is first. We'll fix this after we parse the gameweeks.
        #
        #                 No.   Team    (id)             (team name)           (player name)      Wins   Draws   Losses   Points   FPL Points
        standings.append([1,    [player["entry"], player["entry_name"], player["player_name"]],   0,     0,      0,       0,       0         ])

    # Parse all wins, draws, losses, and total points, then calculate the points at each iteration
    for gameweek in gameweeks[gameweek_range[0] : gameweek_range[1] + 1]:
        for fixture in gameweek:
            entry_1 = next((x for x in standings if x[1][0] == fixture["entry_1_entry"]), None)
            entry_2 = next((x for x in standings if x[1][0] == fixture["entry_2_entry"]), None)

            if not entry_1 or not entry_2:
                raise RuntimeError("Could not extract entires!")
            
            # Append wins
            entry_1[2] +=  fixture["entry_1_win"]
            entry_2[2] +=  fixture["entry_2_win"]

            # Append draws
            entry_1[3] +=  fixture["entry_1_draw"]
            entry_2[3] +=  fixture["entry_2_draw"]

            # Append losses
            entry_1[4] +=  fixture["entry_1_loss"]
            entry_2[4] +=  fixture["entry_2_loss"]

            # Calculate points based off wins and draws
            entry_1[5] =  entry_1[2] * 3 + entry_1[3]
            entry_2[5] =  entry_2[2] * 3 + entry_2[3]

            # Append FPL points
            entry_1[6] +=  fixture["entry_1_points"]
            entry_2[6] +=  fixture["entry_2_points"]

    # Sort the standings first by points then by FPL points
    standings.sort(key = lambda x: (x[5], x[6]), reverse = True)

    # Now that we are sorted update the true ranking in order
    for i in range(len(standings)):
        standings[i][0] = i + 1

    with open(file, "w", encoding = "utf-8") as outfile:
        standings_dict = {
            "data": standings
        }

        json.dump(standings_dict, outfile, ensure_ascii = False)

session = requests.Session()
        
response = session.post("https://users.premierleague.com/accounts/login/", data = {
    "login": os.environ["FPL_USERNAME"],
    "password": os.environ["FPL_PASSWORD"],
    "app": "plfpl-web",
    "redirect_uri": "https://fantasy.premierleague.com/"
})

if "Incorrect email or password" in response.text:
    raise RuntimeError("Incorrect username or password!")

data = session.get("https://fantasy.premierleague.com/api/leagues-h2h/{}/standings".format(os.environ["FPL_LEAGUE_ID"])).json()

# Parse all the players
players = []
for player in data["standings"]["results"]:
    players.append(player)

# Parse all the gameweeks (login required) using the number of players
fixtures = []
fixtures_url = "https://fantasy.premierleague.com/api/leagues-h2h-matches/league/{}/?page={{:d}}".format(os.environ["FPL_LEAGUE_ID"])

for page in itertools.count(1):
    page_data = session.get(fixtures_url.format(page)).json()["results"]

    if page_data:
        fixtures.extend(page_data)
    else:
        break

if len(fixtures) != 38 * (len(players) // 2):
    raise RuntimeError("Invalid number of fixtures ({:d}) parsed for ({:d}) number of players".format (len(fixtures), len(players)))

gameweeks = []
for i in range(38):
    gameweeks.append(fixtures[i * (len(players) // 2) : (i + 1) * (len(players) // 2)])

generate_standings("q1.json", players, gameweeks, (0, 9))
generate_standings("q2.json", players, gameweeks, (10, 18))
generate_standings("q3.json", players, gameweeks, (19, 28))
generate_standings("q4.json", players, gameweeks, (29, 37))
