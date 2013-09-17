Installation
============

API Server
----------
1. Ensure the server's dependencies are installed:

    + pastescript
    + oslo.config
    + routes
    + sqlalchemy

2. Ensure package is installed/set PYTHONPATH to include top-level dir of package

    >Note: Until the issue describe in <https://bugs.launchpad.net/inception/+bug/1226153>
is resolved, the server should be run from the top-level directory of the 
source distribution for Inception Cloud.

        $ cd <top-level-dir>
        $ export PYTHONPATH=$(pwd)

3. Create the database

        $ python inception/api/server.py # needed first time only

4. Run server

        $ paster serve ./etc/inception/paste-config.ini 

More information about Inception Cloud at <https://wiki.openstack.org/wiki/Inception>

Join us

<https://launchpad.net/inception>
