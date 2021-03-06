"""
    Report Generator
"""
import csv

from flask.ext.script import Manager
from sqlalchemy import and_
from sqlalchemy.orm import aliased

from acj.models import Scores, PostsForAnswers, CriteriaAndPostsForQuestions, Criteria, Posts, Judgements, \
    AnswerPairings, Courses, Users, CoursesAndUsers

manager = Manager(usage="Generate Reports")


@manager.option('-c', '--course', dest='course_id', help='Specify a course ID to generate report from.')
def create(course_id):
    """Creates report"""
    course_name = ''
    if course_id:
        course_name = Courses.query.with_entities(Courses.name).filter_by(id=course_id).scalar()
        if not course_name:
            raise RuntimeError("Course with ID {} is not found.".format(course_id))
        course_name = course_name.replace('"', '')
        course_name += '_'

    query = Scores.query. \
        with_entities(Posts.users_id, CriteriaAndPostsForQuestions.questions_id,
                      PostsForAnswers.id, CriteriaAndPostsForQuestions.id, Criteria.name, Scores.score). \
        join(Scores.answer). \
        join(PostsForAnswers.post). \
        join(Scores.question_criterion).join(CriteriaAndPostsForQuestions.criterion). \
        order_by(CriteriaAndPostsForQuestions.questions_id, CriteriaAndPostsForQuestions.id, Posts.users_id)

    if course_id:
        query = query.filter(Posts.courses_id == course_id)

    scores = query.all()

    write_csv(
        course_name + 'scores.csv',
        ['User Id', 'Question Id', 'Answer Id', 'Criterion Id', 'Criterion', 'Score'],
        scores
    )

    scores2 = aliased(Scores)
    query = Judgements.query. \
        with_entities(Judgements.users_id, CriteriaAndPostsForQuestions.questions_id,
                      CriteriaAndPostsForQuestions.id, Criteria.name,
                      AnswerPairings.answers_id1, Scores.score, AnswerPairings.answers_id2,
                      scores2.score, Judgements.answers_id_winner). \
        join(Judgements.question_criterion).join(CriteriaAndPostsForQuestions.criterion). \
        join(Judgements.answerpairing). \
        join(Scores, and_(Scores.answers_id == AnswerPairings.answers_id1,
                          Scores.criteriaandquestions_id == Judgements.criteriaandquestions_id)). \
        join(scores2, and_(scores2.answers_id == AnswerPairings.answers_id2,
                           scores2.criteriaandquestions_id == Judgements.criteriaandquestions_id)). \
        order_by(CriteriaAndPostsForQuestions.questions_id, CriteriaAndPostsForQuestions.id, Judgements.users_id)

    if course_id:
        query = query. \
            join(Judgements.answer_winner).join(PostsForAnswers.post). \
            filter(Posts.courses_id == course_id)

    comparisons = query.all()

    write_csv(
        course_name + 'comparisons.csv',
        ['User Id', 'Question Id', 'Criterion Id', 'Criterion', 'Answer 1', 'Score 1', 'Answer 2', 'Score 2', 'Winner'],
        comparisons
    )


    query = Users.query. \
        with_entities(Users.id, Users.student_no). \
        order_by(Users.id)

    if course_id:
        query = query. \
            join(Users.coursesandusers). \
            filter(CoursesAndUsers.courses_id == course_id)

    users = query.all()

    write_csv(
            course_name + 'users.csv',
            ['User Id', 'Student #'],
            users
    )

    print('Done.')


def write_csv(filename, headers, data):
    with open(filename, 'wb') as csvfile:
        report_writer = csv.writer(
            csvfile, delimiter=',',
            quotechar='"', quoting=csv.QUOTE_MINIMAL
        )
        report_writer.writerow(headers)
        for d in data:
            report_writer.writerow(d)
