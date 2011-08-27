VERSION = (0, 9, 1)
STR_VERSION = '.'.join([str(x) for x in VERSION])
FULL_VERSION = "Pinolo-" + STR_VERSION

DEFAULT_DATABASE_FILENAME = 'db.sqlite'

# in seconds
EOF_RECONNECT_TIME = 60
FAILED_CONNECTION_RECONNECT_TIME = 120
