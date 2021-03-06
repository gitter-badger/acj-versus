describe('ACJ testsuite - Student', function() {
	var rootURL = "/static/index.html#";
	var reset = false;
	
	beforeEach(function() {
		if (!reset) {
			browser().navigateTo('/resetdb');
            reset = true;
        }
	});
	
	describe('questions', function() {
		it('user is logged in', function() {
			browser().navigateTo(rootURL + '/login');
			input('username').enter('testuser');
		    input('password').enter('demo');
		    element('.btn.btn-primary').click();
			expect(browser().location().url()).toBe('/');
		});
		it('go to question page', function() {
			element('#step2').click();
			expect(browser().location().url()).toMatch(/\/questionpage\/./);
		});
		it('create question', function() {
			var qCount = repeater("ul.postingsList.padding0 li").count();
			qCount.execute(function(){});
			input('title').enter("unittestquiz");
			contenteditable('div[name="question"]').enter('unit test question');
			contenteditable('div[name="answerq"]').enter('unit test answer');
			element(".btn.btn-primary:first").click();
			expect(repeater("ul.postingsList.padding0 li").count()).toBe(qCount.value + 1);
		});
		it('delete the created question', function() {
			var qCount = repeater("ul.postingsList.padding0 li").count();
			qCount.execute(function(){});
			confirmOK();
			element("a.btn.btn-danger.btn-sm.btnWidth:first").click();
			expect(repeater("ul.postingsList.padding0 li").count()).toBe(qCount.value - 1);
		});
	});
	
	describe('answers', function() {
		it('go to answer page', function() {
			element('a[ng-click="setType(\'discussion\');switchEdits(-1)"]').click();
			element('#stepAnswer:first').click();
			expect(browser().location().url()).toMatch(/\/answerpage\/./);
		});
		it('create answer', function() {
			var qCount = repeater("ul.postingsList.padding0 li").count();
			qCount.execute(function(){});
			contenteditable('div[name="answer"]').enter('unit test answer');
			element("a[ng-click='submit();submitted=true']").click();
			expect(repeater("ul.postingsList.padding0 li").count()).toBe(qCount.value + 1);
		});
		it('delete the created answer', function() {
			var qCount = repeater("ul.postingsList.padding0 li").count();
			qCount.execute(function(){});
			confirmOK();
			element("a.btn.btn-danger.btn-sm.btnWidth:first").click();
			expect(repeater("ul.postingsList.padding0 li").count()).toBe(qCount.value - 1);
		});
		it('return to question page', function() {
			element('a[href^="#/questionpage/"]').click();
			expect(browser().location().url()).toMatch(/\/questionpage\/./);
		});
	});
	describe('judge', function() {
		it('random judge', function() {
			element('a[href="#/quickjudge"]').click();
			element('#stepNext').click();
			element("div[ng-click=\"sideSelect($index, \'right\', crit.id);pick=\'right\'\"]").click();
			element("#stepSubmit").click();
			expect(element("li.alert.alert-success.text-center").text()).toBe("Script & Judgement updated");
		});
		it('judge answers', function() {
			element('a[ng-click="setType(\'discussion\');switchEdits(-1)"]').click();
			element('a#stepJudge:not(.ng-hide):first').click();
			element("div[ng-click=\"sideSelect($index, \'left\', crit.id);pick=\'left\'\"]").click();
			element("#stepSubmit").click();
			expect(element("li.alert.alert-success.text-center").text()).toBe("Script & Judgement updated");
		});
		it('user is logged out', function() {
			element('.dropdown-menu:last-child a').click();
			expect(browser().location().url()).toBe('/login');
			reset = false;
		});
	});
});
