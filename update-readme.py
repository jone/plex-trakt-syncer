#!/usr/bin/env python

import os
import subprocess
import re


directory = os.path.abspath(os.path.dirname(__file__))
readme_path = os.path.join(directory, 'README.rst')

# read current readme
readme = open(readme_path, 'r').read()

# run the help command to get the usage
cmd = [os.path.join(directory, 'plex-trakt-sync.py'), '--help']
proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
usage = proc.communicate()[0].strip()

# make usage a rest block
prefix = ' ' * 4
usage = prefix + ('\n%s' % prefix).join(usage.split('\n'))
usage = '\n::\n\n' + usage + '\n'

# replace the usage section in the current readme with the new usage
xpr = re.compile('(%usage-start%\s).*(\s\.\. %usage-end%)',
                 flags=re.DOTALL)
readme = xpr.sub('\g<1>%s\g<2>' % usage, readme)

# write update readme
file_ = open(readme_path, 'w')
file_.write(readme)
file_.close()

print usage
print 'DONE'
