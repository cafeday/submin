import random
from cStringIO import StringIO
from lib.utils import mimport
Buffer = mimport('lib.utils').Buffer
iif = mimport('lib.utils').iif

class Html:
	def __init__(self, input):
		self.input = input

	def header(self, title = None, scripts = [], css = []):
		buf = Buffer()
		buf.write('''<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
		"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" lang="en" xml:lang="en">
	<head>
		<title>Submin%s</title>
		<base href="%s" />
		<link rel="stylesheet" type="text/css" href="css/submin.css" 
			media="screen" />\n'''% \
					(iif(title, ' - %s' % title, ' '), self.input.base))

		for sheet in css:
			buf.write('''\t\t<link rel="stylesheet" type="text/css" href="css/%s.css" media="screen" />\n''' % \
					sheet)

		buf.write('''\t\t<script src="js/prototype-1.4.0.js" type="text/javascript"></script>\n''')
		buf.write('''\t\t<script src="js/effects.js" type="text/javascript"></script>\n''')
		buf.write('''\t\t<script src="js/dragdrop.js" type="text/javascript"></script>\n''')

		for script in scripts:
			buf.write('''\t\t<script src="js/%s.js" type="text/javascript"></script>\n''' % \
					(script,))

		buf.write('''
	</head>
	<body>
		<div id="header">
			<h1><a href="%s">Submin</a></h1>
		</div>
		<div id="nav"><ul>''' % self.input.base)

		if self.input.isLoggedIn():
			buf.write(
				'<span class="logged">logged in as: &quot;%s&quot;</span>' % 
					self.input.user)

		if self.input.isAdmin():
			# the LI elements can't be seperated by spaces!
			links = [('users', 'users'), ('groups', 'group'), 
				('permissions', 'authz'), ('repositories', 'repository')]

			for name, link in links:
				if link == self.input.pathInfo[0]:
					active = ' class="adminactive"'
				else:
					active = ' class="admin"'

				buf.write('<li%s><a href="%s">%s</a></li>' % 
						(active, link, name))

		if self.input.isLoggedIn():
			links = { 'profile':'profile', 'logout':'logout' }

			for name, link in links.iteritems():
				if link == self.input.pathInfo[0]:
					active = ' class="active"'
				else:
					active = ''

				buf.write('<li%s><a href="%s">%s</a></li>' % 
						(active, link, name))
		else:
			if self.input.pathInfo[0] == 'login':
				active = ' class="active"'
			else:
				active = ''
			buf.write('<li%s><a href="login">login</a></li>' % active)

		return str(buf)

	def footer(self):
		buf = Buffer()
		buf.write('''
			</div>
		</div>
	</body>
</html>''')

		return str(buf)