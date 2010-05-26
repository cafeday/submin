from submin import models
from submin.hooks.common import trigger_hook
from submin.models import options
import validators
storage = models.storage.get("user")

from submin.models.exceptions import UnknownUserError, UserPermissionError

class FakeAdminUser(object):
	"""Sometimes you have no session_user but you want to make a change to
	a user where admin rights are needed. You can pass an instance of this
	object as 'session_user' to get admin rights."""
	def __init__(self):
		self.is_admin = True

def list(session_user):
	"""Returns a (sorted) list of usernames

	list expects a session_user argument: this is the user requesting the
	user list. If the user is not an admin, it will only get to see
	herself.
	"""
	if not session_user.is_admin: # only admins get to see the entire list
		return [session_user.name]     # users only see themselves

	return [user['name'] for user in storage.list()]

def add(username, password=None):
	"""Adds a new user with a no password.

	To generate a password, call generate_password()
	Raises UserExistsError if a user with this username already exists.
	"""

	if not validators.validate_username(username):
		raise validators.InvalidUsername(username)

	storage.add(username, password)
	trigger_hook('user-create', username=username, user_passwd=password)
	return User(username)

class User(object):
	def __init__(self, username=None, raw_data=None):
		"""Constructor, either takes a username or raw data

		If username is provided, the storage plugin is used to get the
		required data. If raw_data is provided, the storage plugin is not used.
		"""
		db_user = raw_data

		if not raw_data:
			db_user = storage.user_data(username)
			if not db_user:
				raise UnknownUserError(username)

		self._type     = 'user' # needed for Manager
		self._id       = db_user['id']
		self._name     = db_user['name']
		self._email    = db_user['email']
		self._fullname = db_user['fullname']
		self._is_admin = db_user['is_admin']

		self.is_authenticated = False # used by session, listed here to provide
		                              # default value

	def __str__(self):
		return self._name

	def check_password(self, password):
		"""Return True if password is correct, can raise NoMD5PasswordError"""
		return storage.check_password(self._id, password)

	def set_password(self, password, send_email=False):
		storage.set_password(self._id, password)
		trigger_hook('user-update', username=self._name, user_passwd=password)
		if send_email:
			self.email_user(password=password)

	def set_md5_password(self, password):
		storage.set_md5_password(self._id, password)

	def generate_random_string(self, length=50):
		"""generate and return a random string"""
		from string import ascii_letters, digits
		import random
		string_chars = ascii_letters + digits
		string = ''.join([random.choice(string_chars) \
				for x in range(0, length)])

		return string

	def prepare_password_reset(self):
		key = self.generate_random_string()
		storage.set_password_reset_key(self._id, key)
		self.email_user(key=key)

	def valid_password_reset_key(self, key):
		"""Validate password request for this user."""
		return storage.valid_password_reset_key(self._id, key)

	def clear_password_reset_key(self):
		storage.clear_password_reset_key(self._id)

	def email_user(self, key=None, password=None):
		"""Email the user a key (to reset her password) OR a password (if the
		user followed a link with the key in it). Do not call this function
		with both key set and password set, as the user will get one email
		with both messages in it."""
		import smtplib
		from submin.template.shortcuts import evaluate

		templatevars = {
			'from': 'submin@supermind.nl',
			'to': self.email,
			'username': self.name,
			'key': key,
			'password': password,
			'base_url': options.url_path("base_url_submin"),
		}
		server = options.value("smtp_hostname", "localhost")
		port = options.value("smtp_port", 25)
		username = options.value("smtp_username", "")
		password = options.value("smtp_password", "")

		message = evaluate('email/reset_password.txt', templatevars)
		server = smtplib.SMTP(server, int(port))
		if username != "" and password != "":
			server.login(username, password)

		server.sendmail(templatevars['from'], [templatevars['to']], message)
		server.quit()

	def remove(self):
		storage.remove_from_groups(self._id)
		storage.remove_permissions_repository(self._id)
		storage.remove_permissions_submin(self._id)
		storage.remove_notifications(self._id)
		storage.remove_all_ssh_keys(self._id)
		storage.remove(self._id)
		trigger_hook('user-delete', username=self._name)

	def member_of(self):
		return storage.member_of(self._id)

	def nonmember_of(self):
		return storage.nonmember_of(self._id)

	def set_notification(self, repository, allowed, enabled, session_user):
		if not session_user.is_admin:
			permissions = storage.notification(self._id, repository)
			if not permissions or not permissions['allowed']:
				raise UserPermissionError

		# automatically allow if enabled
		if enabled:
			allowed = True

		storage.set_notification(self._id, repository, allowed, enabled)

	def notifications(self):
		"""Returns a dict of dicts, in the following layout:
		{
			'reposname1': {'allowed': True, 'enabled': False},
			'repos2': {'allowed': False, 'enabled': False}
		}
		"""
		from repository import Repository
		notifications = {}
		for repository in Repository.list_all():
			notification = storage.notification(self._id, repository['name'])
			if notification == None:
				notification = {'allowed': False, 'enabled': False}
			notifications[repository['name']] = notification

		return notifications

	def ssh_keys(self):
		"""Returns a list of tuples, containing the title and public key of
		each stored SSH key"""
		return storage.ssh_keys(self._id)

	def add_ssh_key(self, ssh_key, title=None):
		if title is None:
			title = ssh_key.strip().split()[-1]
		# XXX validator for ssh_key on front-end side, disallowing anything
		# coming before the key type (ssh-XXX)

		if not validators.validate_ssh_key(ssh_key):
			raise validators.InvalidSSHKey(ssh_key)
		storage.add_ssh_key(self._id, ssh_key, title)

	def remove_ssh_key(self, ssh_key_id):
		storage.remove_ssh_key(ssh_key_id)

	# Properties
	def _getId(self):
		return self._id

	def _getName(self):
		return self._name

	def _setName(self, name):
		if not validators.validate_username(name):
			raise validators.InvalidUsername(name)
		oldname = self._name
		self._name = name
		storage.set_name(self._id, name)
		trigger_hook('user-update', username=self._name, user_oldname=oldname)

	def _getEmail(self):
		return self._email

	def _setEmail(self, email):
		self._email = email
		if not validators.validate_email(email):
			raise validators.InvalidEmail(email)
		storage.set_email(self._id, email)

	def _getFullname(self):
		return self._fullname

	def _setFullname(self, fullname):
		self._fullname = fullname
		if not validators.validate_fullname(fullname):
			raise validators.InvalidFullname(fullname)
		storage.set_fullname(self._id, fullname)

	def _getIsAdmin(self):
		return self._is_admin

	def _setIsAdmin(self, is_admin):
		self._is_admin = is_admin
		storage.set_is_admin(self._id, is_admin)

	id       = property(_getId)   # id is read-only
	name     = property(_getName,     _setName)
	email    = property(_getEmail,    _setEmail)
	fullname = property(_getFullname, _setFullname)
	is_admin = property(_getIsAdmin,  _setIsAdmin)

__doc__ = """
Storage contract
================

* list()
	Returns a sorted list of users, sorted by username

* add(username, password)
	Adds a new user, raises `UserExistsError` if there already is a user with
	this username

* user_data(username)
	Returns a dictionary with all required user data.
	Returns `None` if no user with this username exists.
	Fields which need to be implemented (with properties?): name, email,
	fullname, is_admin

* check_password(id, password)
	Checks whether the supplied password is valid for a user with userid *id*

* set_password(id, password)
	Sets the password for a user with userid *id* to *password*, in storage's
	native format.
	
* set_md5_password(id, password)
	Sets the md5 password for a user with userid *id* to *password*. If this is
	not supported by the module, it raises an MD5NotSupported error. This
	method is mainly used to convert htpasswd files to storage plugins that
	also use md5 to encrypt passwords.

* valid_password_reset_key(userid)
	Check if the key is valid and not expired for this user.

* set_password_reset_key(userid, key)
	Prepare the password reset, returns a special key that the user must
	present to reset the password. This key can be mailed to the user, for
	example. This overwrites any previous keys _for that user_.

* clear_password_reset_key(userid)
	Clear password reset key, for example when a user has reset her password.

* remove(userid)
	Removes user with id *userid*. Before a user can be removed, all
	remove_-functions below must have been called. This happens in the model,
	so storage plugin designers need not worry about this restriction.

* remove_from_groups(userid)
	Removes user with id *userid* from groups

* remove_permissions_repository(userid)
	Removes a user's repository permissions

* remove_permissions_submin(userid)
	Removes a user's submin permissions

* remove_notifications(userid)
	Removes a user's notifications

* remove_all_ssh_keys(userid)
	Removes a user's ssh_keys (all of them)

* member_of(userid)
	Returns sorted list of groups a user is member of.

* nonmember_of(userid)
	Returns sorted list of groups a user is not a member of.

* notification(userid, repository)
	Returns a dict of the notification, or None if it doesn't exist. The dict
	looks like: {'allowed': True, 'enabled': False}

* set_notification(userid, repository, allowed, enabled)
	Set notification to *allowed*, *enabled* (both booleans) for user *userid*
	on repository *repository*.

* ssh_keys(userid)
	Returns a list of ssh_keys (dicts like
	{'id': id, 'title': title, 'key': key})

* add_ssh_key(userid, ssh_key, title)
	Adds an ssh key for user with id *userid*.

* remove_ssh_key(ssh_key_id)
	Removes a single ssh_key with id *ssh_key_id*.

* set_email(id, email)
	Sets the email for user with id *id*

* set_fullname(id, fullname)
	Sets the fullname for user with id *id*

* set_is_admin(id, is_admin)
	Sets whether user with id *id* is an admin
"""