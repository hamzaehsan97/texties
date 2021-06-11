# -*- coding: utf-8 -*-
from typing import Text
from twilio.rest import Client
from flask import Flask, Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash
from twilio.twiml.messaging_response import MessagingResponse
from flask_sqlalchemy import SQLAlchemy
import datetime
import random
from dotenv import load_dotenv
import os
from os.path import join, dirname



app = Flask(__name__)
#If sms is received twilio will hit this function with the message
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

ENV = 'prod'
if ENV == 'dev':
    app.debug = True
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DEV_DATABASE_URL")
else:
    app.debug=False
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("PROD_DATABASE_URL")
db = SQLAlchemy(app)
class Texties(db.Model):
    __tablename__='texties_table'
    id = db.Column(db.Integer, primary_key=True)
    textie_type = db.Column(db.String(50))
    textie = db.Column(db.String(600))
    phone_number = db.Column(db.String(15))
    created_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)


    def __init__(self, textie, textie_type, phone_number):
        self.textie = textie
        self.textie_type = textie_type
        self.phone_number = phone_number

@app.route('/')
def index():
    return render_template("index.html")


commands_list = ['weight','note','idea','reminder']
positive_emojis=['🙌','📝','🎉','🥳','👯','🎊','🤪','👌']
random_positive_emoji= random.randint(0,len(positive_emojis)-1)


@app.route("/sms", methods=['GET', 'POST'])
def sms_reply():
    print(random_positive_emoji)
    body = request.values.get('Body', None)
    phone_number = request.values.get('From', None)
    resp = MessagingResponse()
    try:
        body_split = body.split(':')
        if(len(body_split)<2):
            command = "none"
        else:
            command = body_split[0]
            command = command.strip()
            command = command.lower()
            command_body = body_split[1]
        if command in commands_list:
            #save weight
            try:
                textie = str(command_body)
                textie_type = command
                data = Texties(textie, textie_type, phone_number)
                db.session.add(data)
                db.session.commit()
                resp.message("Your "+ command+" has been recorded "+positive_emojis[random_positive_emoji])
            except Exception as e:
                print(e)
                resp.message("Hmm, that was weird. Let me try to fix that. 🧰")
        else:
            resp.message("Hmm, textie i don't understand 😕. \n Here are the commands i understand for now (note, weight, reminder, idea)")
    except Exception as e:
        resp.message("Looks like I am having some issues textie. Let's try later 🥺")

    return str(resp)

if __name__ == "__main__":
    app.run()

# @app.route("/get/weight", methods=['GET', 'POST'])
# def get_weight():
#     cur = get_db().cursor()
#     cur.execute('SELECT * from weights')
#     rows = cur.fetchall()
#     weights = ""
#     for row in rows:
#         weights = weights + "Phone number = "+str(row[1])+" weight = "+str(row[2]) + "\n"
#     return weights

# @app.route("/get/notes", methods=['GET', 'POST'])
# def get_notes():
#     cur = get_db().cursor()
#     cur.execute('SELECT * from notes')
#     rows = cur.fetchall()
#     notes = ""
#     for row in rows:
#         notes = notes + "Phone number = "+str(row[1])+" note = "+str(row[2]) + "\n"
#     return notes
        


# def get_db():
#     db = getattr(g, '_database', None)
#     if db is None:
#         db = g._database = sqlite3.connect(DATABASE)
#     return db

# @app.teardown_appcontext
# def close_connection(exception):
#     db = getattr(g, '_database', None)
#     if db is not None:
#         db.close()


