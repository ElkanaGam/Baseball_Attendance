from lxml import html
import requests
import codecs
from bs4 import BeautifulSoup


payroll_base_link = "http://www.thebaseballcube.com/extra/payrolls/byTeam.asp?"
yearq = "Y="
teamq = "T="
allteams = "http://www.thebaseballcube.com/teams/mlb.asp"
game_link_prefix="https://www.baseball-reference.com/leagues/MLB/"
game_link_suffix="-schedule.shtml"
max_year = 1995
min_year = 1989
team_id_dict = {}
team_start_year_dict = {}

# Function to extract the team names, IDs and first year of data in the site

def get_names_ids():
    global allteams
    global team_id_dict
    global team_start_year_dict

    r = requests.get(allteams)
    soup = BeautifulSoup(r.content, 'lxml')
    rows = soup.find_all('tr', {'class': "dataRow"})
    count = 0
    for r in rows:
        children = r.findChildren("a", recursive=True)
        tds = r.findChildren("td", recursive=False)
        if(len(children)>0 and count < 30):
            teamName = str(children[0].text).lower().replace(" ","_")
            teamID = str(children[0]['href']).split("=")[1]
            teamStartYear = str(tds[3].text).split("-")[0]

            #Update global dictionaries for start year of data and team names
            team_id_dict.update({teamID:teamName})
            team_start_year_dict.update({teamID:int(teamStartYear)})
        count+=1


# Function which extracts the player salaries
# input is the year of extraction and team id

def get_team_salary_by_year(team_id,curr_year):

    fp = codecs.open("salaries.txt","a+","utf-8")
    global payroll_base_link
    global teamq
    global yearq
    global team_id_dict
    global team_start_year_dict

    print("Started Extracting " +team_id_dict[team_id]+" Year: "+str(curr_year))

    if(curr_year>= team_start_year_dict[team_id]):
        created_link = payroll_base_link + yearq + str(curr_year) + "&" + teamq + team_id
        r = requests.get(created_link)
        soup = BeautifulSoup(r.content,'lxml')
        rows = soup.find_all('tr',{'class':"dataRow"})
        for r in rows:
            children = r.findChildren("td", recursive=False)
            count = 0
            fp.write(str(curr_year)+","+team_id_dict[team_id]+",")
            for child in children:
                if(count == 0):
                    name = str(child.text).lower().replace(" ","_")
                    fp.write(name)
                    fp.write(",")

                elif (count == 12):
                    st = str(child.text).replace(",","")
                    fp.write(st)
                    fp.write(",")

                count+=1
            fp.write("\n")
        else:
            return


def get_game_link_for_season(curr_year):
    site = "https://www.baseball-reference.com"
    fp = codecs.open("game_links_"+str(curr_year)+".txt","a+","utf-8")
    created_link = game_link_prefix+str(curr_year)+game_link_suffix
    r = requests.get(created_link)
    r.encoding = 'utf-8'
    doc = html.fromstring(r.content)
    rows = doc.xpath("//p/em/a/@href")
    for l in rows:
        fp.write(site+l+"\n")


def get_temp_for_game(game_url):
    fp = codecs.open("game_temps.txt","a+","utf-8")
    r = requests.get(game_url)
    doc = html.fromstring(r.content)
    url_date =game_url.split("boxes/")[1].split("/")[1].split(".shtml")[0][3:11]
    #print(url_date)
    year,month,day = url_date[:4],url_date[4:6],url_date[6:]
    #print(year+"-"+month+"-"+day)
    teams = doc.xpath("//a[contains(@itemprop,'name')]/text()")
    #print(teams)
    info_box = doc.xpath('//*/comment()[contains(., "Start Time Weather")]')
    game_temp = str(info_box[0]).split("Weather:</strong>")[1].split("&")[0].strip(" ")
    if( not game_temp.isdigit()):
        game_temp = "NULL"

    #print(game_temp)
    fp.write(year+"-"+month+"-"+day+","+str(teams[0]).lower().replace(" ","_")+ ","+str(teams[1]).lower().replace(" ","_")+","+game_temp+"\n")
    print(year+"-"+month+"-"+day+","+str(teams[0]).lower().replace(" ","_")+ ","+str(teams[1]).lower().replace(" ","_")+","+game_temp+"\n")






if __name__ == '__main__':
    with codecs.open("game_links_1990.txt", "r", encoding="utf-8") as f:
        content = f.readlines()
    content = [x.strip() for x in content]
    for product in content:
        get_temp_for_game(product)
    #get_game_link_for_season(1990)
    #get_names_ids() # Build global dictionaries
    #y = max_year
    #while(y > min_year):
    #    for tid in team_id_dict.keys(): #every team
    #        get_team_salary_by_year(tid, y)
    #    y -= 1

