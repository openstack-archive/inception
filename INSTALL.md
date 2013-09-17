Installation
============

API Server
----------

SECURITY NOTE: Not for production use!  This server does not provide sufficient
security to operate in a production environment.

1. Ensure the server's dependencies are installed:

    + anyjson
    + inception itself (oslo.config, ipython)
    + pastescript
    + routes
    + sqlalchemy

2. Create the database

        $ python inception/api/server.py # needed first time only

3. Run server

        $ paster serve ./etc/inception/paste-config.ini

