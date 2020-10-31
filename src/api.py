import pyodbc
import flask
import json
import os

app = flask.Flask("trivia")

#get random question
@app.route('/question', methods=['GET'])
def getQuestion():
    return 'hello Alan'
    # driver = os.environ['driver']
    # server = os.environ['server']
    # database = os.environ['database']
    # uid = os.environ['uid']
    # pwd = os.environ['pwd']
    # cnxn = pyodbc.connect("Driver={%s};"
    #                   "Server=%s;"
    #                   "Database=%s;"
    #                   "uid=%s;"
    #                   "pwd=%s" % ( driver, server, database, uid, pwd ))
    # cursor = cnxn.cursor()
    # cursor.execute("select top(1) * from Trivia order by newid()")
    # for row in cursor:
    #     answer = row[1]
    #     question = str(row[2]).replace("\"", "'")
    #     topic = row[3]
    #     class1 = row[4]
    # if row[5] is None:
    #     query = "select top(3) Answer from Trivia where Answer in (select Answer from Trivia " \
    #             "where Topic = ? and Class1 = ? and Answer != ?) group by Answer order by newid()"
    #     tuple = (topic, class1, answer)
    # else:
    #     class2 = row[5]
    #     query = "select top(3) Answer from Trivia where Answer in (select Answer from Trivia " \
    #             "where Topic = ? and Class1 = ? and Class2 = ? and Answer != ?) group by Answer order by newid()"
    #     tuple = (topic, class1, class2, answer)
    # cursor.execute(query, tuple)
    # answers = []
    # for row in cursor:
    #     answers.append(row[0])
    # if len(answers) < 3:
    #     numMissing = 3 - len(answers)
    #     placeholders = ",".join("?" * len(answers))
    #     query = "select top(" + str(numMissing) + ") Answer from Trivia where Answer in (select Answer from Trivia " \
    #             "where Topic = ? and Class1 = ? and Answer != ? and Answer not in (?)) group by Answer order by newid()"
    #     cursor.execute(query, topic, class1, answer, placeholders)
    #     for row in cursor:
    #         answers.append(row[0])
    # return json.dumps({'answer': answer, 'question': question, 'answers': answers})

app.run()