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

RATE_LOVE = 'love'
RATE_HATE = 'hate'


class Syncer(object):

    def __call__(self, args=None):
        if args is None:
            args = sys.argv[1:]

        self.parse_arguments(args)

        if self.options.sync_movies:
            self.sync_movies()

        if self.options.sync_shows:
            self.sync_shows()

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
            '--no-movies', dest='sync_movies', action='store_false',
            default=True,
            help='Do not sync watched movies.')

        parser.add_option(
            '--no-shows', dest='sync_shows', action='store_false',
            default=True,
            help='Do not sync watched shows.')

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

        parser.add_option(
            '-v', '--verbose', dest='verbose', action='store_true',
            help='Print more verbose debugging informations.')

        self.options, self.arguments = parser.parse_args(args)

        if self.options.verbose:
            LOG.setLevel(logging.DEBUG)

        # validate options
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

    def sync_movies(self):
        movie_nodes = tuple(self.plex_get_watched_movies())

        if movie_nodes:
            self.trakt_report_movies(movie_nodes)
            if self.options.rate:
                self.trakt_rate_movies(movie_nodes)

        else:
            LOG.warning('No watched movies could be found in your '
                        'plex server.')

    def sync_shows(self):
        episode_data = self.plex_get_watched_episodes()

        if episode_data:
            self.trakt_report_episodes(episode_data)

        else:
            LOG.warning('No watched show episodes could be found on your '
                        'plex server.')

    def plex_get_watched_movies(self):
        for node in self._plex_request('/library/sections/1/all'):
            if node.getAttribute('viewCount'):
                yield node

    def plex_get_shows(self):
        return self._plex_request('/library/sections/2/all',
                                  nodename='Directory')

    def plex_get_seasons(self):
        for show in self.plex_get_shows():
            seasons = []
            show_key = show.getAttribute('key')

            for season in self._plex_request(show_key, nodename='Directory'):
                seasons.append(season)

            yield show, seasons

    def plex_get_watched_episodes(self):
        shows = []

        for show, seasons in self.plex_get_seasons():
            episodes = []

            for season in seasons:
                season_key = season.getAttribute('key')

                for episode in self._plex_request(season_key):
                    if episode.getAttribute('viewCount'):
                       episodes.append((season, episode))

            if len(episodes) > 0:
                shows.append((show, episodes))

        return shows

    def get_movie_data(self, node):
        """Returns movie data from a XML node, prepared to post to trakt.
        """
        return {'title': node.getAttribute('title'),
                'year': node.getAttribute('year'),
                'plays': node.getAttribute('viewCount'),
                'last_played': node.getAttribute('updatedAt')}

    def get_show_data(self, show):
        return {'title': show.getAttribute('title'),
                'year': show.getAttribute('year')}

    def get_movie_rating(self, node):
        rating = node.getAttribute('userRating')
        if not rating:
            return None

        rating = int(rating)
        if rating >= self.options.min_love:
            return RATE_LOVE

        elif rating <= self.options.max_hate:
            return RATE_HATE

        return None

    def trakt_report_movies(self, nodes):
        movies = []

        for node in nodes:
            movie = self.get_movie_data(node)
            LOG.debug('Mark "%s (%s)" as seen' % (
                    movie['title'], movie['year']))
            movies.append(movie)

        LOG.info('Mark %s movies as seen in trakt.tv' % len(movies))
        self._trakt_post('movie/seen', {'movies': movies})

    def trakt_report_episodes(self, episode_data):
        for show, episodes in episode_data:
            show_data = self.get_show_data(show)
            data = show_data.copy()
            data['episodes'] = []

            for season, episode in episodes:
                data['episodes'].append({
                        'season': season.getAttribute('index'),
                        'episode': episode.getAttribute('index')})
                LOG.debug(('Mark episode "%s", season %s, episode'
                           ' %s (%s) as seen') % (
                        data['title'],
                        season.getAttribute('index'),
                        episode.getAttribute('index'),
                        episode.getAttribute('title')))

                if self.options.rate:
                    rating = self.get_movie_rating(episode)
                    if rating:
                        episode_data = show_data.copy()
                        episode_data.update({
                                'season': season.getAttribute('index'),
                                'episode': episode.getAttribute('index'),
                                'rating': rating})

                        LOG.info(('Rate episode "%s", season %s, episode'
                                   ' %s (%s) with "%s"') % (
                                data['title'],
                                season.getAttribute('index'),
                                episode.getAttribute('index'),
                                episode.getAttribute('title'),
                                rating))
                        self._trakt_post('rate/episode', episode_data)

            LOG.info(('Mark "%s" episodes of the show %s as '
                      'seen in trakt.tv') % (
                    len(data['episodes']), data['title']))
            self._trakt_post('show/episode/seen', data)

    def trakt_rate_movies(self, nodes):
        rated = 0
        total = 0

        for node in nodes:
            total += 1

            movie = self.get_movie_data(node)
            rating = self.get_movie_rating(node)
            if not rating:
                continue

            movie.update({'rating': rating})
            LOG.info('Rate "%s (%s)" with "%s"' % (
                    movie['title'], movie['year'], rating))
            self._trakt_post('rate/movie', movie)

            rated += 1

        LOG.info('Rated %s of %s movies in trakt.tv' % (
                rated, total))

    def _plex_request(self, path, nodename='Video'):
        """Makes a request to plex and parses the XML with minidom.
        """
        url = 'http://%s:%s%s' % (
            self.options.plex_host,
            self.options.plex_port,
            path)

        LOG.info('Plex request to %s' % url)

        response = urllib.urlopen(url)
        data = response.read()
        doc = parseString(data)

        LOG.info('Plex request success')

        return doc.getElementsByTagName(nodename)

    def _trakt_post(self, path, data):
        """Posts informations to trakt. Data should be a dict which will
        be updated with user credentials.
        """
        url = 'http://api.trakt.tv/%s/%s' % (path, self.options.trakt_key)
        passwd = hashlib.sha1(self.options.trakt_password).hexdigest()

        postdata = {'username': self.options.trakt_username,
                    'password': passwd}
        postdata.update(data)

        LOG.debug('POST to %s ...' % url)
        LOG.debug(pformat(data))
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
                LOG.debug('Trakt request success: %s' % pformat(resp_json))

            else:
                filtered_data = dict([(key, value) for (key, value) in resp_json.items()
                                      if not key.endswith('_movies')])
                LOG.info('Trakt request success: %s' % pformat(filtered_data))

            return True

        else:
            self.quit_with_error('Trakt request failed with %s' % resp_data)


if __name__ == '__main__':
    try:
        Syncer()()
    except Exception, e:
        LOG.error(str(e))
        raise
