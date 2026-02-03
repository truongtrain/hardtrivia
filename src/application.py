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
    'jeopardy_round': jeopardy_clues,
    'double_jeopardy_round': double_jeopardy_clues,
    'final_jeopardy': get_final_jeopardy(final_jeopardy_category, final_jeopardy_clue, final_jeopardy_responses, fj_correct_response)
    })

def get_final_jeopardy(final_jeopardy_category, final_jeopardy_clue, final_jeopardy_responses, fj_correct_response):
    if len(final_jeopardy_category) == 0:
        return []
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
        return contestant.split()[-1]    
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
    response_lower = response_string.lower()  
    return '[*]--' in response_lower or '[***]?' in response_lower

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

app.run()