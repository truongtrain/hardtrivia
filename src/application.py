#import pyodbc
#import os
import flask
import json
import pandas as panda
import ssl 
import requests
from bs4 import BeautifulSoup
from flask import jsonify

app = flask.Flask("trivia")

@app.route('/game/<game_id>', methods=['GET'])
def getGame(game_id):
    try:
        _create_unverified_https_context = ssl._create_unverified_context
    except AttributeError:
        pass
    else:
        ssl._create_default_https_context = _create_unverified_https_context
    clues_url = 'https://www.j-archive.com/showgame.php?game_id=' + str(game_id)
    tables = panda.read_html(clues_url)
    jeopardy_board = tables[1]
    double_jeopardy_board = get_board(tables, 60)
    final_jeopardy_category = tables[-4]
    final_jeopardy_clue = tables[-3]
    responses_url = 'https://www.j-archive.com/showgameresponses.php?game_id=' + str(game_id)
    tables = panda.read_html(responses_url)
    jeopardy_responses = tables[1]
    double_jeopardy_responses = get_board(tables, 90)
    coryats = tables[-1]
    contestants = [format_contestant_name(coryats.to_dict('records')[0][0]), format_contestant_name(coryats.to_dict('records')[0][1]), format_contestant_name(coryats.to_dict('records')[0][2])]
    weakest_contestant = get_weakest_contestant(coryats, contestants)
    final_jeopardy_responses = tables[-3]
    fj_correct_response = get_fj_correct_response(responses_url)
    # generate clue_json for each category_number and difficulty_level
    jeopardy_clues = []
    double_jeopardy_clues = []
    for category_number in range(0, 6):
        jeopardy_clues.append([])
        double_jeopardy_clues.append([])
        for difficulty_level in range(1, 6):
            jeopardy_clues[category_number].append(get_clue(category_number, difficulty_level, jeopardy_board, jeopardy_responses, 1, contestants))
            double_jeopardy_clues[category_number].append(get_clue(category_number, difficulty_level, double_jeopardy_board, double_jeopardy_responses, 2, contestants))
    return jsonify({
    'contestants': contestants,
    'weakest_contestant': weakest_contestant,
    'jeopardy_round': jeopardy_clues,
    'double_jeopardy_round': double_jeopardy_clues,
    'final_jeopardy': {
        'category': final_jeopardy_category.to_dict('records')[0][0],
        'clue': final_jeopardy_clue.to_dict('records')[0][0],
        'contestant_responses': get_contestant_responses(final_jeopardy_responses.to_dict('records')),
        'correct_response': fj_correct_response
    }})

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
    while parentheses1 >=0 and parentheses2 >= 0:
        string_to_remove = response_string[parentheses1:parentheses2+1]
        response_string = response_string.replace(string_to_remove,'')
        incorrect_responses.append(string_to_remove)
        parentheses1 = response_string.find('(')   
        parentheses2 = response_string.find(')')
    return incorrect_responses


def get_correct_response(response, correct_contestant):
    delimiter = ' '
    if correct_contestant != '':
        correct_response = delimiter.join(response).replace(correct_contestant,'')
    else:
        correct_response = delimiter.join(response)
        correct_response = correct_response.replace('Triple Stumper','')
    return correct_response


def get_response(incorrect_responses, incorrect_contestants, response_string):
    for incorrect_response in incorrect_responses:
        response_string = response_string.replace(incorrect_response,'')
    for contestant in incorrect_contestants:
        response_string = response_string.replace(contestant,'')
    return response_string.split()[2:]


def get_clue_response(response, response_string, contestants):
    correct_contestant = ''
    incorrect_contestants = []
    for contestant in contestants:
        incorrect_response = contestant + ':'
        if incorrect_response in response_string:
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


def get_clue(category_number, difficulty_level, jeopardy_board, jeopardy_responses, round, contestants):
    if (str(jeopardy_board[category_number][difficulty_level]) == 'nan'):
        return {
        'number': '',
        'category': '',
        'value': '',
        'text': '',
        'response': '',
        'daily_double_wager': ''
    }
    clue = jeopardy_board.to_dict('records')[difficulty_level][category_number].split()
    clue_value = clue[0]
    clue_number = clue[1]
    delimiter = ' '
    clue_text = delimiter.join(clue[2:])
    category = jeopardy_board.to_dict('records')[0][category_number]
    if category.find('(') >= 0 and category.find(')') >= 0:
        start_index = category.find('(')
        end_index = category.find(')')
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
        'number': int(clue_number),
        'category': category,
        'value': clue_value,
        'text': clue_text.upper(),
        'response': clue_response,
        'daily_double_wager': daily_double_wager
    }


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