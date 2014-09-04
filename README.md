acj-versus
==========

Introduction
------------
Adaptive Comparative Judgement (ACJ) is based on the law of comparative judgement conceived by L. L. Thurstone in 1927 as a method for psychological measurements.
First used for psychological measurements, today it offers an alternative to marking, especially for performance assessments for which achievement can be difficult to describe in mark schemes and for those where inter-marker reliability is often a problem.

This application is based on an updated 2012 paper which details ACJ's method and history.
Students answer questions asked by instructors or other students and are then able to compare and judge the given answers. From these judgements a score for each answer is calculated according to ACJ's methods.


Frameworks
----------
The frontend is purely written in Javascript, using [AngularJS](http://angularjs.org/) as a MVC-framework and [Bootstrap](http://getbootstrap.com/) for the design.
The backend uses the python web application framework [Flask](http://flask.pocoo.org/) with [Flask SQLAlchemy](http://pythonhosted.org/Flask-SQLAlchemy/] for database persistence.
[Alembic] (http://alembic.readthedocs.org/) is used to maintain database updates.

Developer Installation
----------------------

### Install Dependencies

After running the following command to install the dependencies, a warning is given saying that the pdfjs library is not injected. This has been noted in Issue #79. The temporary solution is to run "git checkout acj/static/index.html".

	make deps

### Vagrant up the VM

	git clone --branch model_refactor git@github.com:ubc/acj-versus.git acj 
	cd acj && vagrant up
	
### Start Up the ACJ server

	vagrant ssh -c "cd /vagrant && make rundev"
	
Now you should be able to open your browser and access ACJ instance using the following address:

	http://localhost:8080/static/index.html#/
	
### Access Database

A MySQL database is installed and the port 3306 is forwarded to host 3306 (in case there is a conflict, vagrant will pick another port, watch for the information when vagrant starts). From host, database can be connect by:

	mysql -u acj -P 3306 -p acj
	
The default password is `acjacj`

If you already have a MySQL server running on your host, you may need to use the following command:

	mysql -u acj --protocol=TCP -P 3306 -p acj

