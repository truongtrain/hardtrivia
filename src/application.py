#import pyodbc
#import os
import flask
import json
import pandas as panda
import ssl 
import requests
from bs4 import BeautifulSoup
from flask import jsonify
from flask_cors import CORS, cross_origin
import time

app = flask.Flask("trivia")
CORS(app)

@app.route('/game/<game_id>', methods=['GET'])
@cross_origin()
def getGame(game_id):
    try:
        _create_unverified_https_context = ssl._create_unverified_context
    except AttributeError:
        pass
    else:
        ssl._create_default_https_context = _create_unverified_https_context
    clues_url = 'https://www.j-archive.com/showgame.php?game_id=' + game_id
    #clues_url = 'http://web.archive.org/web/20210820171013/https://www.j-archive.com/showgame.php?game_id=3332'
    attempts = 0
    while attempts < 5:
        try:
            attempts+=1
            tables = panda.read_html(clues_url, extract_links='all')
            break
        except Exception as e:
            print(e)
            print('Failed to load page. Trying again.')
            time.sleep(1)
    attempts = 0
    while attempts < 5: 
        try:       
            attempts+=1
            board_tables = panda.read_html(clues_url, attrs = {'class': 'round'}, extract_links='all')
            break
        except:
            print(e)
            print('Failed to load board tables. Trying again.')
            time.sleep(1)
    jeopardy_board = board_tables[0]
    if len(board_tables) > 1:
        double_jeopardy_board = board_tables[1]
    responses_url = 'https://www.j-archive.com/showgameresponses.php?game_id=' + game_id
    #responses_url = 'http://web.archive.org/web/20210820171013/https://www.j-archive.com/showgame.php?game_id=3332'
    attempts = 0
    while attempts < 5:
        try:
            attempts+=1
            responses_tables = panda.read_html(responses_url)
            break
        except:
            print(e)
            print('Failed to load responses. Trying again.')
            time.sleep(1)
    attempts = 0
    while attempts < 5:
        try:
            attempts+=1
            responses_board_tables = panda.read_html(responses_url, attrs = {'class': 'round'})
            break
        except:
            print(e)
            print('Failed to load response tables. Trying again.')
            time.sleep(1)
    jeopardy_responses = responses_board_tables[0]
    if len(responses_board_tables) > 1:
        double_jeopardy_responses = responses_board_tables[1]
        final_jeopardy_category = tables[-5]
        final_jeopardy_clue = tables[-4]
    else:
        double_jeopardy_board = []
        double_jeopardy_responses = []
        final_jeopardy_category = []
        final_jeopardy_clue = []
        final_jeopardy_responses = []
        fj_correct_response = []
    coryats = responses_tables[-1]
    contestants = [format_contestant_name(coryats.to_dict('records')[0][0]), format_contestant_name(coryats.to_dict('records')[0][1]), format_contestant_name(coryats.to_dict('records')[0][2])]
    weakest_contestant = get_weakest_contestant(coryats, contestants)
    final_jeopardy_responses = responses_tables[-3]
    fj_correct_response = get_fj_correct_response(responses_url)
    # generate clue_json for each category_number and difficulty_level
    jeopardy_clues = []
    double_jeopardy_clues = []
    clue_url_map = get_clue_url_map(clues_url)
    for category_number in range(0, 6):
        jeopardy_clues.append([])
        double_jeopardy_clues.append([])
        for difficulty_level in range(1, 6):
            jeopardy_clues[category_number].append(get_clue(category_number, difficulty_level, jeopardy_board, jeopardy_responses, 1, contestants, clue_url_map))
            if len(double_jeopardy_board) > 0:
                double_jeopardy_clues[category_number].append(get_clue(category_number, difficulty_level, double_jeopardy_board, double_jeopardy_responses, 2, contestants, clue_url_map))
    return jsonify({
    'contestants': contestants,
    'weakest_contestant': weakest_contestant,
    #'weakest_contestant': 'Mike',
    'jeopardy_round': jeopardy_clues,
    'double_jeopardy_round': double_jeopardy_clues,
    'final_jeopardy': get_final_jeopardy(final_jeopardy_category, final_jeopardy_clue, final_jeopardy_responses, fj_correct_response)
    })

def get_final_jeopardy(final_jeopardy_category, final_jeopardy_clue, final_jeopardy_responses, fj_correct_response):
    if len(final_jeopardy_category) == 0:
        return [];
    return {
        'category': final_jeopardy_category.to_dict('records')[0][0][0],
        'clue': final_jeopardy_clue.to_dict('records')[0][0][0],
        'url': final_jeopardy_clue.to_dict('records')[0][0][1],
        'contestant_responses': get_contestant_responses(final_jeopardy_responses.to_dict('records')),
        'correct_response': fj_correct_response
    }

def get_clue_url_map(clues_url):
    html_text = requests.get(clues_url).text
    soup = BeautifulSoup(html_text, 'html.parser')
    clues = soup.find_all('td', {'class': 'clue'})
    clue_url_map = {}
    for clue_html in clues:
        clue_number_html = clue_html.find('td', {'class': 'clue_order_number'})
        try:
            clue_id_href = clue_number_html.find('a')['href']
            id_index = clue_id_href.find('clue_id=')
            clue_id = clue_id_href[id_index+len('clue_id='):]
            clue_text_html = clue_html.find('td', {'class': 'clue_text'})  
            anchor_html = clue_text_html.find('a')   
            if anchor_html is not None:
                clue_url_map[clue_id] = anchor_html['href']               
        except:
            pass
    return clue_url_map

def format_contestant_name(contestant):
    if ' ' in contestant:
        return contestant.split()[-1];
    return contestant

def dollar_to_int(dollar):
    if '-' in dollar:
        return int(dollar[2:].replace(',', ''))
    return int(dollar[1:].replace(',', ''))


def get_weakest_contestant(coryats, contestants):
    coryat1 = coryats[0][1]
    coryat2 = coryats[1][1]
    coryat3 = coryats[2][1]
    coryat_list = [dollar_to_int(coryat1), dollar_to_int(coryat2), dollar_to_int(coryat3)]
    min_coryat = min(coryat_list)
    min_coryat_index=coryat_list.index(min_coryat)
    return contestants[min_coryat_index]


def get_incorrect_responses(parentheses1, parentheses2, response_string):
    incorrect_responses = []
    if ': ' not in response_string or is_correct_response(response_string):
        return []
    while parentheses1 >=0 and parentheses2 >= 0:
        string_to_remove = response_string[parentheses1:parentheses2+1]
        response_string = response_string.replace(string_to_remove,'')
        if 'for $' not in string_to_remove and 'Ken:' not in string_to_remove:
            incorrect_responses.append(string_to_remove)
        parentheses1 = response_string.find('(')   
        parentheses2 = response_string.find(')')
    return incorrect_responses


def get_correct_response(response, correct_contestant):
    delimiter = ' '
    correct_response = ''
    if correct_contestant != '':
        for word in response:
            if word == correct_contestant:
                continue
            correct_response += word + ' '
    else:
        correct_response = delimiter.join(response)
        correct_response = correct_response.replace('Triple Stumper','')
    return format_text(correct_response).strip()


def get_response(incorrect_responses, incorrect_contestants, response_string):
    for incorrect_response in incorrect_responses:
        response_string = response_string.replace(incorrect_response,'')
    for contestant in incorrect_contestants:
        response_string = response_string.replace(contestant,'')
    return response_string.split()[2:]

def is_correct_response(response_string):
    what_response = 'what is [*]'
    what_response2 = 'what\'s [*]'
    what_response3 = 'what are [*]'
    who_response = 'who is [*]'
    who_response2 = 'who\'s [*]'
    who_response3 = 'who are [*]'
    response_lower = response_string.lower()  
    return (what_response in response_lower or what_response2 in response_lower or what_response3 in response_lower or who_response in response_lower or who_response2 in response_lower or who_response3 in response_lower) 

def is_incorrect_response(contestant, response_string):
    if is_correct_response(response_string):
        return False
    what_response = 'what is'
    what_response2 = 'what\'s'
    what_response3 = 'what are'
    who_response = 'who is'
    who_response2 = 'who\'s'
    who_response3 = 'who are'
    incorrect_response = contestant + ': '
    response_lower = response_string.lower()  
    return incorrect_response in response_string and (what_response in response_lower or what_response2 in response_lower or what_response3 in response_lower or who_response in response_lower or who_response2 in response_lower or who_response3 in response_lower) 

def get_clue_response(response, response_string, contestants):
    correct_contestant = ''
    incorrect_contestants = []
    for contestant in contestants:
        if is_incorrect_response(contestant, response_string):
            incorrect_contestants.append(format_contestant_name(contestant))
        elif contestant in response[-1]:
            correct_contestant = contestant  
    parentheses1 = response_string.find('(')   
    parentheses2 = response_string.find(')')
    incorrect_responses = get_incorrect_responses(parentheses1, parentheses2, response_string)
    response = get_response(incorrect_responses, incorrect_contestants, response_string)
    correct_response = get_correct_response(response, correct_contestant)
    return json.loads(json.dumps({
            'correct_contestant': correct_contestant,
            'correct_response': correct_response,
            'incorrect_contestants': incorrect_contestants,
            'incorrect_responses': incorrect_responses
        }))


def get_board(tables, start_index):
    #since the position of the double jeopardy board can vary, find the index of the table with length 6
    while len(tables[start_index]) != 6:
        start_index+=1
    return tables[start_index]


def get_fj_correct_response(responses_url):
    html_text = requests.get(responses_url).text
    soup = BeautifulSoup(html_text, 'html.parser')
    return soup.find_all("em", {"class": "correct_response"})[-1].text


def get_clue_value(difficulty_level, round):
    values = [200, 400, 600, 800, 1000]
    return values[difficulty_level-1] * round


def get_clue(category_number, difficulty_level, jeopardy_board, jeopardy_responses, round, contestants, clue_url_map):
    if (str(jeopardy_board[category_number][difficulty_level][0]) == ''):
        return {
        'number': '',
        'category': '',
        'value': '',
        'text': '',
        'response': '',
        'daily_double_wager': ''
    }
    clue = jeopardy_board.to_dict('records')[difficulty_level][category_number][0].split()
    url = jeopardy_board.to_dict('records')[difficulty_level][category_number][1]  
    id_index = url.find('clue_id=')
    clue_id = url[id_index+len('clue_id='):]
    clue_value = clue[0]
    clue_number = clue[1]
    delimiter = ' '
    clue_text = delimiter.join(clue[2:])
    category = jeopardy_board.to_dict('records')[0][category_number][0]
    category_note = ''
    if category.find('(') >= 0 and category.find(')') >= 0:
        start_index = category.find('(')
        end_index = category.find(')')
        category_note = category[start_index+1:end_index]
        category = category[0:start_index] + category[end_index+1:]   
    response_string = jeopardy_responses.to_dict('records')[difficulty_level][category_number]
    response = response_string.split()[2:]
    clue_response = get_clue_response(response, response_string, contestants)
    daily_double_wager = 0
    if clue_value == 'DD:':      
        daily_double_wager = int(clue_number.replace(',', '')[1:])
        clue_value = get_clue_value(difficulty_level, round)
        clue_number = clue_text.split()[0]
        clue_text = delimiter.join(clue_text.split()[1:])
    else:
        clue_value = int(clue_value[1:])
    return {
        'clue_id': clue_id,
        'number': int(clue_number),
        'category': category,
        'category_note': category_note,
        'value': clue_value,
        'text': format_text(clue_text.upper()),
        'response': clue_response,
        'daily_double_wager': daily_double_wager,
        'url': get_clue_url(clue_id, clue_url_map)
    }

def get_clue_url(clue_id, clue_url_map):
    if clue_id in clue_url_map:
        return clue_url_map[clue_id]
    return ''

def format_text(clue_text):
    clue_text = remove_brackets(clue_text)
    while clue_text[0] == '(':
        clue_text = remove_parentheses(clue_text).strip()
    return clue_text

def remove_parentheses(clue_text): 
    idx2 = clue_text.index(')')
    return clue_text[idx2+1:]

def remove_brackets(clue_text): 
    if clue_text[0] == '[':
        idx2 = clue_text.index(']')
        return clue_text[idx2+1:]
    return clue_text

def get_contestant_responses(contestant_responses):
    responses = []
    for i in range(0, 6, 2):
        if len(contestant_responses) > i:
            responses.append({
                'contestant': format_contestant_name(contestant_responses[i][0]),
                'response': contestant_responses[i][1],
                'wager': int(contestant_responses[i+1][0].replace(',', '')[1:])
            })
    return responses

# @app.route('/example', methods=['GET'])
# @cross_origin()
# def getExample():
#     return json.dumps({"contestants": ["Brian", "Lanny", "Martin"], "weakest_contestant": "Martin", "jeopardy_round": [[{"number": 5, "category": "NAME THE BOOK  ", "value": 200, "text": "\"'HE IS A STRANGE, HALF-SAVAGE CREATURE OF THE JUNGLE, MISS PORTER'\"", "response": {"correct_contestant": "", "correct_response": "Tarzan of the Apes", "incorrect_contestants": ["Lanny", "Martin"], "incorrect_responses": ["(Lanny: What is Tarzan?)", "(Alex: Be more specific.)", "(Lanny: What is Tarzan, the Ape Man?)", "(Alex: No. Martin?)", "(Martin: Who is Tarzan of the Jungle?)"]}, "daily_double_wager": 0}, {"number": 6, "category": "NAME THE BOOK  ", "value": 400, "text": "\"THEY REACHED THE CARRIAGE-DRIVE AT TOAD HALL TO FIND, AS THE BADGER HAD ANTICIPATED, A SHINY NEW MOTOR-CAR\"", "response": {"correct_contestant": "Lanny", "correct_response": "Wind in the Willows", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}, {"number": 7, "category": "NAME THE BOOK  ", "value": 600, "text": "\"'THANKS, OLLIE.' THOSE WERE HER LAST WORDS\"", "response": {"correct_contestant": "", "correct_response": "Love Story", "incorrect_contestants": [], "incorrect_responses": ["(Alex: \"Love is never having to say you're sorry.\" [*] was the book.)"]}, "daily_double_wager": 0}, {"number": 8, "category": "NAME THE BOOK  ", "value": 800, "text": "\"ADAM TRASK WAS BORN ON A FARM ON THE OUTSKIRTS OF A LITTLE TOWN WHICH WAS NOT FAR FROM A BIG TOWN IN CONNECTICUT\"", "response": {"correct_contestant": "Lanny", "correct_response": "East of Eden", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}, {"number": 9, "category": "NAME THE BOOK  ", "value": 1000, "text": "\"HABIT, N. A SHACKLE FOR THE FREE\" & \"PREJUDICE, N. A VAGRANT OPINION WITHOUT VISIBLE MEANS OF SUPPORT\"", "response": {"correct_contestant": "", "correct_response": "The Devil's Dictionary", "incorrect_contestants": [], "incorrect_responses": ["(Alex: Two entries in [*].)"]}, "daily_double_wager": 0}], [{"number": 19, "category": "ELVIS A TO Z", "value": 200, "text": "\"H\" IS FOR THIS 1956 SONG FOR WHICH ELVIS FOUND \"A NEW PLACE TO DWELL\"--AT THE TOP OF THE CHARTS", "response": {"correct_contestant": "Brian", "correct_response": "Heartbreak Hotel", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}, {"number": 26, "category": "ELVIS A TO Z", "value": 400, "text": "\"A\" IS FOR THIS LAS VEGAS HOTEL WHERE ELVIS & PRISCILLA WERE MARRIED ON MAY 1, 1967, NOT BY A GENIE BUT BY A JUDGE", "response": {"correct_contestant": "Martin", "correct_response": "the Aladdin", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}, {"number": 27, "category": "ELVIS A TO Z", "value": 600, "text": "\"V\" IS FOR THIS 1964 FILM THAT USED THE TAGLINE \"ELVIS IS AT THE WHEEL BUT ANN-MARGRET DRIVES HIM WILD!\"", "response": {"correct_contestant": "Lanny", "correct_response": "Viva Las Vegas", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}, {"number": 28, "category": "ELVIS A TO Z", "value": 800, "text": "\"T\" IS FOR THIS MISSISSIPPI TOWN OF ELVIS' BIRTH WHICH WAS ONCE CALLED GUM POND BUT LATER RENAMED FOR A TREE", "response": {"correct_contestant": "Lanny", "correct_response": "Tupelo", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}, {"number": 29, "category": "ELVIS A TO Z", "value": 1000, "text": "\"P\" IS FOR THIS MANAGER WHO SOLD ELVIS' ENTIRE MUSIC CATALOG TO RCA IN 1973 FOR ABOUT $5 MILLION, FAR BELOW ITS MARKET VALUE", "response": {"correct_contestant": "Martin", "correct_response": "Colonel Parker", "incorrect_contestants": [], "incorrect_responses": ["(Tom)"]}, "daily_double_wager": 0}], [{"number": 1, "category": "THE COMPLETELY GUILTY BYSTANDER", "value": 200, "text": "ON OCT. 8, 1871 I DIDN'T SEE HER COW START THE FIRE AT HER CHICAGO BARN, BUT I SHOULD HAVE PUT IT OUT EARLY", "response": {"correct_contestant": "Martin", "correct_response": "Mrs. O'Leary", "incorrect_contestants": ["Lanny"], "incorrect_responses": ["(Lanny: Who is Mrs. Leary?)"]}, "daily_double_wager": 0}, {"number": 2, "category": "THE COMPLETELY GUILTY BYSTANDER", "value": 400, "text": "I DIDN'T \"AID\" THE THIEF BY GIVING HIM DIRECTIONS TO THE BANK, NOR DID I DO THIS COMPANION ACT; I DIDN'T INCITE HIM TO ROB IT", "response": {"correct_contestant": "Lanny", "correct_response": "abet", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}, {"number": 16, "category": "THE COMPLETELY GUILTY BYSTANDER", "value": 600, "text": "I WAS A LOOKOUT--I DIDN'T BUST OPEN THE LOCK FOR THE \"BREAKING\" PART OR DO THIS CRIME THAT GOES WITH IT", "response": {"correct_contestant": "Brian", "correct_response": "entering", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}, {"number": 17, "category": "THE COMPLETELY GUILTY BYSTANDER", "value": 800, "text": "I DID GIVE THE GUY A CROWBAR, BUT I NEVER DREAMED HE WOULD STEAL A CAR & COMMIT THIS 3-WORD CRIME, ALSO A VIDEO GAME", "response": {"correct_contestant": "Brian", "correct_response": "grand theft auto", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}, {"number": 18, "category": "THE COMPLETELY GUILTY BYSTANDER", "value": 1000, "text": "I ONLY INTRODUCED THIS BRITISH WAR SECRETARY TO CHRISTINE KEELER; I HAD NO IDEA A SCANDAL WOULD ENSUE & HE'D QUIT", "response": {"correct_contestant": "Lanny", "correct_response": "John Profumo", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}], [{"number": 22, "category": "HEAD TRAUMA", "value": 200, "text": "THIS HEMORRHAGE OF A BLOOD VESSEL LEADING TO THE BRAIN IS ALSO KNOWN AS AN APOPLEXY", "response": {"correct_contestant": "Martin", "correct_response": "a stroke", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}, {"number": 23, "category": "HEAD TRAUMA", "value": 400, "text": "ALSO KNOWN AS DENS SAPIENTIAE, THESE CAN BE A PAIN IF THEY HAVE TO COME OUT", "response": {"correct_contestant": "Martin", "correct_response": "the wisdom teeth ", "incorrect_contestants": [], "incorrect_responses": ["(or third molars)"]}, "daily_double_wager": 1500}, {"number": 24, "category": "HEAD TRAUMA", "value": 600, "text": "THE NFL RECENTLY SET A POLICY FOR THESE INJURIES, FROM THE LATIN FOR \"SHAKING\"", "response": {"correct_contestant": "Lanny", "correct_response": "concussions", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}, {"number": 25, "category": "HEAD TRAUMA", "value": 800, "text": "VEGETABLE TERM FOR AN EAR THAT'S MISSHAPEN FROM REPEATED BLOWS", "response": {"correct_contestant": "Lanny", "correct_response": "a cauliflower ear", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}, {"number": 30, "category": "HEAD TRAUMA", "value": 1000, "text": "ANTONIO EGAS MONIZ WON A 1949 NOBEL PRIZE FOR INTRODUCING THIS PROCEDURE THAT AFFECTS THE PREFRONTAL LOBES", "response": {"correct_contestant": "Lanny", "correct_response": "a lobotomy", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}], [{"number": 13, "category": "MINDBLOWERS", "value": 200, "text": "IN 1875 THE FIRST SWIM ACROSS THIS WATERWAY TOOK ABOUT 22 HOURS; IN 1994 IT WAS ACCOMPLISHED IN ABOUT 7", "response": {"correct_contestant": "Martin", "correct_response": "the English Channel", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}, {"number": 14, "category": "MINDBLOWERS", "value": 400, "text": "THIS SAN ANTONIO SPURS STAR ORIGINALLY TRAINED TO BE AN OLYMPIC SWIMMER, BUT HURRICANE HUGO WRECKED THE POOL", "response": {"correct_contestant": "Lanny", "correct_response": "Tim Duncan", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}, {"number": 15, "category": "MINDBLOWERS", "value": 600, "text": "THE WIFE OF THIS \"GIVE ME LIBERTY OR GIVE ME DEATH\" SPEECHMAKER WAS CONFINED AT HOME DUE TO MENTAL ILLNESS", "response": {"correct_contestant": "Brian", "correct_response": "Patrick Henry", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}, {"number": 20, "category": "MINDBLOWERS", "value": 800, "text": "HORACE GRAY WAS THE FIRST SUPREME COURT JUSTICE TO HIRE 1 OF THESE; HE SPENT MORE TIME AS GRAY'S BARBER THAN RESEARCHING", "response": {"correct_contestant": "Brian", "correct_response": "a clerk", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}, {"number": 21, "category": "MINDBLOWERS", "value": 1000, "text": "CHRISTIANITY TODAY SAID THIS ANIMATED TV DAD IS MORE ASSOCIATED WITH CHRISTIANITY THAN THE POPE OR MOTHER TERESA", "response": {"correct_contestant": "Martin", "correct_response": "Ned Flanders", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}], [{"number": 3, "category": "\"BEST\" SELLERS", "value": 200, "text": "THE CHIEF ATTENDANT OF THE BRIDEGROOM", "response": {"correct_contestant": "Martin", "correct_response": "the best man", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}, {"number": 4, "category": "\"BEST\" SELLERS", "value": 400, "text": "PROVERBIAL 3-WORD TERM FOR A DOG IN RELATION TO OUR SPECIES", "response": {"correct_contestant": "Lanny", "correct_response": "man's best friend", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}, {"number": 10, "category": "\"BEST\" SELLERS", "value": 600, "text": "DAY-OF-THE-WEEK TERM FOR CLOTHING WORN ON SPECIAL OCCASIONS", "response": {"correct_contestant": "Brian", "correct_response": "Sunday best", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}, {"number": 11, "category": "\"BEST\" SELLERS", "value": 800, "text": "UNO, A 15-INCH BEAGLE, TOOK THIS WESTMINSTER KENNEL CLUB TOP PRIZE IN 2008", "response": {"correct_contestant": "Lanny", "correct_response": "Best in Show", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}, {"number": 12, "category": "\"BEST\" SELLERS", "value": 1000, "text": "BRIAN EPSTEIN WAS ASSIGNED TO BOOT THIS DRUMMER FROM THE BEATLES IN 1962", "response": {"correct_contestant": "Lanny", "correct_response": "Pete Best", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}]], "double_jeopardy_round": [[{"number": 1, "category": "LATIN AMERICAN HISTORY", "value": 400, "text": "IN 1821 PANAMA BROKE AWAY FROM SPAIN & BECAME A PROVINCE OF THIS COUNTRY", "response": {"correct_contestant": "Lanny", "correct_response": "Colombia", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}, {"number": 2, "category": "LATIN AMERICAN HISTORY", "value": 800, "text": "IN OCTOBER 1520 THIS PORTUGUESE EXPLORER BECAME THE FIRST EUROPEAN TO REACH CHILE & TIERRA DEL FUEGO", "response": {"correct_contestant": "", "correct_response": "Ferdinand Magellan", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}, {"number": 3, "category": "LATIN AMERICAN HISTORY", "value": 1200, "text": "SHIPWRECKED ENGLISH SAILORS FOUNDED A SETTLEMENT IN 1638 IN WHAT IS NOW THIS CENTRAL AMERICAN NATION", "response": {"correct_contestant": "", "correct_response": "Belize", "incorrect_contestants": ["Lanny"], "incorrect_responses": ["(Lanny: What is... Costa Rica?)", "(Alex: No. It's the only country in Central America that has English as one of its languages, [*]. [*].)"]}, "daily_double_wager": 3000}, {"number": 4, "category": "LATIN AMERICAN HISTORY", "value": 1600, "text": "THIS INDIAN CIVILIZATION, PROBABLY THE FIRST IN THE AMERICAS, LIVED IN EASTERN MEXICO FROM ABOUT 1200 TO 400 B.C.", "response": {"correct_contestant": "Brian", "correct_response": "\u00e2\u0080\u00a6the Olmec", "incorrect_contestants": ["Martin"], "incorrect_responses": ["(Martin: Who are the Toltec?)", "(Alex: [*], yes, they came much earlier.)", "(s)"]}, "daily_double_wager": 0}, {"number": 5, "category": "LATIN AMERICAN HISTORY", "value": 2000, "text": "IN 1990 SHE DEFEATED DANIEL ORTEGA TO BECOME PRESIDENT OF NICARAGUA", "response": {"correct_contestant": "", "correct_response": "Violeta Chamorro", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}], [{"number": 16, "category": "SPIELBERG MOVIES IN OTHER WORDS", "value": 400, "text": "\"MANDIBLES\"", "response": {"correct_contestant": "Brian", "correct_response": "Jaws", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}, {"number": 17, "category": "SPIELBERG MOVIES IN OTHER WORDS", "value": 800, "text": "\"CAPITAL OF BAVARIA\"", "response": {"correct_contestant": "Lanny", "correct_response": "Munich", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}, {"number": 18, "category": "SPIELBERG MOVIES IN OTHER WORDS", "value": 1200, "text": "\"FOREVER\"", "response": {"correct_contestant": "", "correct_response": "Always", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}, {"number": 19, "category": "SPIELBERG MOVIES IN OTHER WORDS", "value": 1600, "text": "\"ACHIEVE MY APPREHENSION WHERE POSSIBLE\"", "response": {"correct_contestant": "", "correct_response": "Catch Me if You Can", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}, {"number": 20, "category": "SPIELBERG MOVIES IN OTHER WORDS", "value": 2000, "text": "\"HELIOS' KINGDOM\"", "response": {"correct_contestant": "", "correct_response": "Empire of the Sun", "incorrect_contestants": ["Lanny"], "incorrect_responses": ["(Lanny: What is Kingdom of the Sun?)"]}, "daily_double_wager": 0}], [{"number": 11, "category": "IT'S GETTING WINDY", "value": 400, "text": "RESIDENTS OF GREENSBURG, KANSAS HAD ABOUT 20 MINUTES WARNING BEFORE ONE OF THESE DESTROYED THEIR TOWN IN 2007", "response": {"correct_contestant": "Brian", "correct_response": "a tornado", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}, {"number": 12, "category": "IT'S GETTING WINDY", "value": 800, "text": "NOAA FORECASTS INCLUDE WIND SPEEDS LIKE 25-30 MPH \"WITH\" THESE SUDDEN BURSTS OF WIND \"UP TO 50\"", "response": {"correct_contestant": "Lanny", "correct_response": "[Alex reads \"NOAA\" as \"The National Oceanic and Atmospheric Administration\".]gusts", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}, {"number": 13, "category": "IT'S GETTING WINDY", "value": 1200, "text": "IT BLEW INTO SOUTHERN LOUISIANA SEPT. 1, 2008 BUT FORTUNATELY DIDN'T TURN OUT TO BE KATRINA II", "response": {"correct_contestant": "Martin", "correct_response": "Gustav", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}, {"number": 14, "category": "IT'S GETTING WINDY", "value": 1600, "text": "THE HOT \"KHAMSIN\" BLOWS ABOUT 50 DAYS A YEAR & GETS ITS NAME FROM THE WORD FOR 50 IN THIS LANGUAGE", "response": {"correct_contestant": "", "correct_response": "Arabic", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}, {"number": 15, "category": "IT'S GETTING WINDY", "value": 2000, "text": "THESE WINDS ARE NO LONGER NEEDED FOR COMMERCE, BUT THEY DO MAKE FOR GREAT WINDSURFING IN BARBADOS", "response": {"correct_contestant": "Martin", "correct_response": "the trade winds", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 3000}], [{"number": 6, "category": "INTERNATIONAL TRAVEL", "value": 400, "text": "WHEN IT'S JUST YOU & THIS PERSON, BE PREPARED TO SHOW A LETTER OF CONSENT OR ORDER OF CUSTODY", "response": {"correct_contestant": "Brian", "correct_response": "your child", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}, {"number": 7, "category": "INTERNATIONAL TRAVEL", "value": 800, "text": "THOUGH NOT BIG ENOUGH TO GET A STAR ON OUR FLAG, THEY'RE THE CABINS ABOARD CRUISE SHIPS", "response": {"correct_contestant": "Brian", "correct_response": "staterooms", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}, {"number": 8, "category": "INTERNATIONAL TRAVEL", "value": 1200, "text": "NATIONALS OF THE EUROPEAN UNION, AUSTRALIA, CANADA & THE U.S. WHO VISIT PERU FOR LESS THAN 90 DAYS AREN'T REQUIRED TO CARRY ONE OF THESE DOCUMENTS UNLESS THEY'RE HERE FOR BUSINESS", "response": {"correct_contestant": "Martin", "correct_response": "a visa", "incorrect_contestants": ["Lanny"], "incorrect_responses": ["(Lanny: What is a passport?)"]}, "daily_double_wager": 0}, {"number": 9, "category": "INTERNATIONAL TRAVEL", "value": 1600, "text": "CITY ON THE SOUTH SIDE OF THE MOST CONGESTED U.S.-MEXICO CROSSING; HALF THE NORTHBOUND CARS WAIT 90 MINUTES", "response": {"correct_contestant": "Lanny", "correct_response": "Tijuana", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}, {"number": 10, "category": "INTERNATIONAL TRAVEL", "value": 2000, "text": "A U.S. EMBASSY MAY PROVIDE SERVICES THROUGH THIS \"SECTION\" WHOSE NAME RECALLS AN ANCIENT ROMAN OFFICE", "response": {"correct_contestant": "Brian", "correct_response": "consular ", "incorrect_contestants": [], "incorrect_responses": ["(consulate accepted)"]}, "daily_double_wager": 0}], [{"number": 21, "category": "SCOTSMEN", "value": 400, "text": "THIS SCOTTISH POET RHYMED \"PURPLE\" WITH \"CURPLE\" (MEANING \"THE RUMP\")", "response": {"correct_contestant": "Brian", "correct_response": "Burns", "incorrect_contestants": [], "incorrect_responses": ["(Rabbie)"]}, "daily_double_wager": 0}, {"number": 22, "category": "SCOTSMEN", "value": 800, "text": "HIS \"WEALTH OF NATIONS\" IS WIDELY CONSIDERED THE FIRST GREAT WORK IN POLITICAL ECONOMY", "response": {"correct_contestant": "Martin", "correct_response": "Adam Smith", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}, {"number": 23, "category": "SCOTSMEN", "value": 1200, "text": "IN THE 1760S HE IMPROVED UPON THE NEWCOMEN STEAM ENGINE BY MAKING A SEPARATE CONDENSER, HIS FIRST INVENTION", "response": {"correct_contestant": "Brian", "correct_response": "Watt", "incorrect_contestants": ["Martin"], "incorrect_responses": ["(Martin: Who is Livingston?)", "(James)"]}, "daily_double_wager": 0}, {"number": 24, "category": "SCOTSMEN", "value": 1600, "text": "THIS SCOTTISH REFORMATION LEADER PUBLISHED HIS \"FAITHFUL ADMONITION\" TO PROTESTANTS IN ENGLAND IN 1554", "response": {"correct_contestant": "Martin", "correct_response": "John Knox", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}, {"number": 25, "category": "SCOTSMEN", "value": 2000, "text": "AFTER RECOVERING FROM A NERVOUS BREAKDOWN, THIS SCOTTISH PHILOSOPHER WROTE \"A TREATISE OF HUMAN NATURE\"", "response": {"correct_contestant": "", "correct_response": "David Hume", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}], [{"number": 26, "category": "ADD A LETTER", "value": 400, "text": "PUT A LETTER ON YOUR MITTEN & YOU BECOME THIS, LOVE-STRUCK", "response": {"correct_contestant": "Martin", "correct_response": "smitten", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}, {"number": 27, "category": "ADD A LETTER", "value": 800, "text": "AFTER YOU TAKE A BEATING, ADD A LETTER TO IT & I'LL GIVE YOU ONE OF THESE TONGUE-LASHINGS", "response": {"correct_contestant": "Lanny", "correct_response": "a berating", "incorrect_contestants": ["Martin"], "incorrect_responses": ["(Martin: [No response])"]}, "daily_double_wager": 0}, {"number": 28, "category": "ADD A LETTER", "value": 1200, "text": "ADDING A LETTER TO SCONE TURNS A BAKED GOOD INTO THIS BRACKET FOR CANDLES", "response": {"correct_contestant": "Martin", "correct_response": "a sconce", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}, {"number": 29, "category": "ADD A LETTER", "value": 1600, "text": "ADD A LETTER TO IGNITE & IT BECOMES THIS BROWN COAL", "response": {"correct_contestant": "Brian", "correct_response": "lignite", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}, {"number": 30, "category": "ADD A LETTER", "value": 2000, "text": "HADDOCK IS A FISH; ADD A LETTER & IT BECOMES THIS LARGE CITRUS FRUIT", "response": {"correct_contestant": "", "correct_response": "shaddock", "incorrect_contestants": [], "incorrect_responses": []}, "daily_double_wager": 0}]], "final_jeopardy": {"category": "PRESIDENTIAL ELECTIONS", "clue": "One of the 2 presidents to win the national popular vote 3 times but only be elected president twice", "contestant_responses": [{"contestant": "Lanny", "response": "Who is Nixon", "wager": 1000}, {"contestant": "Martin", "response": "Who is Grover Cleveland?", "wager": 5601}, {"contestant": "Brian", "response": "Who is Cleveland", "wager": 8300}], "correct_response": "(1 of) Grover Cleveland & Andrew Jackson"}})

# @app.route('/question/<num_questions>', methods=['GET'])
# def getQuestion(num_questions):
#     cnxn = connect_db()
#     cursor = cnxn.cursor()
#     jsonarray = []
#     trivias = load_trivia(cursor, num_questions)
#     for trivia in trivias:
#         triviajson = json.loads(trivia)
#         if not triviajson["class2"]:
#             query = "select top(3) Answer from Trivia where Answer in (select Answer from Trivia " \
#                     "where Topic = ? and Class1 = ? and Answer != ?) group by Answer order by newid()"
#             tuple = (triviajson["topic"], triviajson["class1"], triviajson["correct"])
#         else:
#             query = "select top(3) Answer from Trivia where Answer in (select Answer from Trivia " \
#                     "where Topic = ? and Class1 = ? and Class2 = ? and Answer != ?) group by Answer order by newid()"
#             tuple = (triviajson["topic"], triviajson["class1"], triviajson["class2"], triviajson["correct"])
#         answers = []
#         cursor.execute(query, tuple)
#         for row in cursor:
#             answers.append(row[0])
#         # get more answers if necessary
#         if len(answers) < 3:
#             additional_answers = get_more_answers(answers, cursor, triviajson["topic"], triviajson["class1"], triviajson["correct"])
#             answers = answers + additional_answers
#         answers.append(triviajson["correct"])
#         answers.sort()
#         triviajson["answers"] = answers
#         jsonarray.append(triviajson)

#     return jsonify({'trivia': jsonarray})


# def load_trivia(cursor, num_questions):
#     cursor.execute("select top(?) * from Trivia where Topic = 'Mythology' order by newid()", int(num_questions))
#     trivias = []
#     for row in cursor:
#         trivias.append(json.dumps(
#             {'correct': row[1],
#              'question': str(row[2]).replace("\"", "'"),
#              'answers': [],
#              'topic': row[3],
#              'class1': row[4],
#              'class2': row[5]}))
#     return trivias


# def connect_db():
#     driver = os.environ['driver']
#     server = os.environ['server']
#     database = os.environ['database']
#     uid = os.environ['uid']
#     pwd = os.environ['pwd']
#     cnxn = pyodbc.connect("Driver={%s};"
#                           "Server=%s;"
#                           "Database=%s;"
#                           "uid=%s;"
#                           "pwd=%s" % (driver, server, database, uid, pwd))
#     return cnxn


# def get_more_answers(answers, cursor, topic, class1, answer):
#     additional_answers = [];
#     numMissing = 3 - len(answers)
#     query = "select Answer from Trivia where Answer in (select Answer from Trivia " \
#                                               "where Topic = ? and Class1 = ? and Answer != ?) group by Answer order by newid()"
#     cursor.execute(query, topic, class1, answer)
#     for row in cursor:
#         if row[0] != answer and row[0] not in answers:
#             additional_answers.append(row[0])
#             if len(additional_answers) == numMissing:
#                 break
#     return additional_answers

# class Question:
#     def __init__(self, question, correct, answers, topic, class1, class2):
#         self.question = question
#         self.correct = correct
#         self.answers = answers
#         self.topic = topic
#         self.class1 = class1
#         self.class2 = class2

app.run()