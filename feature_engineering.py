from numpy import mean, std
import csv
import math
import copy
from bisect import bisect_left as bisect
from collections import defaultdict
from datetime import date, datetime

def type_fix(df):
    """
    fix the types of the columns
    """
    for r in df:
        r['date'] = datetime.strptime(r['date'],'%m/%d/%Y').date()
        r['number_of_game'] = int(r['number_of_game'])
        r['visiting_team_game_number'] = int(r['visiting_team_game_number'])
        r['home_team_game_number'] = int(r['home_team_game_number'])
        r['visiting_team_runs'] = int(r['visiting_team_runs'])
        r['home_team_runs'] = int(r['home_team_runs'])
        r['visiting_team_hits'] = int(r['visiting_team_hits'])
        r['visiting_team_home_runs'] = int(r['visiting_team_home_runs'])
        r['home_team_hits'] = int(r['home_team_hits'])
        r['home_team_home_runs'] = int(r['home_team_home_runs'])
        
def fix_team_names(df):
    """
    for teams that have changed names at some point
    """
    teams = {'FLO':'MIA', 'CAL':'ANA'}
    for r in df:
        for team in ['home_team', 'visiting_team']:
            r[team] = teams.get(r[team], r[team])

def divisions(df):
    """
    add team's division to dataset from external integration.
    teams compete to be the team with the most wins in their deivision in order to reach playoffs
    """
    divisions = {}
    with open("divisions.csv", encoding='utf-8-sig') as fp:
        reader = csv.DictReader(fp)
        for r in reader:
            divisions[int(r['season']), r['team']] = r['division']

    for r in df:
        for team in ['visiting_team', 'home_team']:
            r[team+'_division'] = divisions[r['season'], r[team]]

def loss_count(df):
    current_count = defaultdict(int)# holds the metric count per team / season up until a given point in time

    for r in df:
        r['winning_team'] = r['home_team'] if r['home_team_runs'] > r['visiting_team_runs'] else r['visiting_team'] # team with the most runs in the winner
        for team in ('home_team', 'visiting_team'):
            # enter value into dataset before computing the new value given this game's outcome
            r['{}_loss_count'.format(team)] = current_count[r['season'], r[team]]

            if r['winning_team'] != r[team]:
                current_count[r['season'], r[team]] += 1 #team lost, increment loss counter
                
def park_capacity(df):
    """
    add official park capacity from external integration
    note: attendance can sometimes be higher than the park capacity (added standing room for instance)
    """
    park_capacities = {}
    with open("park_capacities.csv", encoding='utf-8-sig') as fp:
        reader = csv.DictReader(fp)
        for r in reader:
            park_capacities[int(r['season']), r['park_id']] = r['park_capacity']

    for r in df:
        r['park_capacity'] = park_capacities[r['season'], r['park_id']]

# @hidden_cell

def normalize(pop, val, cache=None,key=None):
    if val is None:
        return 0
    if cache is not None:
        if key not in cache:
            cache[key] = mean(pop), std(pop)
        m,s = cache[key]
    else:
        m,s = mean(pop), std(pop)
    return (val - m)/s if s else 0

def streaks(df):
    """
    calculate winning/losing streak. How many games in a row has the team won / lost up until the current game.
    """
    current_streak = defaultdict(int) # holds the streak per team up until a given point in time
    for r in df:
        for team in ('home_team', 'visiting_team'):
            # enter value into dataset before computing the new value given this game's outcome
            r[team+'_streak'] = current_streak[r['season'], r[team]]

            if r['winning_team']==r[team]:# team won
                if current_streak[r['season'],r[team]] > 0: # team is on a winning streak, increment it
                    current_streak[r['season'], r[team]]+=1
                else:
                    current_streak[r['season'], r[team]]=1 # team was on a losing streak, nullify it
            else: # team lost
                if current_streak[r['season'], r[team]] < 0: # team is on a losing streak, increment it
                    current_streak[r['season'], r[team]] -= 1
                else:
                    current_streak[r['season'], r[team]] = -1 # team was on a winning streak, nullify it

def cumulative_metric(df,metric):
    current_count = defaultdict(int) # holds the metric count per team / season up until a given point in time
    norm = defaultdict(list) # all values to be used to normalize the feature

    for r in df:
        for team in ('home_team', 'visiting_team'):
            # enter value into dataset before computing the new value given this game's outcome
            r['cumulative_{}_{}'.format(team,metric)] = current_count[r['season'], r[team]]

            norm[r['season'], r[team+'_game_number']].append(current_count[r['season'], r[team]])
            current_count[r['season'], r[team]] += r['_'.join([team,metric])]

    norm_cache = {}
    for r in df:
        for team in ('home_team', 'visiting_team'):
            if r[team+'_game_number'] > 10: # don't calculate this field if there haven't been enough games played this season. not enough data
                pop = norm[r['season'], r[team+'_game_number']] #population to normalize against
                r['cumulative_{}_{}_normalized'.format(team, metric)] = normalize(pop,r['cumulative_{}_{}'.format(team,metric)], norm_cache, (r['season'], r[team+'_game_number']))
            else:
                r['cumulative_{}_{}_normalized'.format(team, metric)] = 0
                
def intradivision(df):
    """
    1 if both game was between two teams from the same division and league, 0 otherwise.
    Teams in the same division compete with each other for a single playoff berth, but also play far
    more games between one another
    """
    for r in df:
        r['is_intradivision'] = r['visiting_team_league']==r['home_team_league'] and \
            r['visiting_team_division']==r['home_team_division']
        
def interleague(df):
    """
    1 if the game is between teams from opposite divisions.
    These games are more rare and thus fans tend to find them moree interesting
    """
    for r in df:
        r['interleague'] = r['visiting_team_league'] != r['home_team_league']
        
def holiday(df):
    """
    1 if Opening Day (first home game of the year), July 4th (in US), Labor Day, Memorial Day, Canada day (in Canada)
    """
    holidays = set()
    with open("holidays.csv", encoding='utf-8-sig') as fp:
        reader = csv.DictReader(fp)
        for r in reader:
            dt = datetime.strptime(r['date'], '%m/%d/%Y').date()
            holidays.add((dt, r['home_team']))

    for r in df:
        r['holiday'] = (r['date'], r['home_team']) in holidays
        
def rivalry(df):
    """
    1 if the game is between local/historic rivals.
    For instance 2 teams from the same city or the famous New York Yankees vs Boston Red Sox
    get from external integration.
    """
    rivalries = set()
    with open("rivalries.csv", encoding='utf-8-sig') as fp:
        reader = csv.DictReader(fp)
        for r in reader:
            rivalries.add((r['visiting_team'], r['home_team']))

    for r in df:
        r['rivalry'] = ((r['visiting_team'], r['home_team'])) in rivalries

def get_condition_score(conditions, percip):
    """
    condition_score = 0 -> best conditions
    high condition_score -> bad conditions
    """

    if conditions == 'in dome': # dome = controlled climate
        return 0

    percip_score = {
        'no precipitation': 0,
        'drizzle': 3,
        'showers': 4,
        'rain': 5,
        'snow': 7
    }
    condition_score = {
        'night': 0,
        'sunny': 0,
        'cloudy': 1,
        'overcast': 1,
    }

    if percip not in ('null', 'unknown'):
        if percip_score[percip] > 0: # if there was percipitation, decide condition score based on that
            return percip_score[percip]

    if conditions not in ('null', 'unknown'): # no/unknown percipitation, use condition data instead
        return condition_score[conditions]
    else:
        return None # no data exists

def month(date):
    # almost no games in mar or oct. estimate using apr / sep respectively
    if date.month == 3:
        return 4
    if date.month == 10:
        return 9
    return date.month

defaults = { #domed stadiums. if the conditions are missing, default to 0.
    ('MIA02', 'wind'): 0,
    ('STP01', 'wind'): 0,
    ('PHO01', 'oondition_score'): 0,
    ('HOU02', 'oondition_score'): 0,
    ('HOU03', 'oondition_score'): 0,
    ('MIA02', 'oondition_score'): 0,
    ('MON02', 'oondition_score'): 0,
    ('SEA02', 'oondition_score'): 0,
    ('SEA03', 'oondition_score'): 0,
    ('TOR02', 'oondition_score'): 0,
    ('STP01', 'oondition_score'): 0,
    ('MIN04', 'oondition_score'): 0,
}

def weather(df):
    """
    weather exxternal integration.
    temp: temprature (F) at the start of the game in the stadium. If the stadium is domed, use indoor temrature
    wind: wind speed (mph) at the start of the game in the stadium. If the stadium is domed wind=0
    condition_score: enumeration of weather condition. no clouds/in dome=0, cloudy/overcast=1, rain=3-5,snow/hail=7
    """
    weather_data = {} # to hold weather data per game
    norm = defaultdict(list) # use means (per team, month) for missing values
    with open("weather.csv") as fp:
        reader = csv.DictReader(fp)
        for r in reader:
            dt = datetime.strptime(r['date'],'%m/%d/%Y').date()
            condition_score = get_condition_score(r['conditions'], r['percip'])

            #convert data from strings
            r['temp'] = int(r['temp']) if r['temp'] != 'null' else None
            r['wind_speed'] = int(r['wind_speed']) if r['wind_speed'] != 'null' else None

            weather_data[dt, r['home']] = {'temp': r['temp'],
                                                  'wind': r['wind_speed'],
                                                  'condition_score': condition_score}
            if r['temp'] is not None:
                norm['temp', month(dt), r['home']].append(r['temp'])
                norm['temp'].append(r['temp'])
            if r['wind_speed'] is not None:
                norm['wind', month(dt), r['home']].append(r['wind_speed'])
                norm['wind'].append(r['wind_speed'])
            if condition_score is not None:
                norm['condition_score', month(dt), r['home']].append(condition_score)
                norm['condition_score'].append(condition_score)

    for r in df:
        for metric in ['temp', 'wind', 'condition_score']:
            """
            get weather data from:
             - actual value from weather data if it exists there, or
             - default value if this is a domed stadium, or
             - average weather metric for that city/month if there are more than 4 entries to  compute the sum with, or
             - overall average weather metric (treatment for missing value)
            """
            r[metric] = weather_data[r['date'], r['home_team']][metric] or \
                        defaults.get((metric, r['park_id'])) or \
                        (mean(norm[metric, month(r['date']), r['home_team']])
                         if len(norm[metric, month(r['date']), r['home_team']]) > 4
                         else mean(norm[metric]))

teams = {
'arizona_diamondbacks':'ARI',
'montreal_expos':'MON',
'florida_marlins':'MIA',
'anaheim_angels':'ANA',
'california_angels':'ANA',
'st._louis_cardinals':'SLN',
'tampa_bay_rays':'TBA',
'tampa_bay_devil_rays':'TBA',
'los_angeles_angels_of_anaheim':'ANA',
'baltimore_orioles':'BAL',
'boston_red_sox':'BOS',
'cincinnati_reds':'CIN',
'houston_astros':'HOU',
'los_angeles_dodgers':'LAN',
'milwaukee_brewers':'MIL',
'minnesota_twins':'MIN',
'new_york_mets':'NYN',
'oakland_athletics':'OAK',
'texas_rangers':'TEX',
'washington_nationals':'WAS',
'chicago_white_sox':'CHA',
'los_angeles_angels':'ANA',
'colorado_rockies':'COL',
'detroit_tigers':'DET',
'philadelphia_phillies':'PHI',
'pittsburgh_pirates':'PIT',
'san_diego_padres':'SDN',
'chicago_cubs':'CHN',
'kansas_city_royals':'KCA',
'new_york_yankees':'NYA',
'seattle_mariners':'SEA',
'san_francisco_giants':'SFN',
'cleveland_indians':'CLE',
'miami_marlins':'MIA',
'toronto_blue_jays':'TOR',
'atlanta_braves':'ATL',

}

player_outliers = {
    'rob macko':'rob mackowiak',
    'fausto carmona':'roberto hernandez',
    'tim vanegmond':'tim van egmond',
    'leo nunez':'juan carlos oviedo'
}

def get_stats(player_data,date,vis_team,home_team,player,pos):
    """
    find player stats in player stat data structure
    """
    date = str(date)
    try:
        return player_data[(date, vis_team, home_team,pos)][player]
    except KeyError: # player name does not exist in integration data
        try:
            if player in player_outliers: # some players have completely different names in the integration data
                return player_data[(date, vis_team, home_team,pos)][player_outliers[player]]
            return player_data[(date, vis_team, home_team,pos)][player.split(' ')[-1]] #try using only last name
        except KeyError:
            #print("{dt},{vs}-{home}: unable to locate {pl}".format(dt=date, vs=vis_team, home=home_team,pl=player))
            return [None]*4 # player is missing

def player_stats(df):
    """
    integrate player offensive/defensive stats. calculate and normalize max, avergae stats per team.
    slg: season start-to-date Slugging percentage of the offensive players in the lineup. A popular in-game metric
        for assesing an offensive player's run contribution.
    ops: season start-to-date On-Base Percentage + Slugging percentage of the offensive players in the lineup.
        A popular in-game metric for assesing an offensive player's overall offensive quality.
    wpa: season start-to-date Win Probability Added of the starting pitcher.
        A complex in-game metric for assesing how much the pitcher helped/ruined the team's chance of winning a game.
    era: season start-to-date Earned Run Average of the starting pitcher.
        A popular in-game metric for assesing the quality of a pitcher.
    """
    skip_header=True
    player_data = defaultdict(dict)
    with open("game_ranks.csv") as fp:
        reader = csv.reader(fp)
        for row in reader:
            if skip_header:
                skip_header = False
            else:
                date, vis_team, home_team, player_id, player_name, slg, ops, era, wpa, is_pitcher,yy = row
                slg = float(slg) if slg != '' else None
                ops = float(ops) if ops != '' else None
                era = float(era) if era != '' else None
                wpa = float(wpa) if wpa != '' else None
                player_name=' '.join(player_name.split('_'))
                player_last_name = player_name.split(' ')[-1]
                player_data[(date,teams[vis_team],teams[home_team],is_pitcher)][player_name] = [slg, ops, era, wpa]
                player_data[(date, teams[vis_team], teams[home_team],is_pitcher)][player_last_name] = [slg, ops, era, wpa]

    games = defaultdict(dict)
    norm = defaultdict(list)

    for r in df:
        for team in ['visiting', 'home']:
            if int(r['number_of_game']) < 2:

                date = r['date']
                pitcher = r[team+'_pitcher_name'].lower()
                players = [r[team+'_player{}_name'.format(i)].lower() for i in range(1,10)]

                games[(date, r[team+'_team'])]['pitcher'] = get_stats(player_data,date,r['visiting_team'],r['home_team'],pitcher,'1')
                games[(date, r[team+'_team'])]['positions'] = [get_stats(player_data,date,r['visiting_team'],r['home_team'],pl,'0') for pl in players]
                try:
                    pitcher = games[(date,r[team+'_team'])]['pitcher']
                    if pitcher[2]: norm['era',r['season']].append(pitcher[2])
                    if pitcher[3]: norm['wpa',r['season']].append(pitcher[3])
                except:
                    print((date,r[team+'_team'],'pitcher'))
                try:
                    pos = games[(date, r[team + '_team'])]['positions']
                    norm['slg',r['season']].extend([pos[p][0] for p in range(9) if pos[p] and pos[p][0]])
                    norm['ops',r['season']].extend([pos[p][1] for p in range(9) if pos[p] and pos[p][1]])
                except:
                    print((date, r[team + '_team'], 'positions'))
    norm_cache = {}
    for i,r in enumerate(df):
        for team in ['home_team', 'visiting_team']:
            if int(r[team+'_game_number']) > 10:
                players = games[r['date'], r[team]]

                r[team+'_starter_era_normalized'] = normalize(norm['era',r['season']], players['pitcher'][2], norm_cache, ('era',r['season']))
                r[team+'_starter_wpa_normalized'] = normalize(norm['wpa',r['season']], players['pitcher'][3], norm_cache, ('wpa',r['season']))

                normalized_ops = [normalize(norm['ops', r['season']], p[1], norm_cache, ('ops', r['season'])) for p in players['positions'] if p]
                normalized_slg = [normalize(norm['slg', r['season']], p[0], norm_cache, ('slg', r['season'])) for p in players['positions'] if p]
                try:
                    r[team+'_max_slg_normalized'] = max(normalized_slg)
                except ValueError:
                    r[team + '_max_slg_normalized'] = 0
                try:
                    r[team + '_max_ops_normalized'] = max(normalized_ops)
                except ValueError:
                    r[team + '_max_ops_normalized'] = 0
                try:
                    r[team + '_avg_slg_normalized'] = mean(normalized_slg)
                except ValueError:
                    r[team + '_avg_slg_normalized'] = 0
                try:
                    r[team + '_avg_ops_normalized'] = mean(normalized_ops)
                except ValueError:
                    r[team + '_avg_ops_normalized'] = 0
            else:
                r[team + '_max_slg_normalized'] = 0
                r[team + '_max_ops_normalized'] = 0
                r[team + '_avg_slg_normalized'] = 0
                r[team + '_avg_ops_normalized'] = 0
                r[team + '_starter_era_normalized'] = 0
                r[team + '_starter_wpa_normalized'] = 0


def salary(df):
    """
    average player yearly salary for each player in the starting lineup.
    Player salaries are an indicator for how much an organization expects for a player to drive revenues - a part of which are generated from attendance
    """
    salaries = {}
    salaries_by_last_name = defaultdict(dict)
    norm = defaultdict(list)
    with open("salaries_integration.csv", encoding='utf-8-sig') as fp:
        reader = csv.DictReader(fp)
        for r in reader:
            salary = int(r['salary'])
            player = player_outliers.get(r['player'], r['player'])
            salaries[r['season'], r['team'], player] = salary
            salaries_by_last_name[int(r['season']), r['team'], player.split()[-1]] = salary
            norm[int(r['season'])].append(salary)

    def find_player_salary(record, team, player):
        return salaries.get((record['season'], record[team+'_team'], player.lower()),
                      salaries_by_last_name.get((record['season'], record[team+'_team'], player.lower().split()[-1]),0))
    norm_cache = {}
    for r in df:
        for team in ('home', 'visiting'):
            starting_pitcher_salary = find_player_salary(r, team, r['{}_pitcher_name'.format(team)])
            lineup_salaries = []
            for i in range(1,10):
                player = r['{}_player{}_name'.format(team, i)]
                sal = find_player_salary(r, team, player)
                if sal:
                    normalized_salary = normalize(norm[r['season']],sal, norm_cache, r['season'])
                    lineup_salaries.append(normalized_salary)

            r[team + '_max_salary_normalized'] = max(lineup_salaries)
            r[team + '_avg_salary_normalized'] = mean(lineup_salaries)
            if starting_pitcher_salary:
                normalized_starting_pitcher_salary = normalize(norm[r['season']],starting_pitcher_salary, norm_cache, r['season'])
                r[team+'_starter_salary_normalized'] = normalized_starting_pitcher_salary
            else:
                r[team+'_starter_salary_normalized'] = 0
                

def standings(df):
    """
    calculate metrics related to the team's standing in the division bracket.
    games_behind: difference in number of losses between a given team and the first place team in its division.
        This represents how far a team is behind in the ranks, and how likely it is for a team to make the playoffs.
        If the team is in first place, games behind is the difference in the number of losses between the team and the second place team (a negative number)
    rank_in_division: team's rank (1st/2nd,3rd...) in its division prior to the game.
        At the end of the season, only the 1st team in the division goes to the playoffs
    """
    gr = defaultdict(dict) # hold number of games remaining in the season for each team by division, date
    divisions_loss_count = defaultdict(dict) # hold loss count for each team by division, date
    pct = defaultdict(dict) # hold win percentage (wins/games played) for each team by division, date
    current_standings = defaultdict(dict)
    current_pct = defaultdict(dict)
    current_gr = defaultdict(dict)

    dt = None
    season = None
    for r in df:
        if r['date'] != dt:
            # hold snapshot of standings for each day
            divisions_loss_count[dt] = copy.deepcopy(current_standings)
            pct[dt] = copy.deepcopy(current_pct)
            gr[dt] = copy.deepcopy(current_gr)

        if season != r['season']:
            # nullify standings for a new season
            current_standings = defaultdict(dict)
            current_pct = defaultdict(dict)
            current_gr = defaultdict(dict)

        dt = r['date']
        season = r['season']

        for team in ['visiting_team', 'home_team']:
            if int(r['number_of_game']) < 2:
                div = r[team+'_league'],r[team+'_division']
                # update current pcts
                current_pct[div][r[team]] = 1-round(r[team+'_loss_count']*1.0/(r[team+'_game_number']-1) if r[team+'_game_number'] > 1 else 0.5,3)
                #update current standings
                current_standings[div][r[team]] = r[team+'_loss_count']

            # update current games remaining
            current_gr[r[team]] = 163 - int(r[team+'_game_number'])

    divisions_loss_count[dt] = copy.deepcopy(current_standings)
    gr[dt] = copy.deepcopy(current_gr)
    pct[dt] = copy.deepcopy(current_pct)

    gr_by_rank = {} # to hold lists of grs for each team, division, date sorted by team rank
    pct_by_rank = {} # to hold lists of pcts for each team, division, date sorted by team rank
    for dt, std in divisions_loss_count.items():
        for div, losses in std.items():
            ls = list(losses.items())
            ls.sort(key=lambda x:x[1]) # sorted list of (team,loss counts) in a division
            gr_by_rank[(dt,)+div] = [gr[dt][x[0]] for x in ls]
            pct_by_rank[(dt,)+div] = [pct[dt][div][x[0]] for x in ls]

    # enter metrics into dataset
    for r in df:
        for team in ['home_team', 'visiting_team']:
            div_loss_vals = list(
                divisions_loss_count[r['date']][r[team + '_league'], r[team + '_division']].values())
            div_loss_vals.sort() # sorted list of loss counts in this teams division

            # if this is a doubleheader, use loss count from before game 1
            loss_cnt = r[team + '_loss_count']-1 if r['number_of_game'] == 2 and r[team + '_loss_count'] not in div_loss_vals else r[team + '_loss_count']
            rank = bisect(div_loss_vals, loss_cnt) + 1 # locate the team's loss count within the list of sorted loss counts. its index in the list (+1) is its rank

            try:
                gb = loss_cnt - div_loss_vals[0 if rank > 1 else 1] # games behind = loss count - contender loss count
            except IndexError:
                gb = 0
            r[team + '_rank_in_division'] = rank
            r[team + '_games_behind'] = gb

            # contender stats to be used to calculate contention score
            # contender = first place team if the current team is not in first place.
            # contender = second place team otherwise
            contender_rank = 0 if rank > 1 or len(pct_by_rank[r['date'], r[team+'_league'], r[team+'_division']])==1 else 1
            r[team + '_contender_pct'] = pct_by_rank[r['date'], r[team+'_league'], r[team+'_division']][contender_rank]
            r[team + '_contender_games_remaining'] = gr_by_rank[r['date'], r[team+'_league'], r[team+'_division']][contender_rank]

bin_gt_cache = {}

def nCr(n,r):
    f = math.factorial
    if n<r:
        return 0
    return f(n) / f(r) / f(n-r)

def bin(n,p,k):
    return nCr(n,k)*p**k*(1-p)**(n-k)

def bin_gt(n,p,k):
    # to save time return obvious results..
    if k==0:
        return 1
    if k>n:
        return 0
    if (n,p,k) not in bin_gt_cache:
        bin_gt_cache[n, p, k] = sum(bin(n,p,i) for i in range(k,n+1))
    return bin_gt_cache[n, p, k]

def contention_score(df):
    """
    calculate probability of reaching the playoffs given the teams rank in the division,
    current win record and number of games left to the season.
    """
    for r in df:
        for team in ['home_team', 'visiting_team']:
            if r[team+'_game_number'] <= 10: # not enough games played in the season. default to 0.5
                r[team + '_contention_score'] = 0.5
            else:
                pct = 1-round(r[team+'_loss_count']*1.0/(r[team+'_game_number']-1) if r[team+'_game_number'] > 1 else 0.5,3)
                gr = 163 - int(r[team+'_game_number']) # games remaining
                gb = r[team+'_games_behind'] # games behind
                contender_pct = r[team + '_contender_pct']  # winning percentage
                contender_gr = r[team + '_contender_games_remaining']

                # contention score = p(X >= Xc + gb) where X~Bin(pct,gr), Xc~Bin(contender_pct,contender_gr)
                # use p(X >= Y) = Sigma_(k=[0,n]) p(X >= k)*p(X = k)
                r[team+'_contention_score'] = sum(bin_gt(gr,pct,max(k+gb,0))*bin(contender_gr,contender_pct,k) for k in range(0,min(gr,contender_gr)+1))


def ticket_price(df):
    """
    average regular game ticket price (USD not adjusted for inflation) for that team/season.
    Normalized against average ticket prices for all teams in each season
    """
    prices = {}
    norm = defaultdict(list) # all values to be used to normalize the feature

    with open("ticket_prices.csv", encoding='utf-8-sig') as fp:
        reader = csv.DictReader(fp)
        for r in reader:
            for season, price in r.items():
                if season != 'team' and price != '':
                    prices[int(season), r['team']] = float(price)
                    norm[int(season)].append(float(price))

    norm_cache = {}
    for r in df:
        #normalize against all ticket prices for that season.
        r['avg_ticket_price_normalized'] = normalize(norm[r['season']],prices[r['season'],r['home_team']], norm_cache, r['season'])

def player_age(df):
    """
    player age = total number of games to date a player has appeared in an opening lineup.
    Normalized against player ages for all players/games.
    "Veteran" players have better name recoginition, tend to be bigger "stars" and become team icons if the have been with the team for a long time
    """
    current_ages = defaultdict(int) # holds the metric count per player up until a given point in time
    ages = {} # holds age metrics (mean,max) for each team / game
    norm = {'avg': [], 'max': []}
    with open("all_players1970_2017.csv") as fp: # load game logs 1970-2017
        reader = csv.DictReader(fp)
        for r in reader:
            dt = max(datetime.strptime(r['date'],'%m/%d/%Y').date(),date(1990,1,1)) # don't care about individual game data before 1990
            for team in ('home', 'visiting'):
                if dt > date(1990, 1, 1):
                    current_team_ages = [current_ages[r['{}_player{}_id'.format(team,i)]] for i in range(1,10)] #get current age for each player in lineup
                    current_team_age_mean = mean(current_team_ages)
                    current_team_age_max = max(current_team_ages)
                    ages[dt, r[team+'_team'], 'avg'] = current_team_age_mean
                    ages[dt, r[team+'_team'], 'max'] = current_team_age_max
                    norm['avg'].append(current_team_age_mean)
                    norm['max'].append(current_team_age_max)
                for i in range(1,10):
                    current_ages[r['{}_player{}_id'.format(team,i)]]+=1 # update ages for all players in this game's lineup

    norm_cache = {}
    for r in df:
        for team in ('home_team', 'visiting_team'):
            r[team+'_average_player_age_normalized'] = normalize(norm['avg'], ages[r['date'], r[team], 'avg'], norm_cache, 'avg')
            r[team+'_max_player_age_normalized'] = normalize(norm['max'], ages[r['date'], r[team], 'max'], norm_cache, 'max')

