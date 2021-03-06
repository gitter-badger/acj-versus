// Use the external Chai As Promised to deal with resolving promises in
// expectations.
var chai = require('chai');
var chaiAsPromised = require('chai-as-promised');
chai.use(chaiAsPromised);

var expect = chai.expect;

var PageFactory  = require('../../factories/page_factory.js');
var UserFactory  = require('../../factories/user_factory.js');
var backEndMocks = require('../../factories/http_backend_mocks.js');

var commonStepDefinitionsWrapper = function() {
	var pageFactory = new PageFactory();
	var userFactory = new UserFactory();
	var mocks = [
		backEndMocks.session,
		backEndMocks.user,
		backEndMocks.course,
		backEndMocks.question
	];

	// login and setup mock backend
	this.Given(/^I'm "([^"]*)"$/, function (username, done) {
		backEndMocks.build(browser, mocks);
		var loginDialog = pageFactory.createPage('login');
		loginDialog.get('/');
		loginDialog.login(userFactory.getUser(username)).then(function() {
			// wait for displayname is populated before we reload the page
			browser.wait(browser.isElementPresent(element(by.binding('loggedInUser.displayname'))), 5000);
			done();
		});
	});

	// check title of page
	this.Then(/^"([^"]*)" page should load$/, function (content_title, done) {
		expect($("#view-title").getText()).to.eventually.equal(content_title).and.notify(done);
	});

	// fill in form
	this.Given(/^I fill in:$/, function (data, done) {
		var list = data.hashes();
		for (var i = 0; i < list.length; i++) {
			element(by.model(list[i].element)).sendKeys(list[i].content);
		}
		done();
	});
};
module.exports = commonStepDefinitionsWrapper;