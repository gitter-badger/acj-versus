"""
	Database Manager, manipulate the database from commandline
"""

from flask.ext.script import Manager, prompt_bool
from acj.core import db

manager = Manager(usage="Perform database operations")


@manager.command
def drop():
	"""Drops database tables"""
	if prompt_bool("Are you sure you want to lose all your data"):
		db.drop_all()
		print ('All tables are dropped.')
		return True

	return False


@manager.command
def create(default_data=True, sample_data=False):
	"""Creates database tables from sqlalchemy models"""
	db.create_all()
	populate(default_data, sample_data)
	print ('All tables are created and data is loaded.')


@manager.command
def recreate(default_data=True, sample_data=False):
	"""Recreates database tables (same as issuing 'drop' and then 'create')"""
	print ("Resetting database state...")
	if drop():
		create(default_data, sample_data)


@manager.command
def populate(default_data=False, sample_data=False):
	"""Populate database with default data"""
	from data.fixtures import get_dbfixture, all_data

	if default_data:
		#from fixtures.default_data import all

		fixture_data = get_dbfixture(db).data(*all_data)

	if sample_data:
		#from fixtures.sample_data import all

		fixture_data = get_dbfixture(db).data(*all_data)

	fixture_data.setup()

	return fixture_data