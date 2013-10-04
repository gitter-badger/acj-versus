from __future__ import division
from flask import Flask, url_for, request, render_template, redirect, escape, session, jsonify, Response
from sqlalchemy_acj import init_db, reset_db, db_session, User, Judgement, Script, Course, Question, Enrollment, CommentA, CommentQ, CommentJ, Entry, Tags
from flask_principal import ActionNeed, AnonymousIdentity, Identity, identity_changed, identity_loaded, Permission, Principal, RoleNeed
from sqlalchemy import desc, func, select
from random import shuffle
from math import log10, exp
from pw_hash import PasswordHash
import exceptions
import MySQLdb
import re
import json
import datetime
import validictory
import os
import time
import csv
import string
import random
import time
from threading import Timer
from werkzeug import secure_filename
from flask.ext import sqlalchemy
import Image
'''
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
'''
app = Flask(__name__)
init_db()
hasher = PasswordHash()
principals = Principal(app)

UPLOAD_FOLDER = 'tmp'
UPLOAD_IMAGE_FOLDER = 'static/user_images'
ALLOWED_EXTENSIONS = set(['csv', 'txt'])
ALLOWED_IMAGE_EXTENSIONS = set(['jpg', 'jpeg', 'png', 'gif', 'bmp'])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['UPLOAD_IMAGE_FOLDER'] = UPLOAD_IMAGE_FOLDER

# Needs
is_admin = RoleNeed('Admin')
is_teacher = RoleNeed('Teacher')
is_student = RoleNeed('Student')

# Permissions
admin = Permission(is_admin)
admin.description = "Admin's permissions"
teacher = Permission(is_teacher)
teacher.description = "Teacher's permissions"
student = Permission(is_student)
student.description = "Student's permissions"

apps_needs = [is_admin, is_teacher, is_student]
apps_permissions = [admin, teacher, student]

#user activity
events = {}

class DatetimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
			return obj.strftime("%F %r")
        return json.JSONEncoder.default(self, obj) 

def commit():
	try:
		db_session.commit()
	except:
		db_session.rollback()
		return False
	return True

@app.teardown_appcontext
def shutdown_session(exception=None):
	db_session.remove()

@app.before_request
def registerOnline():
    global events
    if 'username' in session:
        if session['username'] in events:
            ev = events[session['username']]
            ev.cancel()
        ev = Timer(60.0, submitOnline, [session['username'], datetime.datetime.now()])
        events[str(session['username'])] = ev
        ev.start()

def submitOnline(name, time):
    user = User.query.filter_by(username = name).first()
    user.lastOnline = time
    commit()
        
@app.route('/')
def index():
	return redirect(url_for('static', filename="index.html"))

@app.route('/isinstalled')
def is_installed():
	if os.access('tmp/installed.txt', os.F_OK):
		return json.dumps({'installed': True})
	return json.dumps({'installed': False})

@app.route('/install', methods=['GET'])
def install():
	requirements = []
	writable = True if os.access('tmp', os.W_OK) else False
	requirements.append( { 'text': 'tmp folder is writable', 'boolean': writable } )
	return json.dumps( {'requirements': requirements} )

@app.route('/script/<id>', methods=['GET'])
@student.require(http_exception=401)
def get_script(id):
	query = Script.query.filter_by(id = id).first()
	if not query:
		db_session.rollback()
		return json.dumps({"msg": "No matching script"})
	ret_val = json.dumps( {"content": query.content} )    
	db_session.rollback()
	return ret_val

@app.route('/script/<id>', methods=['POST'])
@student.require(http_exception=401)
def mark_script(id):
	query = Script.query.filter_by(id = id).first()
	if not query:
		db_session.rollback()
		return json.dumps({"msg": "No matching script"})
	query.wins = query.wins + 1
	query.count = query.count + 1
	param = request.json
	sidl = param['sidl']
	sidr = param['sidr']
	sid = 0
	if sidl == int(id):
		sid = sidr
	elif sidr == int(id):
		sid = sidl
	query = Script.query.filter_by(id = sid).first()
	query.count = query.count + 1
	estimate_score(query.qid)
	query = User.query.filter_by(username = session['username']).first()
	uid = query.id
	if sidl > sidr:
		temp = sidr
		sidr = sidl
		sidl = temp
	table = Judgement(uid, sidl, sidr, id)
	db_session.add(table)
	commit()
	return json.dumps({"msg": "Script & Judgement updated"})

@app.route('/answer/<id>', methods=['POST'])
@student.require(http_exception=401)
def post_answer(id):
	param = request.json
	schema = {
		'type': 'object',
		'properties': {
			'content': {'type': 'string'}
		}
	}
	try:
		validictory.validate(param, schema)
	except ValueError, error:
		print (str(error))
		return json.dumps( {"msg": str(error)} )
	qid = id
	user = User.query.filter_by(username = session['username']).first()
	uid = user.id
	author = user.display
	content = param['content']
	table = Script(qid, uid, content)
	db_session.add(table)
	db_session.commit()
	script = Script.query.order_by( Script.time.desc() ).first()
	retval = json.dumps({"id": script.id, "author": author, "time": str(script.time), "content": script.content, "score":"{:10.2f}".format(script.score), "avatar": user.avatar, "commentACount": "0"})
	db_session.rollback()
	return retval

@app.route('/answer/<id>', methods=['PUT'])
@student.require(http_exception=401)
def edit_answer(id):
	param = request.json
	schema = {
		'type': 'object',
		'properties': {
			'content': {'type': 'string'}
		}
	}
	try:
		validictory.validate(param, schema)
	except ValueError, error:
		print (str(error))
		return json.dumps( {"msg": str(error)} )
	script = Script.query.filter_by(id = id).first()
	script.content = param['content']
	commit()
	return json.dumps({"msg": "PASS"})

@app.route('/answer/<id>', methods=['DELETE'])
@student.require(http_exception=401)
def delete_answer(id):
	script = Script.query.filter_by(id = id).first()
	db_session.delete(script)
	commit()
	return json.dumps({"msg": "PASS"})

@app.route('/login', methods=['GET'])
def logincheck():
	if 'username' in session:
		user = User.query.filter_by(username = session['username']).first()
		retval = json.dumps( {"id": user.id, "display": user.display, "usertype": user.usertype} )
		db_session.rollback()
		return retval
	return ''

@app.route('/login', methods=['POST'])
def login():
    param = request.json
    username = param['username']
    password = param['password']
    query = User.query.filter_by(username = username).first()
    if not query:
        db_session.rollback()
        return json.dumps( {"msg": 'Incorrect username or password'} )
    hx = query.password
    if hasher.check_password( password, hx ):
        session['username'] = username
        usertype = query.usertype
        display = User.query.filter_by(username = username).first().display
        db_session.rollback()
        identity = Identity('only_' + query.usertype)
        identity_changed.send(app, identity=identity)
        
        return json.dumps( {"display": display, "usertype": usertype} )
    db_session.rollback()
    return json.dumps( {"msg": 'Incorrect username or password'} )

@app.route('/logout')
def logout():
	session.pop('username', None)
	for key in ['identity.name', 'identity.auth_type']:
		session.pop(key, None)
	identity_changed.send(app, identity=AnonymousIdentity())
	return json.dumps( {"status": 'logged out'} )

@app.route('/user/<id>')
def user_profile(id):
    user = ''
    retval = ''
    loggedUser = User.query.filter_by(username = session['username']).first()
    if id == '0':
    	user = loggedUser
    elif id and loggedUser.usertype != 'Student':
        user = User.query.filter_by(id = id).first()
    if user:
    	retval = json.dumps({"username":user.username, "fullname":user.fullname, "display":user.display, "email":user.email, "usertype":user.usertype, "loggedType": loggedUser.usertype, "loggedName": loggedUser.username})
    db_session.rollback()
    return retval

@app.route('/allUsers')
@admin.require(http_exception=401)
def all_users():
	query = User.query.order_by(User.lastname)
	users = []
	for user in query:
		users.append( {"uid": user.id, "username": user.username, "fullname": user.fullname, "display": user.display, "type": user.usertype} )
	db_session.rollback()
	return json.dumps( {'users': users})

@app.route('/admin', methods=['POST'])
def create_admin():
	result = import_users([request.json], False)
	file = open('tmp/installed.txt', 'w+')
	return json.dumps(result)

@app.route('/roles')
@teacher.require(http_exception=401)
def roles():
	query = User.query.filter_by(username = session['username']).first()
	roles = ['Student','Teacher']
	if query.usertype == 'Admin':
		roles.append('Admin')
	return json.dumps({'roles': roles})

@app.route('/user/<id>', methods=['POST'])
@teacher.require(http_exception=401)
def create_user(id):
	result = import_users([request.json], False)
	return json.dumps(result)

@app.route('/user/<id>', methods=['PUT'])
def edit_user(id):
	user = ''
	loggedUser = User.query.filter_by(username = session['username']).first()
	if id == '0':
		user = loggedUser 
	elif id:
		user = User.query.filter_by(id = id).first()
	param = request.json
	schema = {
		'type': 'object',
		'properties': {
			'email': {'type': 'string', 'format': 'email', 'required': False},
			'display': {'type': 'string'},
			'password': {
				'type': 'object', 
				'properties': {
					'old': {'type': 'string'},
					'new': {'type': 'string'},
				},
				'required': False
			},						
		}
	}
	try:
		validictory.validate(param, schema)
	except ValueError, error:
		print (str(error))
		return ''#json.dumps( {"flash": str(error)} )
	display = param['display']
	query = User.query.filter(User.id != user.id).filter_by(display = display).first()
	if query:
		db_session.rollback()
		return json.dumps( {"flash": 'Display name already exists'} )
	user.display = display
	if 'email' in param:
		email = param['email']
		if not re.match(r"[^@]+@[^@]+", email):
			db_session.rollback()
			return json.dumps( {"flash": 'Incorrect email format'} )
		user.email = email
	else:
		user.email = ''
	if 'password' in param:
		if not hasher.check_password( param['password']['old'], user.password ):
			db_session.rollback()
			return json.dumps( {"flash": 'Incorrect password'} )
		newpassword = param['password']['new']
		newpassword = hasher.hash_password( newpassword )
		user.password = newpassword
	usertype = user.usertype
	commit()
	return json.dumps( {"msg": "PASS", "usertype": usertype} )

@app.route('/pickscript/<id>/<sl>/<sr>', methods=['GET'])
@student.require(http_exception=401)
def pick_script(id, sl, sr):
	query = hi_priority_pool(id, 10)
	question = Question.query.filter_by(id = id).first()
	course = Course.query.filter_by(id = question.cid).first()
	if not query:
		retval = json.dumps( {"cid": course.id, "course": course.name, "question": question.content} )
		db_session.rollback()
		return retval
	fresh = get_fresh_pair( query, sl, sr )
	if not fresh:
		retval = json.dumps( {"cid": course.id, "question": question.content, "course": course.name} ) 
		db_session.rollback()
		return retval
	if fresh == 'SAME PAIR':
		db_session.rollback()
		return json.dumps( {"nonew": 'No new pair'} )
	retval = json.dumps( {"cid": course.id, "course": course.name, "question": question.content, "qtitle": question.title, "sidl": fresh[0], "sidr": fresh[1]} )
	db_session.rollback()
	return retval

def hi_priority_pool(id, size):
	script = Script.query.filter_by(qid = id).order_by( Script.count.desc() ).first()
	max = script.count
	script = Script.query.filter_by(qid = id).order_by( Script.count ).first()
	min = script.count
	if max == min:
		max = max + 1
	scripts = Script.query.filter_by(qid = id).order_by( Script.count ).limit( size ).all()
	index = 0
	for script in scripts:
		if script.count >= max:
			scripts[:index]
			break
		index = index + 1
	shuffle( scripts )
	return scripts

@student.require(http_exception=401)
def get_fresh_pair(scripts, cursidl, cursidr):
	uid = User.query.filter_by(username = session['username']).first().id
	samepair = False
	index = 0
	for scriptl in scripts:
		index = index + 1
		if uid != scriptl.uid:
			for scriptr in scripts[index:]:
				if uid != scriptr.uid:
					sidl = scriptl.id
					sidr = scriptr.id
					if sidl > sidr:
						temp = sidr
						sidr = sidl
						sidl = temp
					query = Judgement.query.filter_by(uid = uid).filter_by(sidl = sidl).filter_by(sidr = sidr).first()
					if not query:
						if sidr == int(cursidr) and sidl == int(cursidl):
							samepair = True
							continue
						db_session.rollback()
						return [sidl, sidr]
	db_session.rollback()
	if (samepair):
		return 'SAME PAIR'
	return ''

@app.route('/randquestion')
@student.require(http_exception=401)
def random_question():
    scripts = Script.query.order_by( Script.count ).limit(10).all()
    #if not script:
    #	return ''
    #count = script.count
    #scripts = Script.query.filter_by( count = count ).all()
    #while len(scripts) < 2:
    #	count = count + 1
    #	nextscripts = Script.query.filter_by( count = count).all()
    #	scripts.extend( nextscripts )
    user = User.query.filter_by( username = session['username'] ).first()
    shuffle( scripts )
    lowest0 = ''
    retqid = ''
    lowest1 = ''
    for script in scripts:
        if lowest0 == 0:
        	break
        qid = script.qid
        question = Question.query.filter_by( id = qid ).first()
        if user.usertype != 'Admin':
            enrolled = Enrollment.query.filter_by( cid = question.cid ).filter_by( uid = user.id ).first()
            if not enrolled:
                continue
            if question.quiz:
                answered = Script.query.filter(Script.qid == qid).filter(Script.uid == user.id).first()
                if not answered:
                    continue
        query = Script.query.filter_by(qid = qid).order_by( Script.count ).limit(10).all()
        shuffle( query )
        fresh = get_fresh_pair( query, 0, 0 )
        if fresh:
            sum = Script.query.filter_by(id = fresh[0]).first().count + Script.query.filter_by(id = fresh[1]).first().count
            if lowest0 == '':
            	lowest0 = sum
            	retqid = qid
            else:
            	lowest1 = sum
            	if lowest0 > lowest1:
            		lowest0 = lowest1
            		retqid = qid
    if lowest0 != '':
    	retval = json.dumps( {"question": retqid} )
    	db_session.rollback()
    	return retval
    db_session.rollback()
    return ''

@app.route('/cjmodel')
def produce_cj_model():
	scripts = Script.query.order_by( Script.id ).all()
	index = 0
	for scriptl in scripts:
		lwins = scriptl.wins
		for scriptr in scripts:
			if scriptl != scriptr:
				rwins = scriptr.wins
				odds = (lwins/scriptl.count) / (rwins/scriptr.count) 
				diff = log10( odds )
				table =  CJ_Model(scriptl.id, scriptr.id, diff)
				db_session.add(table)
	commit()
	return '1001110100101010001011010101010'


def estimate_score(id):
	scripts = Script.query.filter_by(qid = id).order_by( Script.id ).all()
	for scriptl in scripts:
		sidl = scriptl.id
		sigma = 0
		lwins = scriptl.wins
		for scriptr in scripts:
			if scriptl != scriptr:
				rwins = scriptr.wins
				if lwins + rwins == 0:
					prob = 0
				else:
					prob = lwins / (lwins + rwins)
				sigma = sigma + prob
		query = Script.query.filter_by(id = sidl).first()
		query.score = sigma
	db_session.commit()
	return '101010100010110'
		
@app.route('/ranking/<id>')
@student.require(http_exception=401)
def marked_scripts(id):
    answered = False
    scripts = Script.query.filter_by(qid = id).order_by( Script.score.desc() ).all() 	
    slst = []
    for script in scripts:
        author = User.query.filter_by(id = script.uid).first()
        commentA = CommentA.query.filter_by(sid = script.id).all()
        slst.append( {"id": script.id, "title": script.title, "author": author.display, "time": str(script.time), "content": script.content, "score": "{:10.2f}".format(script.score), "comments": [], "avatar": author.avatar, "commentACount": len(commentA)} )
        if author.username == session['username']:
            answered = True
    question = Question.query.filter_by(id = id).first()
    course = Course.query.filter_by(id = question.cid).first()
    user = User.query.filter_by(username = session['username']).first()
    userQ = User.query.filter_by(id = question.uid).first()
    commentQ = CommentQ.query.filter_by(qid = question.id).all()
    retval = json.dumps( {"display": user.display, "usertype": user.usertype, "cid": course.id, "course": course.name, 
                          "qtitle": question.title, "question": question.content, "scripts": slst, "commentQCount": len(commentQ), 
                          "authorQ": userQ.display, "timeQ": str(question.time), "avatarQ": userQ.avatar, "answered": answered, "quiz": question.quiz} )
    db_session.rollback()
    return retval

@app.route('/ranking')
@student.require(http_exception=401)
def total_ranking():
	scripts = Script.query.order_by( Script.score.desc() ).all()
	lst = []
	for script in scripts:
		question = Question.query.filter_by(id = script.qid).first()
		course = Course.query.filter_by(id = question.cid).first()
		author = User.query.filter_by(id = script.uid).first().display
		lst.append( {"course": course.name, "question": question.content, "author": author, "time": str(script.time), "content": script.content, "score": "{:10.2f}".format(script.score) } )
	db_session.rollback()
	return json.dumps( {"scripts": lst} )

def get_comments(type, id, sidl=None, sidr=None):
	comments = []
	lst = []
	if (type == 'answer'):
		comments = CommentA.query.filter_by(sid = id).order_by( CommentA.time ).all()
	elif (type == 'question'):
		comments = CommentQ.query.filter_by(qid = id).order_by( CommentQ.time ).all()
	elif (type == 'judgement'):
		comments = CommentJ.query.filter_by(qid = id, sidl = sidl, sidr = sidr).order_by( CommentJ.time ).all()
	for comment in comments:
		author = User.query.filter_by(id = comment.uid).first()
		lst.append( {"id": comment.id, "author": author.display, "time": str(comment.time), "content": comment.content, "avatar": author.avatar} )
	retval = json.dumps( {"comments": lst} )
	db_session.rollback()
	return retval

def make_comment(type, id, content, sidl=None, sidr=None):
	table = ''
	uid = User.query.filter_by(username = session['username']).first().id
	if (type == 'answer'):
		table = CommentA(id, uid, content)
	elif (type == 'question'):
		table = CommentQ(id, uid, content)
	elif (type == 'judgement'):
		table = CommentJ(id, sidl, sidr, uid, content)
	db_session.add(table)
	db_session.commit()
	comment = ''
	if (type == 'answer'):
		comment = CommentA.query.order_by( CommentA.time.desc() ).first()
	elif (type == 'question'):
		comment = CommentQ.query.order_by( CommentQ.time.desc() ).first()
	elif (type == 'judgement'):
		comment = CommentJ.query.order_by( CommentJ.time.desc() ).first()
	author = User.query.filter_by(id = comment.uid).first()
	retval = json.dumps({"comment": {"id": comment.id, "author": author.display, "time": str(comment.time), "content": comment.content, "avatar": author.avatar}})
	db_session.rollback()
	return retval

def edit_comment(type, id, content, sidl=None, sidr=None):
	comment = ''
	if (type == 'answer'):
		comment = CommentA.query.filter_by(id = id).first()
	elif (type == 'question'):
		comment = CommentQ.query.filter_by(id = id).first()
	elif (type == 'judgement'):
		comment = CommentJ.query.filter_by(id = id, sidl = sidl, sidr = sidr).first()
	comment.content = content
	db_session.commit()
	db_session.rollback()
	return json.dumps({"msg": "PASS"})

def delete_comment(type, id, sidl=None, sidr=None):
	comment = ''
	if (type == 'answer'):
		comment = CommentA.query.filter_by(id = id).first()
	elif (type == 'question'):
		comment = CommentQ.query.filter_by(id = id).first()
	elif (type == 'judgement'):
		comment = CommentJ.query.filter_by(id = id, sidl = sidl, sidr = sidr).first()
	db_session.delete(comment)
	commit()
	return json.dumps({"msg": "PASS"})


@app.route('/answer/<id>/comment')
def get_commentsA(id):
	return get_comments('answer', id)


@app.route('/answer/<id>/comment', methods=['POST'])
def comment_answer(id):
	param = request.json
	schema = {
		'type': 'object',
		'properties': {
			'content': {'type': 'string'}
		}
	}
	try:
		validictory.validate(param, schema)
	except ValueError, error:
		print (str(error))
		return json.dumps( {"msg": str(error)} )
	return make_comment('answer', id, param['content'])


@app.route('/answer/<id>/comment', methods=['PUT'])
def edit_commentA(id):
	param = request.json
	schema = {
		'type': 'object',
		'properties': {
			'content': {'type': 'string'}
		}
	}
	try:
		validictory.validate(param, schema)
	except ValueError, error:
		print (str(error))
		return json.dumps( {"msg": str(error)} )
	return edit_comment('answer', id, param['content'])


@app.route('/answer/<id>/comment', methods=['DELETE'])
def delete_commentA(id):
	return delete_comment('answer', id)


@app.route('/question/<id>/comment')
def get_commentsQ(id):
	return get_comments('question', id)


@app.route('/question/<id>/comment', methods=['POST'])
def comment_question(id):
	param = request.json
	schema = {
		'type': 'object',
		'properties': {
			'content': {'type': 'string'}
		}
	}
	try:
		validictory.validate(param, schema)
	except ValueError, error:
		print (str(error))
		return json.dumps( {"msg": str(error)} )
	return make_comment('question', id, param['content'])


@app.route('/question/<id>/comment', methods=['PUT'])
def edit_commentQ(id):
	param = request.json
	schema = {
		'type': 'object',
		'properties': {
			'content': {'type': 'string'}
		}
	}
	try:
		validictory.validate(param, schema)
	except ValueError, error:
		print (str(error))
		return json.dumps( {"msg": str(error)} )
	return edit_comment('question', id, param['content'])

@app.route('/judgepage/<id>/comment/<sidl>/<sidr>')
def get_commentsJ(id, sidl, sidr):
	return get_comments('judgement', id, sidl, sidr)


@app.route('/judgepage/<id>/comment/<sidl>/<sidr>', methods=['POST'])
def comment_judgement(id, sidl, sidr):
	param = request.json
	schema = {
		'type': 'object',
		'properties': {
			'content': {'type': 'string'}
		}
	}
	try:
		validictory.validate(param, schema)
	except ValueError, error:
		print (str(error))
		return json.dumps( {"msg": str(error)} )
	return make_comment('judgement', id, param['content'], sidl, sidr)


@app.route('/judgepage/<id>/comment/<sidl>/<sidr>', methods=['PUT'])
def edit_commentJ(id, sidl, sidr):
	param = request.json
	schema = {
		'type': 'object',
		'properties': {
			'content': {'type': 'string'}
		}
	}
	try:
		validictory.validate(param, schema)
	except ValueError, error:
		print (str(error))
		return json.dumps( {"msg": str(error)} )
	return edit_comment('judgement', id, param['content'], sidl, sidr)


@app.route('/judgepage/<id>/comment/<sidl>/<sidr>', methods=['DELETE'])
def delete_commentJ(id, sidl, sidr):
	return delete_comment('judgement', id, sidl, sidr)


@app.route('/course/<id>', methods=['DELETE'])
def delete_coursae(id):
	course = Course.query.filter_by( id = id).first()
	db_session.delete(course)
	commit()
	return ''

@app.route('/course', methods=['POST'])
@teacher.require(http_exception=401)
def create_course():
	user = User.query.filter_by( username = session['username']).first()
	param = request.json
	course = Course.query.filter_by( name = param['name']).first()
	if course:
		db_session.rollback()
		return json.dumps( {"flash": 'Course name already exists.'} )
	name = param['name']
	newCourse = Course(name)
	db_session.add(newCourse)
	db_session.commit()
	course = Course.query.filter_by( name = name ).first()
	table = Enrollment(user.id, course.id)
	db_session.add(table)
	retval = json.dumps({"id": newCourse.id, "name": newCourse.name})
	commit()
	return retval

@app.route('/course', methods=['GET'])
@student.require(http_exception=401)
def list_course():
    user = User.query.filter_by( username = session['username'] ).first()
    courses = Course.query.order_by( Course.name ).all()
    lst = []
    for course in courses:
        time = None
        if user.usertype != 'Admin':
            query = Enrollment.query.filter_by(cid = course.id).filter_by(uid = user.id).first()
            if not query:
                continue
            else:
                time = str(query.time)
        new = 0
        if user.lastOnline:
            for question in course.question:
                if question.time > user.lastOnline:
                    new += 1
        else:
            new = len(course.question)
        lst.append( {"id": course.id, "name": course.name, "count": len(course.question), "new": new, "time": time} )
    db_session.rollback()
    return json.dumps( {"courses": lst} )

@app.route('/editcourse/<cid>', methods=['GET'])
@teacher.require(http_exception=401)
def get_course(cid):
    course = Course.query.filter_by(id = cid).first()
    taglist = []
    for tag in course.tags:
        taglist.append({"tag": tag.name, "id": tag.id})
    db_session.rollback()
    return json.dumps( {"id": course.id, "name": course.name, "tags": taglist} )

@app.route('/editcourse/<cid>', methods=['PUT'])
@teacher.require(http_exception=401)
def edit_course(cid):
    param = request.json
    schema = {
        'type': 'object',
        'properties': {
            'name': {'type': 'string'}
        }
    }
    try:
        validictory.validate(param, schema)
    except ValueError, error:
        print (str(error))
        return json.dumps( {"msg": str(error)} )
    
    course = Course.query.filter_by(id = cid).first()
    course.name = param['name']
    commit()
    
    retval = json.dumps({"msg": "PASS"})
    return retval

@app.route('/managetag', methods=['POST'])
@teacher.require(http_exception=401)
def add_tag():
    param = request.json
    schema = {
        'type': 'object',
        'properties': {
            'cid': {'type': 'integer'},
            'name': {'type': 'string'}
        }
    }
    try:
        validictory.validate(param, schema)
    except ValueError, error:
        print (str(error))
        return json.dumps( {"msg": str(error)} )
    
    course = Course.query.filter_by(id = param['cid']).first()
    tag = Tags.query.filter_by(name = param['name']).first()
    if not tag:
        tag = Tags(param['name'])
    course.tags.append(tag)
    commit()
    
    taglist = []
    for tag in course.tags:
        taglist.append({"tag": tag.name, "id": tag.id})
    db_session.rollback()
    return json.dumps( {"id": course.id, "name": course.name, "tags": taglist} )

@app.route('/managetag/<cid>/<tid>', methods=['DELETE'])
@teacher.require(http_exception=401)
def remove_tag(cid, tid):
    param = request.json
    course = Course.query.filter_by(id = cid).first()
    tag = Tags.query.filter_by(id = tid).first()
    course.tags.remove(tag)
    commit()
    
    taglist = []
    for tag in course.tags:
        taglist.append({"tag": tag.name, "id": tag.id})
    db_session.rollback()
    return json.dumps( {"id": course.id, "name": course.name, "tags": taglist} )

@app.route('/question/<id>')
@student.require(http_exception=401)
def list_question(id):
    course = Course.query.filter_by(id = id).first()
    questions = Question.query.filter_by(cid = id).order_by( Question.time.desc() ).all()
    lstQuestion = []
    lstQuiz = []
    for question in questions:
        taglistQ = []
        for tag in question.tagsQ:
            taglistQ.append(tag.name)
        author = User.query.filter_by(id = question.uid).first()
        count = Script.query.filter_by(qid = question.id).all()
        if question.quiz:
            user = User.query.filter_by(username = session['username']).first()
            answered = Script.query.filter(Script.qid == question.id).filter(Script.uid == user.id).first()
            lstQuiz.append( {"id": question.id, "author": author.display, "time": str(question.time), "title": question.title, "content": question.content, "avatar": author.avatar, "count": len(count), "answered": answered != None, "tags": taglistQ} )
        else:
            lstQuestion.append( {"id": question.id, "author": author.display, "time": str(question.time), "title": question.title, "content": question.content, "avatar": author.avatar, "count": len(count), "tags": taglistQ} )
    taglist = []
   
    for tag in course.tags:
        taglist.append({"tag": tag.name, "id": tag.id})
    db_session.rollback()
    
    return json.dumps( {"course": course.name, "tags": taglist, "questions": lstQuestion, "quizzes": lstQuiz} )

@app.route('/question/<id>', methods=['PUT'])
def edit_question(id):
    param = request.json
    schema = {
        'type': 'object',
        'properties': {
        	'title': {'type': 'string'},
        	'content': {'type': 'string'},
            'taglist': {'type': 'array'}
        }
    }
    try:
        validictory.validate(param, schema)
    except ValueError, error:
        print (str(error))
        return json.dumps( {"msg": str(error)} )
    question = Question.query.filter_by(id = id).first()
    question.title = param['title']
    question.content = param['content']
    question.tagsQ = []
    for tagname in param['taglist']:
        tag = Tags.query.filter_by(name = tagname).first()
        question.tagsQ.append(tag)
    commit()
    return json.dumps({"msg": "PASS"})

@app.route('/question/<id>', methods=['POST'])
@student.require(http_exception=401)
def create_question(id):
    param = request.json
    schema = {
        'type': 'object',
        'properties': {
            'title': {'type': 'string'},
            'content': {'type': 'string'},
            'type': {'type': 'string'},
            'taglist': {'type': 'array'}
        }
    }
    try:
        validictory.validate(param, schema)
    except ValueError, error:
        print (str(error))
        return json.dumps( {"msg": str(error)} )
    content = param['content']
    title = param['title']
    type = param['type']
    user = User.query.filter_by(username = session['username']).first()
    newQuestion = Question(id, user.id, title, content, type=='quiz')
    db_session.add(newQuestion)
    for id in param['taglist']:
        tag = Tags.query.filter_by(id = id).first()
        newQuestion.tagsQ.append(tag)
    db_session.commit()
    course = Course.query.filter_by(id = id).first()
    retval = json.dumps({"id": newQuestion.id, "author": user.display, "time": str(newQuestion.time), "title": newQuestion.title, "content": newQuestion.content, "avatar": user.avatar, "count": "1" if type=='quiz' else "0", "answered": True})
    db_session.rollback()
    return retval

@app.route('/question/<id>', methods=['DELETE'])
@student.require(http_exception=401)
def delete_question(id):
	question = Question.query.filter_by(id = id).first()
	user = User.query.filter_by(username = session['username']).first()
	if user.id != question.uid and user.usertype != 'Teacher' and user.usertype != 'Admin':
		retval = json.dumps( {"msg": user.display} )
		db_session.rollback()
		return retval
	db_session.delete(question)
	commit()
	return ''

@app.route('/enrollment/<cid>')
@teacher.require(http_exception=401)
def students_enrolled(cid):
	users = User.query.filter((User.usertype == 'Teacher') | (User.usertype == 'Student')).order_by( User.fullname ).all()
	studentlst = []
	teacherlst = []
	for user in users:
		enrolled = ''
		query = Enrollment.query.filter_by(uid = user.id).filter_by(cid = cid).first()
		if (query):
			enrolled = query.id
		if user.usertype == 'Student':
			studentlst.append( {"uid": user.id, "username": user.fullname, "enrolled": enrolled} )
		else:
			teacherlst.append( {"uid": user.id, "username": user.fullname, "enrolled": enrolled} )
	course = Course.query.filter_by(id = cid).first()
	retval = json.dumps( { "course": course.name, "students": studentlst, "teachers": teacherlst } )
	db_session.rollback()
	return retval

@app.route('/enrollment/<cid>', methods=['POST'])
@teacher.require(http_exception=401)
def enroll_student(cid):
	user = {'user': {'id': request.json['uid']}}
	retval = enrol_users([user], cid)
	return json.dumps(retval)

@app.route('/enrollment/<eid>', methods=['DELETE'])
@teacher.require(http_exception=401)
def drop_student(eid):
	query = Enrollment.query.filter_by( id = eid ).first()
	db_session.delete(query)
	commit()
	return json.dumps( {"msg": "PASS"} )

def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def allowed_image_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_IMAGE_EXTENSIONS

@app.route('/userimport', methods=['POST'])
@teacher.require(http_exception=401)
def user_import():
	file = request.files['file']
	if not file or not allowed_file(file.filename):
		return json.dumps( {"completed": True, "msg": "Please provide a valid file"} )
	schema = {
		'type': 'object',
		'properties': {
			'course': {'type': 'string'}
		}
	}
	try:
		validictory.validate(request.form, schema)
	except ValueError, error:
		return json.dumps( {"completed": True} )
	courseId = request.form['course']
	retval = []
	ts = time.time()
	timestamp = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
	filename = timestamp + '-' + secure_filename(file.filename)
	file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
	content = csv_user_parser(os.path.join(app.config['UPLOAD_FOLDER'], filename))
	result = import_users(content['list'])
	enrolled = []
	success = []
	if len(result['success']):
		enrolled = enrol_users(result['success'], courseId)
		success = enrolled['success']
		enrolled = enrolled['error']
	error = result['error'] + enrolled + content['error']
	return json.dumps( {"success": success, "error": error, "completed": True} )

@teacher.require(http_exception=401)
def csv_user_parser(filename):
	reader = csv.reader(open(filename, "rU"))
	list = []
	error = []
	for row in reader:
		# filter removes trailing empty columns in cases where some rows have more than 4 columns
		row = filter(None, row)
		if len(row) != 4:
			error.append({'user': {'username': 'N/A', 'display': 'N/A'}, 'msg': str(row) + ' is an invalid row'})
			continue
		user = {'username': row[0], 'password': password_generator(), 'usertype': 'Student',
			'email': row[3], 'firstname': row[1], 'lastname': row[2], 'display': row[1] + ' ' + row[2]}
		list.append(user)
	return {'list': list, 'error': error}

@teacher.require(http_exception=401)
def password_generator(size=16, chars=string.ascii_uppercase + string.ascii_lowercase + string.digits):
	return ''.join(random.choice(chars) for x in range(size))

def import_users(list, group=True):
	schema = {
		'type': 'object',
		'properties': {
			'username': {'type': 'string'},
			'usertype': {'type': 'string', 'enum': ['Admin', 'Student', 'Teacher']},
			'password': {'type': 'string'},
			'email': {'type': 'string', 'format': 'email', 'required': False},
			'firstname': {'type': 'string'},
			'lastname': {'type': 'string'},
			'display': {'type': 'string'},
		}
	}
	# query all used usernames and displays
	query = User.query.with_entities(User.username).all()
	usernames = [item for sublist in query for item in sublist]
	query = User.query.with_entities(User.display).all()
	displays = [item for sublist in query for item in sublist]
	duplicate = []
	error = []
	success = []
	for user in list:
		try:
			validictory.validate(user, schema)
		except ValueError, err:
			error.append({'user': user, 'msg': str(err), 'validation': True})
			continue
		if user['username'] in duplicate:
			error.append({'user': user, 'msg': 'Duplicate username in file'})
			continue
		if user['username'] in usernames:
			if not group:
				error.append({'user': user, 'msg': 'Username already exists'})
			else:
				u = User.query.filter_by( username = user['username'] ).first()
				if u.usertype == 'Student':
					user = {'id': u.id, 'username': u.username, 'password': 'hidden', 'usertype': 'Student',
						'email': u.email, 'firstname': u.firstname, 'lastname': u.lastname, 'display': u.display}
					duplicate.append(user['username'])
					success.append({'user': user})
				else : 
					error.append({'user': user, 'msg': 'User is not a student'})
			continue
		if user['display'] in displays:
			if not group:
				error.append({'user': user, 'msg': 'Display name already exists'})
				continue
			integer = random.randrange(1000, 9999)
			user['display'] = user['display'] + ' ' + str(integer)
		if 'email' in user:
			email = user['email']
			if not re.match(r"[^@]+@[^@]+", email):
				error.append({'user': user, 'msg': 'Incorrect email format'})
				continue
		else:
			email = ''
		table = User(user['username'], hasher.hash_password(user['password']), user['usertype'], email, user['firstname'], user['lastname'], user['display'])
		db_session.add(table)
		status = commit()
		if not status:
			error.append({'user': user, 'msg': 'Error'})
		else:
			# if successful append usernames + displays to prevent duplicates
			duplicate.append(user['username'])
			displays.append(user['display'])
			user['id'] = table.id
			success.append({'user': user})
	return {'error': error, 'success': success}

@app.route('/password/<uid>')
@admin.require(http_exception=401)
def reset_password(uid):
	user = User.query.filter_by( id = uid ).first()
	password = password_generator()
	user.password = hasher.hash_password( password )
	commit()
	return json.dumps( {"resetpassword": password} )

@app.route('/judgements/<qid>', methods=['GET'])
@student.require(http_exception=401)
def get_judgements(qid):
    judgements = []
    judgement = Judgement.query.filter(Judgement.script1.has(qid = qid)).group_by(Judgement.sidl, Judgement.sidr).add_columns(func.sum(Judgement.winner == Judgement.sidl, type_=None).label('wins_l'), 
                                func.sum(Judgement.winner == Judgement.sidr, type_=None).label('wins_r')).all()
    question = Question.query.filter_by(id = qid).first()
    userQ = User.query.filter_by(id = question.uid).first()
    course = Course.query.filter_by(id = question.cid).first()
    for fullrow in judgement:
        row = fullrow[0]
        user1 = User.query.filter_by(id = row.script1.uid).first()
        user2 = User.query.filter_by(id = row.script2.uid).first()
        commentsCount = CommentJ.query.filter_by(sidl = row.sidl).filter_by(sidr = row.sidr).count()
        judgements.append({"scriptl": row.script1.content, "scriptr": row.script2.content, "winner": row.winner, "wins_l": int(fullrow.wins_l), "wins_r": int(fullrow.wins_r),
                           "sidl": row.sidl, "sidr": row.sidr, "scorel": "{:10.2f}".format(row.script1.score), "scorer": "{:10.2f}".format(row.script2.score), 
                           "authorl": user1.display, "authorr": user2.display, "timel": str(row.script1.time), "timer": str(row.script2.time), 
                           "avatarl": user1.avatar, "avatarr": user2.avatar, "qid": row.script1.qid, "commentsCount": commentsCount})
    ret_val = json.dumps({"judgements": judgements, "title": question.title, "question": question.content, "cid": course.id, "course": course.name,
                          "authorQ": userQ.display, "timeQ": str(question.time), "avatarQ": userQ.avatar})
    db_session.rollback()
    return ret_val

@app.route('/notifications', methods=['GET'])
@student.require(http_exception=401)
def get_notifications():
    user = User.query.filter_by(username = session['username']).first()
    if user.lastOnline is not None:
        scripts = Script.query.join(Question, Script.qid == Question.id).filter(Question.uid == user.id).filter(Script.time > user.lastOnline).all()
        questions = []
        dummy = []
        for answer in scripts:
            if answer.qid not in dummy:
               questions.append({"qid": answer.qid, "title": answer.question.title})
               dummy.append(answer.qid)
        return json.dumps({"count": len(questions), "questions": questions})
    else:
        return json.dumps({"count": 0, "questions": {}})

@app.route('/statistics/<cid>', methods=['GET'])
@teacher.require(http_exception=401)
def get_stats(cid):
    stats = []
    course = Course.query.filter_by(id = cid).first()
    totalQuestionCount = Question.query.filter_by(cid = cid).count()
    totalAnswerCount = Script.query.filter(Script.qid.in_(Question.query.with_entities(Question.id).filter_by(cid = cid))).count()
    studentsInCourse = User.query.join(Enrollment, Enrollment.uid == User.id).filter(Enrollment.cid == cid).filter(User.usertype == 'Student').all()
    for student in studentsInCourse:
        questionCount = Question.query.filter_by(cid = cid).filter_by(uid = student.id).count()
        answerCount = Script.query.filter(Script.qid.in_(Question.query.with_entities(Question.id).filter_by(cid = cid))).filter_by(uid = student.id).count()
        answerAvg = Script.query.with_entities(func.avg(Script.score).label('average')).filter(Script.qid.in_(Question.query.with_entities(Question.id).filter_by(cid = cid))).filter_by(uid = student.id).first()
        stats.append({"totalQuestions": totalQuestionCount, "totalAnswers": totalAnswerCount,"student":{"firstname": student.firstname, "lastname": student.lastname, "questionCount": questionCount, "answerCount": answerCount, "avgScore": answerAvg}})
    return json.dumps({"coursename": course.name, "stats":stats})

@app.route('/uploadimage', methods=['POST'])
@student.require(http_exception=401)
def upload_image():
    file = request.files['file']
    if not file or not allowed_image_file(file.filename):
        return json.dumps( {"completed": True, "msg": "Please provide a valid image file"} )
    #throw exception if its not an image file
    try:
        img = Image.open(file)
    except IOError:
        return json.dumps( {"completed": True, "msg": "Invalid image file"} )    
    #scale the image if necessary
    if img.size[0] > 800 or img.size[1] > 800:
        neww = 0
        newh = 0
        rw = img.size[0] / 800
        rh = img.size[1] / 800
        
        if rw > rh:
            newh = int(round(img.size[1] / rw))
            neww = 800
        else:
            neww = int(round(img.size[0] / rh))
            newh = 800
        img = img.resize((neww,newh), Image.ANTIALIAS)
                        
    retval = []
    ts = time.time()
    timestamp = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d_%H:%M:%S")
    filename = timestamp + '-' + secure_filename(file.filename)
    if not os.path.exists(app.config['UPLOAD_IMAGE_FOLDER']):
        os.makedirs(app.config['UPLOAD_IMAGE_FOLDER'])
    img.save(os.path.join(app.config['UPLOAD_IMAGE_FOLDER'], filename))
    file.close()
    return json.dumps( {"file": filename, "completed": True} )

@teacher.require(http_exception=401)
def enrol_users(users, courseId):
    error = []
    success = []
    enrolled = Enrollment.query.filter_by(cid = courseId).with_entities(Enrollment.uid).all()
    enrolled =  [item for sublist in enrolled for item in sublist]
    for u in users:
        if u['user']['id'] in enrolled:
        	success.append(u)
        	continue
        table = Enrollment(u['user']['id'], courseId)
        db_session.add(table)
        status = commit()
        if status:
        	u['eid'] = table.id
        	success.append(u)
        else:
        	u['msg'] = 'The user is created, but cannot be enrolled'
        	error.append(u)
    return {'error': error, 'success': success}

@app.route('/resetdb')
def resetdb():
    reset_db()
    return ''

@identity_loaded.connect_via(app)
def on_identity_loaded(sender, identity):
	needs = []
	
	if identity.id in ('only_Student', 'only_Teacher', 'only_Admin'):
		needs.append(is_student)
	
	if identity.id in ('only_Teacher', 'only_Admin'):
		needs.append(is_teacher)
	
	if identity.id == 'only_Admin':
		needs.append(is_admin)
	
	for n in needs:
		identity.provides.add(n)

app.secret_key = 'asdf1234'

if __name__=='__main__':
	app.run(debug=True)
	#app.run('0.0.0.0',8080)
