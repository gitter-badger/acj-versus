from flask import Flask, redirect, session, abort, jsonify
from flask.ext.login import current_user
from sqlalchemy.orm import joinedload

from .answer import on_answer_modified, on_answer_get, on_answer_list_get, on_answer_create, on_answer_flag, \
    on_answer_delete, on_user_question_answer_get, on_user_question_answered_count, on_user_course_answered_count, \
    on_answer_view_count
from .attachment import on_save_tmp_file, on_attachment_get, on_attachment_delete
from .classlist import on_classlist_get, on_classlist_upload, on_classlist_enrol, on_classlist_unenrol, \
    on_classlist_instructor_label, on_classlist_instructor, on_classlist_student
from .comment import on_comment_modified, on_comment_get, on_comment_list_get, on_comment_create, on_comment_delete, \
    on_answer_comment_modified, on_answer_comment_get, on_answer_comment_list_get, on_answer_comment_create, \
    on_answer_comment_delete, on_answer_comment_user_get
from .course import on_course_modified, on_course_get, on_course_list_get, on_course_create
from .criteria import on_criteria_list_get, criteria_get, criteria_post, criteria_update, \
    accessible_criteria, criteria_create, default_criteria_get, on_course_criteria_delete, \
    on_course_criteria_update, on_question_criteria_create, on_question_criteria_delete, \
    on_question_criteria_get
from .evalcomment import on_evalcomment_create, on_evalcomment_get, on_evalcomment_view, on_evalcomment_view_my
from .judgement import on_answer_pair_get, on_judgement_create, on_judgement_question_count, \
    on_judgement_course_count
from .question import on_question_modified, on_question_get, on_question_list_get, on_question_create, \
    on_question_delete
from .report import on_export_report
from .gradebook import on_gradebook_get
from .group import on_group_create, on_group_delete, on_group_course_get, on_group_import, on_group_get, \
    on_group_user_create, on_group_user_delete
from .selfeval import selfevaltype_get, selfeval_course_acomment_count
from acj.users import on_user_modified, on_user_get, on_user_list_get, on_user_create, on_user_course_get, \
    on_user_password_update, on_user_types_all_get, on_instructors_get, on_course_roles_all_get, on_users_display_get, \
    on_teaching_course_get, on_user_edit_button_get
from .authorization import define_authorization
from .core import login_manager, bouncer, db, cas
from .configuration import config
from .models import Users
from .activity import log


def create_app(conf=config, settings_override=None):
    """Return a :class:`Flask` application instance

    :param settings_override: override the default settings or settings in the configuration file
    """
    if settings_override is None:
        settings_override = {}
    app = Flask(__name__)
    app.config.update(conf)
    app.config.update(settings_override)

    app.logger.debug("Application Configuration: " + str(app.config))

    db.init_app(app)

    # Flask-Login initialization
    login_manager.init_app(app)

    # This is how Flask-Login loads the newly logged in user's information
    @login_manager.user_loader
    def load_user(user_id):
        app.logger.debug("User logging in, ID: " + user_id)
        return Users.query. \
            options(joinedload("usertypeforsystem")). \
            options(joinedload("coursesandusers").joinedload("usertypeforcourse")). \
            get(int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        if 'CAS_AUTH_MSG' in session:
            msg = session.pop('CAS_AUTH_MSG')
            response = jsonify({'message': msg, 'status': 403, 'type': 'CAS'})
            response.status_code = 403
            return response
        return abort(401)

    cas.init_app(app)

    # Flask-Bouncer initialization
    bouncer.init_app(app)

    # Assigns permissions to the current logged in user
    @bouncer.authorization_method
    def bouncer_define_authorization(user, they):
        define_authorization(user, they)

    # Loads the current logged in user. Note that although Flask-Bouncer advertises
    # compatibility with Flask-Login, it looks like it's compatible with an older
    # version than we're using, so we have to override their loader.
    @bouncer.user_loader
    def bouncer_user_loader():
        return current_user

    # Initialize rest of the api modules
    from .course import courses_api

    app.register_blueprint(courses_api, url_prefix='/api')
    from .classlist import classlist_api

    app.register_blueprint(classlist_api, url_prefix='/api/courses/<int:course_id>/users')
    from .group import groups_api, groups_users_api

    app.register_blueprint(groups_api, url_prefix='/api/courses/<int:course_id>/groups')
    app.register_blueprint(groups_users_api, url_prefix='/api/courses/<int:course_id>/users/<int:user_id>/groups')
    from .login import login_api

    app.register_blueprint(login_api)
    from .users import users_api, user_types_api, user_course_types_api

    app.register_blueprint(users_api, url_prefix='/api/users')
    app.register_blueprint(user_types_api, url_prefix='/api/usertypes')
    app.register_blueprint(user_course_types_api, url_prefix='/api/courseroles')
    from .question import questions_api

    app.register_blueprint(questions_api, url_prefix='/api/courses/<int:course_id>/questions')
    from .answer import answers_api, all_answers_api

    app.register_blueprint(
        answers_api,
        url_prefix='/api/courses/<int:course_id>/questions/<int:question_id>/answers')
    app.register_blueprint(
        all_answers_api,
        url_prefix='/api/courses/<int:course_id>/answers')
    from .attachment import attachment_api

    app.register_blueprint(
        attachment_api,
        url_prefix='/api/attachment')
    from .comment import commentsforquestions_api, commentsforanswers_api

    app.register_blueprint(
        commentsforquestions_api,
        url_prefix='/api/courses/<int:course_id>/questions/<int:question_id>/comments')
    app.register_blueprint(
        commentsforanswers_api,
        url_prefix='/api/courses/<int:course_id>/questions/<int:question_id>')
    from .evalcomment import evalcomments_api

    app.register_blueprint(
        evalcomments_api,
        url_prefix='/api/courses/<int:course_id>/questions/<int:question_id>/judgements/comments')
    from .criteria import coursescriteria_api, criteria_api, questionscriteria_api

    app.register_blueprint(coursescriteria_api, url_prefix='/api/courses/<int:course_id>/criteria')
    app.register_blueprint(criteria_api, url_prefix='/api/criteria')
    app.register_blueprint(
        questionscriteria_api,
        url_prefix='/api/courses/<int:course_id>/questions/<int:question_id>/criteria')
    from .judgement import judgements_api, all_judgements_api

    app.register_blueprint(
        judgements_api,
        url_prefix='/api/courses/<int:course_id>/questions/<int:question_id>/judgements')
    app.register_blueprint(
        all_judgements_api,
        url_prefix='/api/courses/<int:course_id>/judgements')
    from .answerpairing import answerpairing_api

    app.register_blueprint(
        answerpairing_api,
        url_prefix='/api/courses/<int:course_id>/questions/<int:question_id>/answerpairing')
    from .report import report_api

    app.register_blueprint(report_api, url_prefix='/api/courses/<int:course_id>/report')
    from .gradebook import gradebook_api

    app.register_blueprint(
        gradebook_api,
        url_prefix='/api/courses/<int:course_id>/questions/<int:question_id>/gradebook')
    from .selfeval import selfeval_api, selfeval_acomments_api

    app.register_blueprint(selfeval_api, url_prefix='/api/selfevaltypes')
    app.register_blueprint(selfeval_acomments_api, url_prefix='/api/selfeval/courses/<int:course_id>/questions')
    from .common import timer_api

    app.register_blueprint(timer_api, url_prefix='/api/timer')

    @app.route('/')
    def route_root():
        return redirect('/static/index.html#/')

    return app


# user events
on_user_modified.connect(log)
on_user_get.connect(log)
on_user_list_get.connect(log)
on_user_create.connect(log)
on_user_course_get.connect(log)
on_user_edit_button_get.connect(log)
on_user_password_update.connect(log)
on_teaching_course_get.connect(log)

on_user_types_all_get.connect(log)
on_instructors_get.connect(log)

on_course_roles_all_get.connect(log)
on_users_display_get.connect(log)

# course events
on_course_modified.connect(log)
on_course_get.connect(log)
on_course_list_get.connect(log)
on_course_create.connect(log)

# question events
on_question_modified.connect(log)
on_question_get.connect(log)
on_question_list_get.connect(log)
on_question_create.connect(log)
on_question_delete.connect(log)

# comment events
on_comment_modified.connect(log)
on_comment_get.connect(log)
on_comment_list_get.connect(log)
on_comment_create.connect(log)
on_comment_delete.connect(log)

# answer comment events
on_answer_comment_modified.connect(log)
on_answer_comment_get.connect(log)
on_answer_comment_list_get.connect(log)
on_answer_comment_create.connect(log)
on_answer_comment_delete.connect(log)
on_answer_comment_user_get.connect(log)
on_answer_view_count.connect(log)

# criteria events
on_criteria_list_get.connect(log)
criteria_get.connect(log)
criteria_post.connect(log)
criteria_update.connect(log)

accessible_criteria.connect(log)
criteria_create.connect(log)
default_criteria_get.connect(log)

on_course_criteria_delete.connect(log)
on_course_criteria_update.connect(log)

# question criteria events
on_question_criteria_create.connect(log)
on_question_criteria_delete.connect(log)
on_question_criteria_get.connect(log)

# answer events
on_answer_modified.connect(log)
on_answer_get.connect(log)
on_answer_list_get.connect(log)
on_answer_create.connect(log)
on_answer_flag.connect(log)
on_answer_delete.connect(log)
on_user_question_answer_get.connect(log)
on_user_question_answered_count.connect(log)
on_user_course_answered_count.connect(log)

# judgement events
on_answer_pair_get.connect(log)
on_judgement_create.connect(log)
on_judgement_question_count.connect(log)
on_judgement_course_count.connect(log)

# classlist events
on_classlist_get.connect(log)
on_classlist_upload.connect(log)
on_classlist_enrol.connect(log)
on_classlist_unenrol.connect(log)
on_classlist_instructor_label.connect(log)
on_classlist_instructor.connect(log)
on_classlist_student.connect(log)

# group events
on_group_create.connect(log)
on_group_delete.connect(log)
on_group_course_get.connect(log)
on_group_import.connect(log)
on_group_get.connect(log)

# group users events
on_group_user_create.connect(log)
on_group_user_delete.connect(log)

# evalcomment event
on_evalcomment_create.connect(log)
on_evalcomment_get.connect(log)
on_evalcomment_view.connect(log)
on_evalcomment_view_my.connect(log)

# report event
on_export_report.connect(log)

# attachment event
on_save_tmp_file.connect(log)
on_attachment_get.connect(log)
on_attachment_delete.connect(log)

# gradebook event
on_gradebook_get.connect(log)

# selfeval event
selfevaltype_get.connect(log)
selfeval_course_acomment_count.connect(log)
