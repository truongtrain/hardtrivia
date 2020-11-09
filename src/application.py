import pyodbc
import flask
import json
import os

from flask import jsonify

app = flask.Flask("trivia")

@app.route('/question/<num_questions>', methods=['GET'])
def getQuestion(num_questions):
    cnxn = connect_db()
    cursor = cnxn.cursor()
    jsonarray = []
    trivias = load_trivia(cursor, num_questions)
    for trivia in trivias:
        triviajson = json.loads(trivia)
        if not triviajson["class2"]:
            query = "select top(3) Answer from Trivia where Answer in (select Answer from Trivia " \
                    "where Topic = ? and Class1 = ? and Answer != ?) group by Answer order by newid()"
            tuple = (triviajson["topic"], triviajson["class1"], triviajson["correct"])
        else:
            query = "select top(3) Answer from Trivia where Answer in (select Answer from Trivia " \
                    "where Topic = ? and Class1 = ? and Class2 = ? and Answer != ?) group by Answer order by newid()"
            tuple = (triviajson["topic"], triviajson["class1"], triviajson["class2"], triviajson["correct"])
        answers = []
        cursor.execute(query, tuple)
        for row in cursor:
            answers.append(row[0])
        # get more answers if necessary
        if len(answers) < 3:
            additional_answers = get_more_answers(answers, cursor, triviajson["topic"], triviajson["class1"], triviajson["correct"])
            answers = answers + additional_answers
        answers.append(triviajson["correct"])
        answers.sort()
        triviajson["answers"] = answers
        jsonarray.append(triviajson)

    return jsonify({'trivia': jsonarray})


def load_trivia(cursor, num_questions):
    cursor.execute("select top(?) * from Trivia order by newid()", int(num_questions))
    trivias = []
    for row in cursor:
        trivias.append(json.dumps(
            {'correct': row[1],
             'question': str(row[2]).replace("\"", "'"),
             'answers': [],
             'topic': row[3],
             'class1': row[4],
             'class2': row[5]}))
    return trivias


def connect_db():
    driver = os.environ['driver']
    server = os.environ['server']
    database = os.environ['database']
    uid = os.environ['uid']
    pwd = os.environ['pwd']
    cnxn = pyodbc.connect("Driver={%s};"
                          "Server=%s;"
                          "Database=%s;"
                          "uid=%s;"
                          "pwd=%s" % (driver, server, database, uid, pwd))
    return cnxn


def get_more_answers(answers, cursor, topic, class1, answer):
    additional_answers = [];
    numMissing = 3 - len(answers)
    query = "select Answer from Trivia where Answer in (select Answer from Trivia " \
                                              "where Topic = ? and Class1 = ? and Answer != ?) group by Answer order by newid()"
    cursor.execute(query, topic, class1, answer)
    for row in cursor:
        if row[0] != answer and row[0] not in answers:
            additional_answers.append(row[0])
            if len(additional_answers) == numMissing:
                break
    return additional_answers

class Question:
    def __init__(self, question, correct, answers, topic, class1, class2):
        self.question = question
        self.correct = correct
        self.answers = answers
        self.topic = topic
        self.class1 = class1
        self.class2 = class2

app.run()