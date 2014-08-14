// Login/logout controllers

// Isolate this module's creation by putting it in an anonymous function
(function() {

var module = angular.module('ubc.ctlt.acj.login',
	[
		'ngAnimate',
		'ngResource',
		'ngRoute',
		'mgcrea.ngStrap',
		'ubc.ctlt.acj.authentication',
		'ubc.ctlt.acj.authorization',
		'ubc.ctlt.acj.user'
	]
);

/***** Providers *****/
module.factory('LoginResource', function($resource) {
	return $resource(
		'/login/:operation',
		{},
		{
			login: { method:'POST', params: {operation: "login"} },
			logout: { method:'DELETE', params: {operation: "logout"} }
		}
	);
});

/***** Directives *****/
// TODO this might be useful elsewhere, if we need to autofocus something
// html5 property autofocus behaves differently on Firefox than in Chrome, in Firefox
// it only works before onload, so it doesn't do anything if we pop the login modal
// after the entire page has been loaded.
// The timeout forces a wait for the loginbox to be rendered.
module.directive('autoFocus', function($timeout, $log) {
    return {
        restrict: 'AC',
        link: function(scope, _element, attr) {
            $timeout(function(){
                _element[0].focus();
            }, 100);
        }
    };
});

/***** Listeners *****/
// display the login page if user is not logged in
module.run(function ($rootScope, $route, $location, $log, $modal, AuthenticationService) {
	// Create a modal dialog box for containing the login form
	var loginBox = $modal(
		{
			rootScope: $rootScope,
			contentTemplate: 'modules/login/login-partial.html',
			backdrop: 'static', // can't close login on backdrop click
			keyboard: false, // can't close login on pressing Esc key
			show: false // don't show login on initialization
		});
	// Track whether loginBox is visible to prevent .show() creating duplicates
    loginBox.visible = false;
	// Functions to display/hide the login form
	$rootScope.showLogin = function() {
		if (loginBox.visible) return;
		loginBox.$promise.then(loginBox.show);
        loginBox.visible = true;
	};
	$rootScope.hideLogin = function() {
        if (loginBox.visible) {
            loginBox.hide();
            loginBox.visible = false;
        }
	};
	// Show the login form when we have a login required event
	$rootScope.$on(AuthenticationService.LOGIN_REQUIRED_EVENT, $rootScope.showLogin);
	// Hide the login form on login
	$rootScope.$on(AuthenticationService.LOGIN_EVENT, $rootScope.hideLogin);

	// Requires the user to be logged in for every single route
//	$rootScope.$on('$locationChangeStart', function(event, next) {
//		if (!AuthenticationService.isAuthenticated())
//		{
//			event.preventDefault();
//			// user needs to be logged in
//			$rootScope.$broadcast(AuthenticationService.LOGIN_REQUIRED_EVENT);
//			// wipe out current data displayed on screen
//			$route.reload();
//		}
//	});
});


/***** Controllers *****/
module.controller(
	"LoginController",
	function LoginController($rootScope, $scope, $location, $log, $route,
							 LoginResource,
							 UserResource,
							 AuthenticationService)
	{
		$scope.submitted = false;

		$scope.submit = function() {
			$scope.submitted = true;
			var params = {"username": $scope.username,
							"password": $scope.password};
			LoginResource.login(params).$promise.then(
				function(ret) {
					// login successful
					$log.debug("Login authentication successful!");
					userid = ret.userid
					$log.debug("Login User ID: " + userid);
					// retrieve logged in user's information
                    AuthenticationService.login().then(function() {
                        $scope.login_err = "";
                        $scope.submitted = false;
                        $route.reload();
                    }, function() {
                        $log.error(
                                "Failed to retrieve logged in user's data: " +
                                JSON.stringify(ret));
                        $scope.login_err = "Unable to retrieve user information, server problem?";
                        $scope.submitted = false;
                    });
				},
				function(ret) {
					// login failed
					$log.debug("Login authentication failed.");
					if (ret.data.error)
					{
						$scope.login_err = ret.data.error;
					}
					else
					{
						$scope.login_err = "Server error during authentication.";
					}
					$scope.submitted = false;
				}
			);

		};
	}
);

module.controller(
	"LogoutController",
	function LogoutController($scope, $location, $log, $route, LoginResource, AuthenticationService) {
		$scope.logout = function() {
			LoginResource.logout().$promise.then(
				function() {
					$log.debug("Logging out user successful.");
					AuthenticationService.logout();
					$location.path("/"); //redirect user to home screen
					$route.reload();
				}
				// TODO do we care about logout failure? if so, handle it here
			);
		};
	}
);
// End anonymous function
})();
