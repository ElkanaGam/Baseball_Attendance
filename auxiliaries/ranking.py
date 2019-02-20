from lxml import html
import requests
import codecs
import sys
game_link_prefix="https://www.baseball-reference.com/leagues/MLB/"
game_link_suffix="-schedule.shtml"
max_year = 2017
min_year = 2017

def get_ranking_team(team,curr_year):
    site = "https://www.baseball-reference.com/teams"
    link = site + "/"+team+"/"+str(curr_year)+".shtml"
    fp = codecs.open(team+"_team_ranks_"+str(curr_year)+".csv","a+","utf-8")

    r = requests.get(link)
    r.encoding = 'utf-8'
    doc = html.fromstring(r.content)
    print(r.content)
    rows = doc.xpath("//td[contains(@data-stat,'RBI')]/text()")
    for l in rows:
        print(l)


def get_game_link_for_season(curr_year):
    site = "https://www.baseball-reference.com"
    fp = codecs.open("game_links_"+str(curr_year)+".txt","a+","utf-8")
    # output = codecs.open("game_ranks_" + str(curr_year) + ".csv", "a+", "utf-8")
    # output.write("date,visiting_team,home_team,player_id,player_name,slg,ops,era,wpa,isPitcher")
    created_link = game_link_prefix+str(curr_year)+game_link_suffix
    r = requests.get(created_link)
    r.encoding = 'utf-8'
    doc = html.fromstring(r.content)
    rows = doc.xpath("//p/em/a/@href")
    for l in rows:
        fp.write(site+l+"\n")


def get_ranks_for_game(game_url,curr_year):


    r = requests.get(game_url)
    doc = html.fromstring(r.content)
    url_date =game_url.split("boxes/")[1].split("/")[1].split(".shtml")[0][3:11]

    teams = doc.xpath("//a[contains(@itemprop,'name')]/text()")


    player_stats = doc.xpath("/*//comment()[contains(., 'player is active')]")

    for p in player_stats:
        t1 = str(p).split("<tbody>")[1].split("</tbody>")[0]
        extract_batter_info(t1,url_date,teams)

        try:
            t2 = str(p).split("<tbody>")[2].split("</tbody>")[0]
            extract_batter_info(t2,url_date,teams)

        except IndexError:
            pass



def extract_batter_info(table,url_date,teams):

    year, month, day = url_date[:4], url_date[4:6], url_date[6:]
    fp = codecs.open("game_ranks_" + str(year) + ".csv", "a+", "utf-8")
    tb = str(table).replace("\n","")
    rows = tb.split("<tr")

    player_name,player_id,era,wpa,slg,ops = "","","","","","",


    for i in range(1,len(rows)):
        try:
            player_id = rows[i].split("data-append-csv=\"")[1].split("\"")[0]
            player_name = rows[i].split("shtml\">")[1].split("</a>")[0].lower().replace(" ","_")
        except:
            continue

        pitchers = 0 if (rows[i].find("earned_run_avg\" >") == -1) else 1

        if pitchers:
            era = rows[i].split("earned_run_avg\" >")[1].split("</")[0]
            wpa = rows[i].split("wpa_def\" >")[1].split("</")[0]



        else:
            slg = rows[i].split("slugging_perc\" >")[1].split("</")[0]
            ops =rows[i].split("onbase_plus_slugging\" >")[1].split("</")[0]

        if(era != "" or wpa!="" or slg!="" or ops!=""):
            fp.write(year+"-"+month+"-"+day+","
                     + str(teams[0]).lower().replace(" ","_")+ ","
                     + str(teams[1]).lower().replace(" ","_")+","
                     + player_id+","+player_name+","
                     + slg + "," + ops + ","
                     + era +"," + wpa + ","
                     + str(pitchers)+","+"\n")

            print(year + "-" + month + "-" + day + ","
                        + str(teams[0]).lower().replace(" ", "_") + ","
                        + str(teams[1]).lower().replace(" ", "_") + ","
                        + player_id + "," + player_name + "," + slg + "," + ops + "," + era +"," + wpa+ "," + str(pitchers) + ",")





if __name__ == '__main__':
     y = int(sys.argv[1])
     while y <= int(sys.argv[2]):
        fp = codecs.open("logger.txt", "a+", "utf-8")
        fp.write("INFO: Started season "+str(y)+"\n")
        get_game_link_for_season(y)
        fp.write("INFO: Downloaded Season Links for " + str(y) + "\n")
        with codecs.open("game_links_"+str(y)+".txt", "r", encoding="utf-8") as f:
            content = f.readlines()
        content = [x.strip() for x in content]
        for product in content:
            get_ranks_for_game(product,y)
        y+=1