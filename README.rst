===================
 Plex Trakt syncer
===================

A simple console script for updating your Trakt_ profile with the infos from your Plex_ media center.

Features
========

- Marks movies watched in Plex_ when watched in your Trakt_ profile.
- Optionally flages the movies in Trakt_ with "love" or "hate" according to the rating in Plex_.

Install
=======

Either download the script from https://github.com/jone/plone-trakt-syncer/downloads or
clone the repository with git:

::

    $ git clone https://github.com/jone/plone-trakt-syncer.git
    $ cd plex-trakt-syncer
    $ plex-trakt-sync.py --help

You may also want to set up a cronjob for starting the script.


Usage
=====

.. %usage-start%

::

    Usage: plex-trakt-sync.py [options]
    
    This script connects to a Plex media center server and reports the watched
    movies to a trakt.tv user profile. Optionally it also flags the movies at the
    trakt profile with "love" or "hate" according to ratings in Plex.
    
    Options:
      --version             show program's version number and exit
      -h, --help            show this help message and exit
      -H HOST, --host=HOST  Hostname or IP of plex server (default: localhost)
      -P PORT, --port=PORT  Port of the plex server (default: 32400)
      -u USERNAME, --username=USERNAME
                            trakt.tv username
      -p PASSWORD, --password=PASSWORD
                            trakt.tv password
      -k API-KEY, --key=API-KEY
                            trakt.tv API key
      -r, --rate            Submit plex movie ratings to trakt.
      --max-hate=1-10       Maxmimum plex rating for flagging a movie with "hate"
                            (In combination with -r option, defaults to 3).
      --min-love=1-10       Minimum plex rating for flagging a movie with "love"
                            (In combination with -r option, defaults to 8).
      -v, --verbose         Print more verbose debugging informations.
    
     ** Rating **           The plex rating allows to give up to 5 stars for a
    movie, but you can also give half stars, so there are 10 steps for the rating.
    The configurable --min-hate and --max-love options take a value between 1 and
    10. Movies which are not yet rated in plex are not flagged at all.

.. %usage-end%

License
=======

"THE BEER-WARE LICENSE" (Revision 42):

jone_ wrote this script. As long as you retain this notice you
can do whatever you want with this stuff. If we meet some day, and you think
this stuff is worth it, you can buy me a beer in return.

Source
======

The source is located at https://github.com/jone/plone-trakt-syncer


.. _Trakt: http://trakt.tv/
.. _Plex: http://www.plexapp.com/
.. _jone: http://github.com/jone
