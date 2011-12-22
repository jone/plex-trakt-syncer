#!/usr/bin/env python

from optparse import OptionParser
from pprint import pformat
from xml.dom.minidom import parseString
import hashlib
import json
import logging
import os
import sys
import urllib
import urllib2


VERSION = '1.0'

DESCRIPTION = '''This script connects to a Plex media center server and
reports the watched movies to a trakt.tv user profile. Optionally it also
flags the movies at the trakt profile with "love" or "hate" according to
ratings in Plex.'''

EPILOG = '''
** Rating **           The plex rating allows to give up to 5 stars for
a movie, but you can also give half stars, so there are 10 steps for the
rating. The configurable --min-hate and --max-love options take a value
between 1 and 10. Movies which are not yet rated in plex are not flagged
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
LOG.setLevel(logging.INFO)


class Syncer(object):

    def __call__(self, args=None):
        if args is None:
            args = sys.argv[1:]

        self.parse_arguments(args)

        movies = []
        for node in tuple(self.plex_get_watched_movies())[:40]:
            movie = self.get_movie_data(node)
            LOG.info('mark "%s (%s)" as seen' % (
                    movie['title'], movie['year']))
            movies.append(movie)

        print self.trakt_report_movies(movies)

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
            '-P', '--port', dest='plex_port', default=32400,
            metavar='PORT',
            help='Port of the plex server (default: 32400)')

        parser.add_option(
            '-u', '--username', dest='trakt_username',
            metavar='USERNAME',
            help='trakt.tv username')

        parser.add_option(
            '-p', '--password', dest='trakt_password',
            metavar='PASSWORD',
            help='trakt.tv password')

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

        if not self.options.trakt_key:
            self.quit_with_error('Please define a trakt API key (-k).')

        if not self.options.trakt_password:
            self.quit_with_error('Please define a trakt password (-p).')

        if self.options.max_hate > 10 or self.options.max_hate < 0:
            self.quit_with_error('--max-hate should be between 1 and 10')

        if self.options.min_love > 10 or self.options.min_love < 0:
            self.quit_with_error('--min-love should be between 1 and 10')

    def plex_get_watched_movies(self):
        for node in self._plex_request('library/sections/1/all'):
            if node.getAttribute('viewCount'):
                yield node

    def get_movie_data(self, node):
        """Returns movie data from a XML node, prepared to post to trakt.
        """
        return {'title': node.getAttribute('title'),
                'year': node.getAttribute('year'),
                'plays': node.getAttribute('viewCount'),
                'last_played': node.getAttribute('updatedAt')}

    def trakt_report_movies(self, movies):
        print self._trakt_post('movie/seen', {'movies': movies})

    def _plex_request(self, path):
        """Makes a request to plex and parses the XML with minidom.
        """
        url = 'http://%s:%i/%s' % (
            self.options.plex_host,
            self.options.plex_port,
            path)

        response = urllib.urlopen(url)
        data = response.read()
        doc = parseString(data)

        return doc.getElementsByTagName('Video')

    def _trakt_post(self, path, data):
        """Posts informations to trakt. Data should be a dict which will
        be updated with user credentials.
        """
        url = 'http://api.trakt.tv/%s/%s' % (path, self.options.trakt_key)
        passwd = hashlib.sha1(self.options.trakt_password).hexdigest()

        postdata = {'username': self.options.trakt_username,
                    'password': passwd}
        postdata.update(data)

        LOG.info('trakt POST to %s' % path)
        try:
            # data = urllib.urlencode(postdata)
            request = urllib2.Request(url, json.dumps(postdata))
            response = urllib2.urlopen(request)

        except urllib2.URLError, e:
            LOG.error(e)
            raise

        resp_data = response.read()
        resp_json = json.loads(resp_data)
        if resp_json.get('status') == 'success':

            if LOG.isEnabledFor(logging.DEBUG):
                LOG.debug('detailed trakt response: %s' % pformat(resp_json))

            else:
                filtered_data = dict([(key, value) for (key, value) in resp_json.items()
                                  if not key.endswith('_movies')])
                LOG.info('trakt response (filtered): %s' % pformat(filtered_data))

            return True

        else:
            self.quit_with_error('trakt request failed with %s' % resp_data)


if __name__ == '__main__':
    try:
        Syncer()()
    except Exception, e:
        LOG.error(str(e))
        raise
