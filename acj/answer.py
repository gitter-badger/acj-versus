from bouncer.constants import CREATE, READ, EDIT
from flask import Blueprint
from flask.ext.bouncer import ensure
from flask.ext.login import login_required, current_user
from flask.ext.restful import Resource, marshal
from flask.ext.restful.reqparse import RequestParser
from acj import dataformat, db
from acj.authorization import require
from acj.models import Posts, PostsForAnswers, PostsForQuestions, Courses, PostsForAnswersAndPostsForComments
from acj.util import new_restful_api

answers_api = Blueprint('answers_api', __name__)
api = new_restful_api(answers_api)

new_answer_parser = RequestParser()
new_answer_parser.add_argument('post', type=dict, default={})

existing_answer_parser = RequestParser()
existing_answer_parser.add_argument('id', type=int, required=True, help="Answer id is required.")
existing_answer_parser.add_argument('post', type=dict, default={})

# /
class AnswerRootAPI(Resource):
	#TODO pagination
	@login_required
	def get(self, course_id, question_id):
		course = Courses.query.get_or_404(course_id)
		question = PostsForQuestions.query.get_or_404(question_id)
		require(READ, question)
		answers = PostsForAnswers.query.join(Posts).\
			filter(PostsForAnswers.postsforquestions_id==question.id).\
			order_by(Posts.created.desc()).all()
		return {"objects":marshal(answers, dataformat.getPostsForAnswers())}

	@login_required
	def post(self, course_id, question_id):
		course = Courses.query.get_or_404(course_id)
		question = PostsForQuestions.query.get_or_404(question_id)
		post = Posts(courses_id=course_id)
		answer = PostsForAnswers(post=post, postsforquestions_id=question_id)
		require(CREATE, answer)
		params = new_answer_parser.parse_args()
		post.content = params.get("post").get("content")
		if not post.content:
			return {"error":"The answer content is empty!"}, 400
		post.users_id = current_user.id
		db.session.add(post)
		db.session.add(answer)
		db.session.commit()
		return marshal(answer, dataformat.getPostsForAnswers())
api.add_resource(AnswerRootAPI, '')

# /id
class AnswerIdAPI(Resource):
	@login_required
	def get(self, course_id, question_id, answer_id):
		course = Courses.query.get_or_404(course_id)
		answer = PostsForAnswers.query.get_or_404(answer_id)
		require(READ, answer)
		return marshal(answer, dataformat.getPostsForAnswers())
	def post(self, course_id, question_id, answer_id):
		course = Courses.query.get_or_404(course_id)
		question = Questions.query.get_or_404(question_id)
		answer = PostsForAnswers.query.get_or_404(answer_id)
		require(EDIT, answer)
		params = existing_answer_parser.parse_args()
		# make sure the answer id in the url and the id matches
		if params['id'] != answer_id:
			return {"error":"Answer id does not match the URL."}, 400
		# modify answer according to new values, preserve original values if values not passed
		answer.post.content = params.get("post").get("content")
		if not answer.post.content:
			return {"error":"The answer content is empty!"}, 400
		db.session.add(answer.post)
		db.session.add(answer)
		db.session.commit()
		return marshal(answer, dataformat.getPostsForAnswers())
api.add_resource(AnswerIdAPI, '/<int:answer_id>')
