import pyodbc
import flask
import json
import os

from flask import jsonify

app = flask.Flask("trivia")

@app.route('/question/<num_questions>', methods=['GET'])
def getQuestion(num_questions):
    numQuestions = num_questions
    driver = os.environ['driver']
    server = os.environ['server']
    database = os.environ['database']
    uid = os.environ['uid']
    pwd = os.environ['pwd']
    cnxn = pyodbc.connect("Driver={%s};"
                      "Server=%s;"
                      "Database=%s;"
                      "uid=%s;"
                      "pwd=%s" % ( driver, server, database, uid, pwd ))
    cursor = cnxn.cursor()
    cursor.execute("select top(10) * from Trivia order by newid()")
    trivias = []
    jsonarray = []
    for row in cursor:
        trivia = Question
        trivia.correct = row[1]
        trivia.question = str(row[2]).replace("\"", "'")
        trivia.topic = row[3]
        trivia.class1 = row[4]
        if row[5] is not None:
            trivia.class2 = row[5]
        trivias.append(trivia)
        #correct = row[1]
        #question = str(row[2]).replace("\"", "'")
        #topic = row[3]
        #class1 = row[4]

    for trivia in trivias:
        if trivia.class2 is None:
            query = "select top(3) Answer from Trivia where Answer in (select Answer from Trivia " \
                    "where Topic = ? and Class1 = ? and Answer != ?) group by Answer order by newid()"
            tuple = (trivia.topic, trivia.class1, trivia.correct)
        else:
            #class2 = row[5]
            query = "select top(3) Answer from Trivia where Answer in (select Answer from Trivia " \
                    "where Topic = ? and Class1 = ? and Class2 = ? and Answer != ?) group by Answer order by newid()"
            tuple = (trivia.topic, trivia.class1, trivia.class2, trivia.correct)
        cursor.execute(query, tuple)
        answers = []
        for row in cursor:
            answers.append(row[0])
        # get more answers if necessary
        if len(answers) < 3:
            getMoreAnswers(answers, cursor, trivia.topic, trivia.class1, trivia.correct)
        triviajson = json.dumps({'correct': trivia.correct, 'question': trivia.question, 'answers': answers})
        jsonarray.append(triviajson)

    return jsonify({'trivia': jsonarray})

def getMoreAnswers(answers, cursor, topic, class1, answer):
    numMissing = 3 - len(answers)
    placeholders = ",".join("?" * len(answers))
    query = "select top(" + str(numMissing) + ") Answer from Trivia where Answer in (select Answer from Trivia " \
                                              "where Topic = ? and Class1 = ? and Answer != ? and Answer not in (?)) group by Answer order by newid()"
    cursor.execute(query, topic, class1, answer, placeholders)
    for row in cursor:
        answers.append(row[0])

class Question:
    def __init__(self, question, correct, answers, topic, class1, class2):
        self.question = question
        self.correct = correct
        self.answers = answers
        self.topic = topic
        self.class1 = class1
        self.class2 = class2

app.run()