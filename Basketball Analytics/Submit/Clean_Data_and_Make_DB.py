"""
Python Script used to Read in original data files and store to .db file

Requires these files in working directory:
'NBA Hackathon - Event Codes.txt'
'NBA Hackathon - Game Lineup Data Sample (50 Games).txt'
'NBA Hackathon - Play by Play Data Sample (50 Games).txt'
"""

# Python 3.7
import sqlite3
import pandas as pd

db_name = 'analytics_track.db'
# Connect to db
connection = sqlite3.connect(db_name)
cursor = connection.cursor()

# Read in EVENT CODES file
df = pd.read_csv('data/NBA Hackathon - Event Codes.txt', delimiter='\t')
# Take care of strange NaN value on row index 146:
df.set_value(146, 'Action_Type_Description', 'No Shot')
# Remove extra spaces in last two columns:
df["Event_Msg_Type_Description"] = df["Event_Msg_Type_Description"].map(str.strip)
df["Action_Type_Description"] = df["Action_Type_Description"].map(str.strip)
# Save to DB file in 'event_codes' table:
df.to_sql('event_codes', connection, if_exists='replace')


# Read in Game Lineup File
df = pd.read_csv('data/NBA Hackathon - Game Lineup Data Sample (50 Games).txt', delimiter='\t')
# Save to DB file in 'game_lineup' table:
df.to_sql('game_lineup', connection, if_exists='replace')


# Read in Play by Play File
df = pd.read_csv('data/NBA Hackathon - Play by Play Data Sample (50 Games).txt', delimiter='\t')
# Save to DB
df.to_sql('play_by_play', connection, if_exists='replace')

print("Database saved as file:", db_name)