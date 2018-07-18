"""
Game Simulator Class & Functions
Created by Berkeley Ballers Team for 2018 NBA Hackathon
School: UC Berkeley
##### GO BEARS! #####

- Game Class: Treats each game as an object. Tracks Plus/Minus data and events
- Game Simulator: Uses class to read in play by play events & execute Game methods
- Game to Table: Function that uses game object and outputs to Pandas table
- MAIN: runs the necessary logic to run simulation for all games & output CSV file.
"""
import sqlite3
import pandas as pd


# !! Must have analytics_track.db file in directory !!
connection = sqlite3.connect('analytics_track.db')
cursor = connection.cursor()

def run_query(qry):
    return pd.read_sql_query(qry, connection)


class Game:           
    # Initialize a new game object with: GameID, & TeamID's
    def __init__(self, game_id, team1_id, team2_id):
        self.game = game_id
        self.team1 = team1_id
        self.team2 = team2_id 
        self.team1_score = 0
        self.team2_score = 0

        # Dictionary with Player_id:Active Status
        self.team1_active = {}
        self.team2_active = {}

        # Dictionary with Player_id:Plus/Minus
        self.team1_pm = {}
        self.team2_pm = {}

    ### Update Plus/Minus stats and score:  ###
    
    def update_score(self, team_id, points):
        # Plus/Minus points relative to TEAM 1
        if team_id == self.team1:
            self.team1_score += points
            pm = points
        elif team_id == self.team2:
            self.team2_score += points
            pm = -points
            
        for player, active in self.team1_active.items():
            if active:
                try:
                    self.team1_pm[player] += pm
                except KeyError:
                    self.team1_pm[player] = pm

        for player, active in self.team2_active.items():
            if active:
                try:
                    self.team2_pm[player] -= pm
                except KeyError:
                    self.team2_pm[player] = -pm           

    ### Updating active players ###       
    
    def get_starter(self, team_id, period):
        ### Gets the starting 5 for each quarter, returns ITERABLE ###
        df = run_query("SELECT Person_id FROM game_lineup WHERE Game_id='{}' AND Team_id='{}' AND Period={}".format(self.game,team_id,period))
        return df.Person_id
    
    def start_period(self, period):
        tm1_starters = self.get_starter(self.team1, period)
        tm2_starters = self.get_starter(self.team2, period)
        for player in tm1_starters:
            self.team1_active[player] = True
        for player in tm2_starters:
            self.team2_active[player] = True
            
    def end_period(self):
        for player in self.team1_active:
            self.team1_active[player] = False
        for player in self.team2_active:
            self.team2_active[player] = False            
        
    def make_substitution(self,leaving, entering):
        """Changes the active state of the leaving and entering players.
        Checks the active players sets instead of TeamID provided because
        original dataset is inconsistent for that field."""
        if leaving in self.team1_active.keys():
            self.team1_active[leaving] = False
            self.team1_active[entering] = True
        elif leaving in self.team2_active.keys():
            self.team2_active[leaving] = False
            self.team2_active[entering] = True
        else:
            print('ERROR: Player', leaving, "not found on either team found.")


# SQL Query to get Play-by-Play for a specific Game_id
plays_query = """
SELECT Period, PC_Time, WC_Time, Event_Num, p.Event_Msg_Type, p.Action_Type, Event_Msg_Type_Description,
       Action_Type_Description, Option1, Option2, Team_id, Person1, Person2
FROM play_by_play p 
INNER JOIN event_codes e 
    ON p.Event_Msg_Type = e.Event_Msg_Type 
    AND p.Action_Type = e.Action_Type
WHERE p.Game_id = '{}'
ORDER BY Period asc, PC_Time desc, WC_Time asc, Event_Num asc;
"""


from collections import deque

def game_simulation(game_id):
    teams_list = run_query("SELECT distinct Team_id from game_lineup WHERE Game_id = '{}'".format(game_id)).Team_id
    game = Game(game_id, teams_list[0], teams_list[1])
    play_by_play = run_query(plays_query.format(game_id))
    
    # To keep track of fouls/and subs for special case:
    foul_state = False
    foul_time = 0
    sub_queue = deque([])
    
    for play in play_by_play.itertuples():
        event_type = play.Event_Msg_Type
                       
        if foul_state:
            if event_type not in [3,8,9] and play.PC_Time != foul_time:  # If action after foul is not a free throw or substitution
                while len(sub_queue) > 0:   # make the substitutions (after PM was updated)
                    sub = sub_queue.popleft()
                    game.make_substitution(sub[0], sub[1])
                foul_state = False
            elif event_type == 8:   # Substitution
                # Store sub that needs to be made in queue for after foul/freethrow sequence
                sub_queue.append((play.Person1, play.Person2))
                continue
                
        if event_type in [2, 4, 5, 7, 9, 10, 11]:
        # Ignore Missed Shot, Rebound, Turnover, Violation, Timeout, JumpBall
            continue  # exit this iteration of for-loop
            
        elif event_type == 12:  # Start Period
            game.start_period(play.Period)
            
        elif event_type == 13:  # End Period
            game.end_period()
            
        elif event_type == 1:  # Made Shot
            game.update_score(play.Team_id, play.Option1)
            
        elif event_type == 3:  # Free Throw
            if play.Option1 == 1:
                game.update_score(play.Team_id, play.Option1)

        elif event_type == 6:  # Foul
            foul_state = True
            foul_time = play.PC_Time

        elif event_type == 8:  # Substitution
            game.make_substitution(play.Person1, play.Person2)
            
    return game


def game_to_table(game):
    gid = game.game
    tm1 = pd.DataFrame([[gid, player, pm] for player,pm in game.team1_pm.items()], columns = ['Game_ID', 'Player_ID', 'Player_Plus/Minus'])
    tm2 = pd.DataFrame([[gid, player, pm] for player,pm in game.team2_pm.items()], columns = ['Game_ID', 'Player_ID', 'Player_Plus/Minus'])
    return pd.concat([tm1, tm2])


def main():
	game_ids = run_query('SELECT DISTINCT Game_id FROM game_lineup').Game_id
	output_table = pd.DataFrame()
	i = 1

	for gid in game_ids:
		print('Gettings stats for game', i)
		sim = game_simulation(gid)
		output_table = pd.concat([output_table,game_to_table(sim)])
		i += 1

	print('Saving results to CSV...')
	output_table.to_csv('Berkeley_Ballers_Q1_BBALL.csv', index=False)
	print('Done.')

main()