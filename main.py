import os
import sys
import tempfile
import subprocess
from dropbox import client, rest, session
from gistapi import Gist, Gists

APP_KEY = '5ci5qiywhs060nt'
APP_SECRET = 'hxcpv5p7ptgmqcj'
ACCESS_TYPE = 'dropbox'

sess = session.DropboxSession(APP_KEY, APP_SECRET, ACCESS_TYPE)

# Check for presence of request token
try:
	with open("/tmp/dropbox_token.pkl", "r") as f:
		token_key, token_secret = f.read().split('|')
		sess.set_token(token_key, token_secret)
except (IOError, IndexError):
	request_token = sess.obtain_request_token()
	print request_token
	print str(request_token)

	url = sess.build_authorize_url(request_token)
	print "url:", url
	print "Please authorize in the browser. After you're done, press Enter."
	raw_input()

	access_token = sess.obtain_access_token(request_token)
	try:
		with open("/tmp/dropbox_token.pkl", "w") as f:
			f.write("%s|%s" % (access_token.key, access_token.secret))
	except IOError:
		pass
	except AttributeError as e:
		print "Internal Error: " % e

client = client.DropboxClient(sess)

m = client.metadata("/")
if m['is_dir']:
	files = m['contents']
else:
	files = [m]
for (i,f) in enumerate(files):
	print i, f['path']

print "Which file?"
ixFile = int(raw_input())
selectedFile = files[ixFile]
if selectedFile['is_dir']:
	print "Sorry, but only files have revisions."
	sys.exit(2)
print "Getting revisions of %s" % selectedFile['path']
revs = client.revisions(selectedFile['path'])
print "There are %d revisions of %s." % (len(revs), selectedFile['path'])
if len(revs) < 2:
	response = raw_input("There's only one revision of this file. Are you sure you want to export it? [Y/n] ")
	if not response or response.lower()[0] == 'y':
		pass
	else:
		print "Aborting."
		sys.exit(0)

basename = selectedFile['path'].split('/')[-1]
print "basename: %s" % str(basename)

scratchDir = tempfile.mkdtemp()
os.chdir(scratchDir)
f = open(os.path.join(scratchDir, basename), "w")

try:
	subprocess.Popen(['git', 'init', '.'],
		stdout=sys.stdout,
		stderr=sys.stderr).wait()
except OSError as e:
	print "Is git installed?"
	sys.exit(1)
for r in sorted(revs, key=lambda r: r['revision']):
	f.seek(0)
	response = client.get_file(r['path'], rev=r['revision'])
	f.write(response.read())
	response.close()
	f.flush()
	
	p = subprocess.Popen(['git', 'add', basename],
		stdout=sys.stdout,
		stderr=sys.stderr)
	exitCode = p.wait()
	if exitCode != 0:
		print "git add returned <> 0"
	
	# And now the fun begins
	p = subprocess.Popen(['git', 'commit', '-am', 'Revision %d from Dropbox2Git' % r['revision']],
		stdout=sys.stdout,
		stderr=sys.stderr)
	exitCode = p.wait()
	if exitCode != 0:
		print "Something bad might have happened; git returned status code of %d" % exitCode
	print "Completed revision %d" % r['revision']
print "Git repository complete at %s" % scratchDir
