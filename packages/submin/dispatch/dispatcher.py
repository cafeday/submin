from submin.dispatch.response import Response, HTTP404, XMLStatusResponse

from submin.views.error import ErrorResponse
from submin.views.test import Test
from submin.views.users import Users
from submin.views.groups import Groups
from submin.views.authviews import Login, Logout, Password
from submin.views.repositories import Repositories
from submin.views.intro import Intro
from submin.views.ajax import Ajax
from submin.views.upgrade import Upgrade
from submin.models import options
from submin.models.exceptions import UnknownKeyError
from submin.dispatch.session import Session


classes = {
	'test': Test,
	'users': Users,
	'groups': Groups,
	'login': Login,
	'logout': Logout,
	'x': Ajax,
	'repositories': Repositories,
	'upgrade': Upgrade,
	'password': Password,
	'': Intro,
}

def init_tests():
	"""Initialize url-coupling to test-views
	Only loaded if config-options in section "tests" are present
	"""
	try:
		options.value("tests_scenarios_file")
	except UnknownKeyError:
		return

	from submin.views.uiscenarios import UIScenarios
	classes["uiscenarios"] = UIScenarios

init_tests()

def dispatcher(request):
	# Add session information to request
	request.session = Session(request)

	path = request.path_info.strip('/').split('/')

	handlerName = 'handler'
	if path[0].lower() in classes:
		cls = classes[path[0].lower()](request)
		if not hasattr(cls, handlerName):
			raise Exception, "No handler %r found for view %r" % (handlerName, path[0].lower())

		del path[0]
		handler = getattr(cls, handlerName)
		try:
			response = handler(request, path)

			if not issubclass(response.__class__, Response):
				raise Exception, "Handler %r should return a Response instance" % handler
		except UnknownKeyError, e:
			env = options.env_path() # this should never trigger another UnknownKeyError
			summary = "It seems your installation is missing a configuration option (%s)" % str(e)
			details = """
You can add the missing config option by executing the following commandline:

submin-admin %s config set %s &lt;value&gt;

Unfortunately, this error handling does not know the value you should set, but
the name of the missing option should give you a hint to its value :)""" % \
	(env, str(e))

			if not request.is_ajax():
				details = '<pre>' + details + '</pre>'
				response = ErrorResponse(summary, request=request, details=details)
			else:
				details = summary + '\n\n' + details
				response = XMLStatusResponse('', False, details)
		except Exception, e:
			import traceback
			details = traceback.format_exc()

			if not request.is_ajax():
				details = '<pre>' + details + '</pre>'
				response = ErrorResponse(str(e), request=request, details=details)
			else:
				details = 'Whoops, an internal error occured:\n\n' + str(e) + '\n\n' + details
				response = XMLStatusResponse('', False, details)

	else:
		response = HTTP404('/'.join(path))

	response.setCookieHeaders(request.cookieHeaders())

	return response

