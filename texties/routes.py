from texties.models import Texties, AuthenticationTable
from flask import request, session, g, redirect, url_for, abort, \
     render_template, flash, jsonify
from twilio.twiml.messaging_response import MessagingResponse
import random
from texties import app, jwt
from texties import db, client
from texties.models import texties_schema, authentications_schema
import json 
from flask_jwt_extended import create_access_token
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import jwt_required
from werkzeug.exceptions import HTTPException
from texties.parse import Parser
import re
import os
import flask


commands_list = ['weight','note','idea','reminder']
positive_emojis=['ð','ð','ð','ðĨģ','ðŊ','ð','ðĪŠ','ð']
random_positive_emoji= random.randint(0,len(positive_emojis)-1)
phone_num_regex=re.compile(r'((?:\+\d{2}[-\.\s]??|\d{4}[-\.\s]??)?(?:\d{3}[-\.\s]??\d{3}[-\.\s]??\d{4}|\(\d{3}\)\s*\d{3}[-\.\s]??\d{4}|\d{3}[-\.\s]??\d{4}))')


#General Error handler
@app.errorhandler(HTTPException)
def return_error(e):
    """Return JSON instead of HTML for HTTP errors."""
    # start with the correct headers and status code from the error
    response = e.get_response()
    response.headers.add('Access-Control-Allow-Origin', '*')
    # replace the body with JSON
    response.data = json.dumps({
        "code": e.code,
        "name": e.name,
        "description": e.description,
    })
    response.content_type = "application/json"
    return response


#Check phone number validity and change it to E.164 format
def phone_check(number):
    number=number.strip()
    number=(re.sub('[^A-Za-z0-9]+','',number))
    if(number[0]=='1'and len(number)==11):
        number = number[1:]
    if phone_num_regex.match(number) and len(number)==10:
        return "+1"+number
    else:
        return False


@app.route('/')
def index():
    return json.dumps({'Error':'Nothing to look here. Move on chump!'})

#Return access token
@app.route('/token')
def token():
    access_token = create_access_token(identity="test")
    response = json.dumps({'success':True, 'access_token':access_token}), 200, {'ContentType':'application/json'}
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

# Save a textie along with its type
@app.route("/sms", methods=['GET', 'POST'])
def sms_reply():
    body = request.values.get('Body', None)
    phone_number = request.values.get('From', None)
    phone_number = phone_check(phone_number)
    if phone_number==False:
            return json.dumps({'success':False, 'error':'Invalid phone number format'}), 403, {'ContentType':'application/json'}
    resp = MessagingResponse()
    try:
        parser = Parser(body)
        if len(parser.errors) < 1:
            textie_to_db("sms", resp, parser.textie, parser.category, phone_number)    
        else:
            for error in parser.errors:
                resp.message(error)
    except Exception as e:
        resp.message("Looks like I am having some issues textie. Let's try later ðĨš")
    return str(resp)

# Post textie to DB
def textie_to_db(medium, resp, textie, textie_type, phone_number):
    try:
        data = Texties(textie, textie_type, phone_number)
        db.session.add(data)
        db.session.commit()
        if medium == "sms":
            resp.message("Your "+ textie_type+" has been recorded "+positive_emojis[random_positive_emoji])
        else:
            response = flask.jsonify({'some': 'data'})
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.data = json.dumps({
        "success": True,
        "code": 200,
        })
        response.content_type = "application/json"
        return response
    except Exception as e:
        if medium == "sms":
            resp.message("Hmm, that was weird. Let me try to fix that. ð§°")
        else:
            return return_error(e)

# Add textie for web app
@app.route("/add", methods=['GET', 'POST'])
def add():
    try:
        body = str(request.args.get('textie'))
        phone_number=str(request.args.get('phone_number'))
        phone_number = phone_check(phone_number)
        if phone_number==False:
            return json.dumps({'success':False, 'error':'Invalid phone number format'}), 403, {'ContentType':'application/json'}
    except Exception as e:
        return return_error(e)
    try:
        parser = Parser(body)
        if len(parser.errors) < 1:
            res = textie_to_db("web", "", str(parser.textie), str(parser.category), str(phone_number))
            print(res.data)
            # if res.data.success == True:
            #         return json.dumps({'success':True, 'textie':body, }), 403, {'ContentType':'application/json'}
            # else:
            #     return return_error(({"success":False}),res)
        else:
            return_error(parser.errors[0])
    except Exception as e:
        return return_error(e)
    return json.dumps({'success':True, 'textie':body, }), 403, {'ContentType':'application/json'}



# Check phone number and send auth code
@app.route("/auth", methods=['GET', 'POST'])
def auth():
    try:
        phone_number=str(request.args.get('phone_number'))
        phone_number = phone_check(phone_number)
        if phone_number==False:
            return json.dumps({'success':False, 'error':'Invalid phone number format'}), 403, {'ContentType':'application/json'}
        auth_code = str(random.randint(1111,9999))
    except Exception as e:
        return return_error(e)
    try:
        data = AuthenticationTable(auth_code,phone_number)
        db.session.add(data)
        db.session.commit()
        try:
            auth_code = "Here is your Authentication Code: "+auth_code
            message = client.messages.create(
                              body=auth_code,
                              from_='+15126050927',
                              to=phone_number
                          )
        except Exception as e:
            return return_error(e)
    except Exception as e:
        return return_error(e)
    return json.dumps({'success':True}), 200, {'ContentType':'application/json'}

# Check auth code against database for phone number
@app.route("/auth_check", methods=['GET','POST'])
def auth_check():
    try:
        auth_code= str(request.args.get('auth_code'))
        auth_code = auth_code.strip()
        auth_phone_number=str(request.args.get('phone_number'))
        auth_phone_number = phone_check(auth_phone_number)
        if auth_phone_number==False:
            return json.dumps({'success':False, 'error':'Invalid phone number format'}), 403, {'ContentType':'application/json'}
    except Exception as e:
        return return_error(e)
    try:
        response = AuthenticationTable.query.filter_by(phone_number=auth_phone_number).order_by(AuthenticationTable.id.desc()).all()
        if(str(response[0].auth_code) ==  auth_code):
            access_token = create_access_token(identity="test")
            return json.dumps({'success':True, 'access_token':access_token}), 200, {'ContentType':'application/json'}
        else:
            return json.dumps({'success':False, 'Error': 'Auth Code Incorrect'}), 403, {'ContentType':'application/json'}
    except Exception as e:
        return return_error(e)

# Get a type of textie
@app.route("/get", methods=['GET', 'POST'])
def get_weight():
    try:
        type=request.args.get('type')
        phone_number=str(request.args.get('phone_number'))
        phone_number = phone_check(phone_number)
        if phone_number==False:
            return json.dumps({'success':False, 'error':'Invalid phone number format'}), 403, {'ContentType':'application/json'}
        all_texties = Texties.query.filter_by(textie_type=type, phone_number=phone_number).all()
        result = texties_schema.dump(all_texties)
        return jsonify(result)
    except Exception as e:
        return return_error(e)

@app.route("/signup",methods=['GET','POST'])
def signup():
    try:
        phone_number=str(request.args.get('phone_number'))
        phone_number = phone_check(phone_number)
        if phone_number==False:
            return json.dumps({'success':False, 'error':'Invalid phone number format'}), 403, {'ContentType':'application/json'}
        try:
            # welcome_message="hey"
            welcome_message = "Welcome to texties! \nYou can save your notes by texting me anytime. To learn more reply with --help"
            message = client.messages.create(
                                body=welcome_message,
                                from_='+15126050927',
                                to=phone_number
                            ) 
            samples = 'Here are some sample texts you can send me.\n\n\nnote: Return library card\n\nidea: Create a meowCoin ððŠ\n\nweight: 145lbs'
            message = client.messages.create(
                                body=samples,
                                from_='+15126050927',
                                to=phone_number
                            )
            return json.dumps({'success':True}), 200, {'ContentType':'application/json'}
        except Exception as e:
            return return_error(e)
    except Exception as e:
        return return_error(e)



# Search for a type of textie
@app.route("/search", methods=['GET', 'POST'])
def search():
    try:
        type=request.args.get('type')
        search_text=request.args.get('search_text')
        phone_number=str(request.args.get('phone_number'))
        phone_number = phone_check(phone_number)
        if phone_number==False:
            return json.dumps({'success':False, 'error':'Invalid phone number format'}), 403, {'ContentType':'application/json'}
        all_texties = Texties.query.filter(Texties.textie.contains(search_text)).filter_by(textie_type=type, phone_number=phone_number).all()
        result = texties_schema.dump(all_texties)
        return jsonify(result)
    except Exception as e:
        return return_error(e)

# Delete a textie from the database
@app.route("/delete_texties", methods=['GET','TYPE'])
def delete_texties():
    delete_key_args=request.args.get('delete_key')
    delete_key = os.environ.get('DELETE_KEY','asdnaksjdnakjsdnalksdnadlaksndlakjsfowjhgskdjbsihbg')
    if delete_key_args == delete_key:
        try:
            returned = Texties.query.delete()
            print(returned)
            return json.dumps({'success':True, returned:{jsonify(returned)}}), 200, {'ContentType':'application/json'}
        except Exception as e:
            return return_error(e)
    else:
        return json.dumps({'success':False, 'Error': "Incorrect Delete Key"}), 403, {'ContentType':'application/json'}

# Delete a textie from database
@app.route("/delete", methods=['GET','POST'])
def delete():
    try:
        delete_id=int(request.args.get('id'))
    except Exception as e:
        return return_error(e)
    try:
        returned = Texties.query.filter_by(id=delete_id).first()
        db.session.delete(returned)
        db.session.commit()
        return json.dumps({'success':True}), 200, {'ContentType':'application/json'}
    except Exception as e:
        return return_error(e)

# Update a textie in the database
@app.route("/update", methods=['GET','POST'])
def update():
    try:
        update_id=request.args.get('id')
        update_textie=request.args.get('textie')
    except Exception as e:
        return return_error(e)
    try:
        resp = Texties.query.filter_by(id=update_id).first()
        resp.textie = update_textie
        db.session.commit()
        return json.dumps({'success':True, 'snackBar':"Textie Updated"}), 200, {'ContentType':'application/json'}
    except Exception as e:
        return return_error(e)


# Delete auth codes from the database
@app.route("/delete_authentication", methods=['GET','TYPE'])
def delete_authentication():
    delete_key_args=request.args.get('delete_key')
    delete_key = os.environ.get('DELETE_KEY','asdnaksjdnakjsdnalksdnadlaksndlakjsfowjhgskdjbsihbg')
    if delete_key_args == delete_key:
        try:
            returned = AuthenticationTable.query.delete()
            print(returned)
            return json.dumps({'success':True}), 200, {'ContentType':'application/json'}
        except Exception as e:
            return return_error(e)
    else:
        return json.dumps({'success':False, 'Error': "Incorrect Delete Key"}), 403, {'ContentType':'application/json'}
