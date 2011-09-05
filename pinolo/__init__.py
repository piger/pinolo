VERSION = (0, 9, 1)
STR_VERSION = '.'.join([str(x) for x in VERSION])
FULL_VERSION = "Pinolo-" + STR_VERSION
SOURCE_URL = "http://code.dyne.org/?r=pinolo"
USER_AGENT = "Pinolo/%s +%s" % (STR_VERSION, SOURCE_URL)

DEFAULT_DATABASE_FILENAME = 'db.sqlite'

# in seconds
EOF_RECONNECT_TIME = 60
FAILED_CONNECTION_RECONNECT_TIME = 120
CONNECTION_TIMEOUT = 60 * 5
PING_DELAY = float(60 * 4)
