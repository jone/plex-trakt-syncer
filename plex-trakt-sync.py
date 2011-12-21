#!/usr/bin/env python

import logging
from optparse import OptionParser
import os
import sys


VERSION = '1.0'

DESCRIPTION = '''This script connects to a Plex media center server and
reports the watched movies to a trakt.tv user profile. Optionally it also
flags the movies at the trakt profile with "love" or "hate" according to
ratings in Plex.'''

EPILOG = '''
** Rating **           The plex rating allows to give up to 5 stars for
a movie, but you can also give half stars, so there are 10 steps for the
rating. The configurable --min-hate and --max-love options take a value
between 0 and 10. Movies which are not yet rated in plex are not flagged
at all.
'''

LOG_FILE = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                        'syncer.log')

logging.basicConfig(
    filename=LOG_FILE,
    datefmt='%Y-%m-%dT%H:%M:%S',
    format='%(asctime)s %(levelname)s [%(name)s] %(message)s')


LOG = logging.getLogger('plex-trakt-syncer')
LOG.addHandler(logging.StreamHandler())


class Syncer(object):

    def __call__(self, args=None):
        if args is None:
            args = sys.argv[1:]

        self.parse_arguments(args)

    def quit_with_error(self, message):
        LOG.error(message)
        sys.exit(1)

    def parse_arguments(self, args):
        """Parses the passed arguments.
        """

        parser = OptionParser(version=VERSION, description=DESCRIPTION,
                              epilog=EPILOG)

        parser.add_option(
            '-H', '--host', dest='plex_host', default='localhost',
            metavar='HOST',
            help='Hostname or IP of plex server (default: localhost)')

        parser.add_option(
            '-u', '--username', dest='trakt_username',
            metavar='USERNAME',
            help='trakt.tv username')

        parser.add_option(
            '-k', '--key', dest='trakt_key',
            metavar='API-KEY',
            help='trakt.tv API key')

        parser.add_option(
            '-r', '--rate', dest='rate', action='store_true',
            help='Submit plex movie ratings to trakt.')

        parser.add_option(
            '--max-hate', dest='max_hate', type='int', metavar='1-10',
            default=3,
            help='Maxmimum plex rating for flagging a movie with "hate" '
            '(In combination with -r option, defaults to 3).')

        parser.add_option(
            '--min-love', dest='min_love', type='int', metavar='1-10',
            default=8,
            help='Minimum plex rating for flagging a movie with "love" '
            '(In combination with -r option, defaults to 8).')

        # validate options
        self.options, self.arguments = parser.parse_args(args)

        if not self.options.trakt_username:
            self.quit_with_error('Please define a trakt username (-u).')

        print self.options, self.arguments


if __name__ == '__main__':
    Syncer()()
