#!/usr/bin/env python
import praw
import json
import getpass
import requests
import argparse
from time import sleep
from datetime import datetime

#TO DO:
#argparse to allow automatic start
#bypass mechanism for argparse presence
#not as object

#If data is live game data json
#GAME ID: data['gameData']['game]['pk'] or data['gamePk']
#Game state (Preview/In Progess/Final): data['gameData']['status']['abstractGameState']
#AWAY TEAM data['gameData']['teams']['away']
#Name: data['gameData']['teams']['away']['name']
#Abbreviation: data['gameData']['teams']['away']['abbreviation']

#HOME TEAM data['gameData']['teams']['home']
#Name: data['gameData']['teams']['home']['name']
#Abbreviation: data['gameData']['teams']['home']['abbreviation']

#PLAYERS: data['gameData']['players'][<ID>]
#surname: data['gameData']['players'][<ID>]['lastName']
#id: data['gameData']['players'][<ID>]['id']
#full name: data['gamedata']['players'][<ID>]['fullName']
#position: data['gameData']['players'][<ID>]['primaryPosition']['abbreviation'] (D/RW/G/LW/C)
#type: data['gameData']['players'][<ID>]['primaryPosition']['type'] (Forward/Defenseman/Goalie)
#team: data['gameData']['players'][<ID>]['currentTeam'][tricode'] (e.g. 'NYI')
#teamname: data['gameData']['players'][<ID>]['currentTeam']['name'] (e.g. 'New York Islanders')

#Some basic game info
#Team: data['liveData']['linescore']['teams']['home'/'away']['team']['triCode'/'name']
#Shots: data['liveData']['linescore']['teams']['home'/'away']['shotsOnGoal']
#Goals: data['liveData']['linescore']['teams']['home'/'away']['goals']

#Game Plays
#data['liveData']['plays'].keys() -> ['penaltyPlays', 'allPlays', 'scoringPlays', 'currentPlay', 'playsByPeriod']
#data['liveData']['plays']['scoringPlays'/'penaltyPlays'] --> list of play indices
#data['liveData']['plays']['allPlays'] -> list of plays

#Goal:
#goal = data['liveData']['plays']['allPlays'][<INDEX>]
#Period: goal['about']['period']
#Time (since start of period): goal['about']['periodTime']
#Time Remaining: goal['about']['periodTimeRemaining']
#Game score: goal['about']['goals'] -> {'away': <score>, 'home': <score>}
#Goal scorer: goal['players'][<index>]['playerType'] == 'Scorer'
#Assist players: goal['players'][<index>]['playerType'] == 'Assist'
#Player name: goal['players'][<index>]['fullName']
#Goal type: goal['result']['secondaryType']
#strength: goal['result']['strength']['code']
#---
#Period - Time - Score (with team logos) - Description

#Penalty:
#penalty = data['liveData']['plays']['allPlays'][<INDEX>]
#Period: penalty['about']['period']
#Time (since start of period): penalty['about']['periodTime']
#Time Remaining: penalty['about']['periodTimeRemaining']
#Team: penalty['team']['triCode'/'name'] -- team taking penalty
#Players: penalty['players'][<INDEX>]['fullName']
#Penalized/Victim: penalty['players']['<INDEX>]['playerType'] --> 'PenaltyOn'||'DrewBy'
#Call: penalty['results']['secondaryType']
#Length: penalty['results']['penaltyMinutes']
#Severity: penalty['
#---
#Period - Time - Length (with shorthanded team logo) - Description

#Intermission:
#data['livedata']['linescore']['intermissionInfo']
#inIntermission (bool) : data['liveData']['linescore']['intermissionInfo']['inIntermission']
#time remaining: data['liveData']['linescore']['intermissionInfo']['intermissionTimeRemaining']
#Intermission - time remaining

#Game over when: data['liveData']['plays']['allPlays'][-1]['eventTypeId'] == 'GAME_END'


#Functions:
#(1) Login       - returns praw.Reddit object
#(2) Select game - returns game_id to construct tables in (5)
#(3) Find GDT    - uses praw.Reddit object, returns GDT post object
#(4) Pull post   - uses GDT post object, returns post text
#(5) Edit post   - uses results of (4) and (6), returns combination of the two
#(6) Build GDT tables - uses game_id, returns tables (as text)
#(7) Edit post   - what a dumb command, uses post object from (3)
#(8) Monitor game- uses URL to make sure game score isn't final.  If is, exits
#(9) Renew ticket- i don't know if i'm going to do this

teams = {'MIN': ['/r/wildhockey', 'Minnesota', 'Wild'], 'TOR': ['/r/leafs', 'Toronto', 'Leafs'], 'WSH': ['/r/caps', 'Washington', 'Capitals'], 'BOS': ['/r/bostonbruins', 'Boston', 'Bruins'], 'DET': ['/r/detroitredwings', 'Detroit', 'Red Wings'], 'NYI': ['/r/newyorkislanders', 'New York', 'Islanders'], 'FLA': ['/r/floridapanthers', 'Florida', 'Panthers'], 'COL': ['/r/coloradoavalanche', 'Colorado', 'Avalanche'], 'NSH': ['/r/predators', 'Nashville', 'Predators'], 'CHI': ['/r/hawks', 'Chicago', 'Blackhawks'], 'NJD': ['/r/devils', 'New Jersey', 'Devils'], 'DAL': ['/r/dallasstars', 'Dallas', 'Stars'], 'CGY': ['/r/calgaryflames', 'Calgary', 'Flames'], 'NYR': ['/r/rangers', 'New York', 'Rangers'], 'CAR': ['/r/canes', 'Carolina', 'Hurricanes'], 'WPG': ['/r/winnipegjets', 'Winnipeg', 'Jets'], 'BUF': ['/r/sabres', 'Buffalo', 'Sabres'], 'VAN': ['/r/canucks', 'Vancouver', 'Canucks'], 'STL': ['/r/stlouisblues', 'St Louis', 'Blues'], 'SJS': ['/r/sanjosesharks', 'San Jose', 'Sharks'], 'MTL': ['/r/habs', 'Montreal', 'Canadiens'], 'PHI': ['/r/flyers', 'Philadelphia', 'Flyers'], 'ANA': ['/r/anaheimducks', 'Anaheim', 'Ducks'], 'LAK': ['/r/losangeleskings', 'Los Angeles', 'Kings'], 'CBJ': ['/r/bluejackets', 'Columbus', 'Blue Jackets'], 'PIT': ['/r/penguins', 'Pittsburgh', 'Penguins'], 'EDM': ['/r/edmontonoilers', 'Edmonton', 'Oilers'], 'TBL': ['/r/tampabaylightning', 'Tampa Bay', 'Lightning'], 'ARI': ['/r/coyotes', 'Arizona', 'Coyotes'], 'OTT': ['/r/ottawasenators', 'Ottawa', 'Senators'], 'VGK':['/r/goldenknights', 'Vegas', 'Golden Knights']}

convert = {'San Jose Sharks': 'SJS', 'Detroit Red Wings': 'DET', 'Arizona Coyotes': 'ARI', 'Carolina Hurricanes': 'CAR', 'Toronto Maple Leafs': 'TOR', 'Boston Bruins': 'BOS', 'Florida Panthers': 'FLA', 'Columbus Blue Jackets': 'CBJ', 'Anaheim Ducks': 'ANA', 'Buffalo Sabres': 'BUF', 'Montreal Canadiens': 'MTL', 'Edmonton Oilers': 'EDM', 'Pittsburgh Penguins': 'PIT', 'New York Rangers': 'NYR', 'Washington Capitals': 'WSH', 'St Louis Blues': 'STL', 'Colorado Avalanche': 'COL', 'Minnesota Wild': 'MIN', 'Dallas Stars': 'DAL', 'Winnipeg Jets': 'WPG', 'New Jersey Devils': 'NJD', 'Tampa Bay Lightning': 'TBL', 'Los Angeles Kings': 'LAK', 'Calgary Flames': 'CGY', 'Chicago Blackhawks': 'CHI', 'New York Islanders': 'NYI', 'Nashville Predators': 'NSH', 'Ottawa Senators': 'OTT', 'Vancouver Canucks': 'VAN', 'Philadelphia Flyers': 'PHI', 'Vegas Golden Knights':'VGK'}

def main():
  parser = argparse.ArgumentParser( description='Inputs to bypass info-gathering scripts' )
  parser.add_argument( '--game_id', '-g', type=str, default=None, help='The game ID (the number input when selecting game)' )
  parser.add_argument( '--post_id', '-p', type=str, default=None, help='The GDT\'s post ID' )
  parser.add_argument( '--remaining', '-r', dest='remaining', action='store_true', default=False, help='Swap the time clock to time remaining in period' )
  args = parser.parse_args()
  
  reddit = login()
  
  if not args.game_id:
    [ game_id, home, away ] = select_game()
  else:
    game_id = args.game_id
    [ home, away ] = find_teams( game_id )

  url = 'https://statsapi.web.nhl.com/api/v1/game/'+str(game_id)+'/feed/live'

  if not args.post_id:
    gdt = find_gdt( reddit, home, away )
  else:
    gdt = reddit.submission( id = args.post_id )

  while True:
    post = pull_post( gdt )
    tables = build_tables( url, args.remaining )
    post = edit_post( post, tables )
    edit_gdt( gdt, post )
    monitor_game( url )
    sleep(30)
    

def login(  ): #Login to PRAW
  r = praw.Reddit( 'AUTHENTICATION' )
  #r = praw.Reddit( client_id='', client_secret='', user_agent='', username='', password='' )
  return r

def find_teams( game_id ):
  #If give game_id but not post ID, need home and away for post search
  import pytz
  from datetime import datetime

  pacific = pytz.timezone( 'US/Pacific' ) #Open page, get data
  today = datetime.now(pacific).strftime('%Y-%m-%d')
  url = 'https://statsapi.web.nhl.com/api/v1/schedule?startDate='+today+'&endDate='+today+'&expand=schedule.teams,schedule.linescore'
  page = requests.get( url )
  games = json.loads( page.content.decode('utf-8') )['dates'][0]['games']
  page.close()
  
  for game in games:
    if int(game['gamePk']) == int(game_id):
      home = game['teams']['home']['team']['abbreviation']
      away = game['teams']['away']['team']['abbreviation']
      return [ home, away ]
  print( 'No matching game tonight.  Please double check your game ID\nExiting . . .' )
  exit(1)

def select_game( ): #Look at today's NHL schedule, scrape games, offer options to user.  Couched in 'if not parser.game_id: game_id = select_game()'
  import pytz
  from datetime import datetime

  pacific = pytz.timezone( 'US/Pacific' ) #Open page, get data
  today = datetime.now(pacific).strftime('%Y-%m-%d')
  url = 'https://statsapi.web.nhl.com/api/v1/schedule?startDate='+today+'&endDate='+today+'&expand=schedule.teams,schedule.linescore'
  page = requests.get( url )
  data = json.loads( page.content.decode( 'utf-8' ) )['dates'][0]['games']
  page.close()

  games = {} #Parse data, pull game_id, teams, game state
  for x in data[:]:
    game_id = x['gamePk']
    games[game_id] = {'a':x['teams']['away']['team']['abbreviation'],'h':x['teams']['home']['team']['abbreviation'],'id':x['gamePk']}
    if x['linescore']['currentPeriod'] == 0:
      games[game_id]['time'] = 'Pre-game'
    elif x['linescore']['currentPeriodTimeRemaining'] == 'FINAL':
      games[game_id]['time'] = 'Finished'
    else:
      games[game_id]['time'] = x['linescore']['currentPeriodOrdinal']+' '+x['linescore']['currentPeriodTimeRemaining']

  for x in sorted(games.keys()): #Print data: GAME_ID AWAY at HOME - GAME_STATE
    print( '{0} {1} at {2} - {3}'.format(x,games[x]['a'],games[x]['h'],games[x]['time']) )

  #print(games)
  response = input('Please enter the number of the game you need: ') #Select GAME_ID
  valid = False
  while not valid:
    try:
      gameThread = games[int(response)]
    except Exception as e:
      response = input('Invalid input, please enter the number of the game you need: ')
    else:
      valid = True

  return [ response, games[int(response)]['h'], games[int(response)]['a'] ]

def find_gdt( reddit, away, home ): #Search for GDT or be given URL
  import pytz
  utc = pytz.timezone( 'UTC' )
  pacific = pytz.timezone( 'US/Pacific' )
  search = input( 'Have you already posted the GDT? (y/n) ' )
  if search.lower() == 'y':
    user = reddit.user.me()
    posts = [ x for x in user.submissions.new( limit = 50 ) ]
    game_check = []
    for post in posts:
      made = utc.localize( datetime.utcfromtimestamp(post.created) ).astimezone(pacific)
      if ( made.strftime('%d%m%Y')==datetime.now(pacific).strftime('%d%m%Y') ) and ( post.subreddit.url=='/r/hockey' ) and ( away in post.title ) and ( home in post.title ):
        game_check.append( post ) #Add post to list
    if len( game_check ) == 0:
      print( 'GDT not found' )    
      posted = input( 'What is the GDT URL? ' )
      try:
        submission = reddit.submission( url = posted )
      except praw.exceptions.ClientException as e:
        print( 'Invalid URL: Please post a GDT then rerun the script\n{}'.format(e) )
        exit( 1 )
      return submission
    elif len( game_check ) == 1:
      return game_check[0]
    else:
      for post in game_check:
        print( '{0} - {1}'.format( post.id, post.title ) )
      id_num = ( 'Please enter the ID of the correct post: ' )
      for post in game_check:
        if id_num == post.id:
          print( 'Post found.  Continuing.' )
          return post
        else:
          url = input( 'No matching post.  Please re-run the script or input a URL here: ' )
          try:
            submission = reddit.submission( url = posted )
          except praw.exceptions.ClientException as e:
            print( 'Invalid URL: Please post a GDT then rerun the script\n{}'.format(e) )
  else:
    posted = input( 'What is the GDT URL? ' )
    try:
      submission = reddit.submission( url = posted )
    except praw.exceptions.ClientException as e:
      print( 'Invalid URL: Please post a GDT then rerun the script\n{}'.format(e) )
      exit( 1 )
    return submission


def pull_post( post ):
  return post.selftext

def edit_post( post, tables ):
  print( 'Editing GDT text ...' )
  split = post.split('***')
  new_post = split[0] + '***\n' + tables + '\n' + '***\n' + split[2]
  return new_post

#Intermission:
#data['livedata']['linescore']['intermissionInfo']
#inIntermission (bool) : data['liveData']['linescore']['intermissionInfo']['inIntermission']
#time remaining: data['liveData']['linescore']['intermissionInfo']['intermissionTimeRemaining']
#Intermission - time remaining
def intermission( data ):
  if data['liveData']['linescore']['intermissionInfo']['inIntermission']:
    time_remaining = data['liveData']['linescore']['intermissionInfo']['intermissionTimeRemaining']
    seconds = 1.2 * time_remaining
    minutes = int(round(seconds/60, 0))
    residual = int(seconds) % 60
    time_left = str(minutes)+':'+str(residual)
    intermission_table = '|INTERMISSION|\n|:--:|\n|{}|'.format( time_left )
    return intermission_table
  else:
    return ''

def build_time_clock( data ):
  time_clock = '|Time Clock|\n|:--:|\n'
  period = data['liveData']['plays']['allPlays'][-1]['about']['ordinalNum']
  time = data['liveData']['plays']['allPlays'][-1]['about']['periodTime']
  if time == '20:00':
    time_clock += '|End {}|'.format( period )
  else:
    time_clock += '|{0} - {1}|'.format( period, time )
  return time_clock

def build_score_table( data ):
  goals_home = [ '-',0,0,0,0,0 ] #First entry is a dummy.  No 0th period in hockey
  goals_away = [ '-',0,0,0,0,0 ]
  periods = [ '1st', '2nd', '3rd', 'OT', 'SO' ]
  home = data['gameData']['teams']['home']['triCode']
  away = data['gameData']['teams']['away']['triCode']
  goals = data['liveData']['plays']['scoringPlays']
  period = 1
  home_total = 0
  away_total = 0
  for index in goals:
    goal = data['liveData']['plays']['allPlays'][index]
    team = goal['team']['triCode']
    period = goal['about']['period']
    home_total = goal['about']['goals']['home']
    away_total = goal['about']['goals']['away']
    if team == home:
      goals_home[ period ] += 1
    elif team == away:
      goals_away[ period ] += 1
    else:
      print( 'Somebody done fucked up' )
  header = 'Team |'
  line2 = ':--:|:--:|'
  home_scores = '[]({}) |'.format(teams[home][0])
  away_scores = '[]({}) |'.format(teams[away][0])
  for i in range( int(period) ):
    header += periods[i] + '|'
    line2 += ':--:|'
    home_scores += ' {} |'.format(goals_home[i+1])
    away_scores += ' {} |'.format(goals_away[i+1])
  header += 'Total'
  home_scores += str(home_total)
  away_scores += str(away_total) 
  table = header + '\n' + line2 + '\n' + home_scores + '\n' + away_scores + '\n'
  return table

def build_goals_table( data ):
  table = 'Period | Time | Team | Strength | Description\n:--:|:--:|:--:|:--:|:--:|\n'
  goals = data['liveData']['plays']['scoringPlays']
  line = ' {} | {} | {} | {} | {} \n'
  for index in goals:
    goal = data['liveData']['plays']['allPlays'][index]
    period = goal['about']['ordinalNum']
    time = goal['about']['periodTime']
    team = '[]({})'.format( teams[goal['team']['triCode']][0] )
    strength = goal['result']['strength']['name']
    description = goal['result']['description']
    table += line.format( period, time, team, strength, description )
  return table 

def build_penalty_table( data ):
  table = 'Period | Time | Team | Type | Min | Description\n:--:|:--:|:--:|:--:|:--:|:--:|\n'
  penalties = data['liveData']['plays']['penaltyPlays']
  line = ' {} | {} | {} | {} | {} | {} \n'
  for index in penalties:
    penalty = data['liveData']['plays']['allPlays'][index]
    period = penalty['about']['ordinalNum']
    time = penalty['about']['periodTime']
    team = '[]({})'.format( teams[penalty['team']['triCode']][0] )
    penalty_type = penalty['result']['penaltySeverity']
    penalty_min = str(penalty['result']['penaltyMinutes'])
    description = penalty['result']['description']
    table += line.format( period, time, team, penalty_type, penalty_min, description ) 
  return table

def build_time_table_elapsed( data ):
  last_play = data['liveData']['plays']['allPlays'][-1]
  period_ordinal = last_play['about']['ordinalNum']
  time_elapsed = last_play['about']['periodTime']
  table = '|Time Clock|\n|:--:|\n|{} - {}|\n'.format( period_ordinal, time_elapsed )
  if data['gameData']['status']['detailedState'] == 'Final':
    table = '|Time Clock|\n|:--:|\n|FINAL|\n'
  return table

def build_time_table_remaining( data ):
  last_play = data['liveData']['plays']['allPlays'][-1]
  period_ordinal = last_play['about']['ordinalNum']
  time_remaining = last_play['about']['periodTimeRemaining']
  table = '|Time Clock|\n|:--:|\n|{} - {}|\n'.format( period_ordinal, time_remaining )
  if data['gameData']['status']['detailedState'] == 'Final':
    table = '|Time Clock|\n|:--:|\n|FINAL|\n'
  return table

def build_tables( url, timeclock ):
  import requests
  import json

  page = requests.get( url )
  data = json.loads(page.content.decode('utf-8'))
  page.close()
  plays = data['liveData']['plays']['allPlays']
  tables = ''
  if len(plays) >= 0:
    print( 'Generating tables ... ' )
    score = build_score_table( data )
    penalties = build_penalty_table( data )
    if timeclock:
      time = build_time_table_remaining( data )
    else:
      time = build_time_table_elapsed( data )
    period_break = intermission( data ) 
    goal_data = build_goals_table( data )
    tables = '\n\n' + time + '\n\n' + score + '\n\n' + penalties + '\n\n' + goal_data
    if period_break != '':
      tables = period_break + '\n\n' + tables
  return tables

def edit_gdt( gdt, post ):
  print( 'Updating GDT ...\n' )
  gdt.edit( post )

def monitor_game( url ):
  import requests
  import json
  page = requests.get( url )
  data = json.loads( page.content.decode( 'utf-8' ) )
  page.close()
  
  if data['gameData']['status']['detailedState'] == 'Final':
    print( "This game has ended.  Exiting" )
    exit( 0 )

main()
