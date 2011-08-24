# pinolo: The naughty IRC bot

pinolo is an IRC bot written for fun.

## Requirements

- python >= 2.5
- SQLAlchemy
- Xapian
- gevent


## Getting started


### From source

 - Check out the pinolo source code using git:

	git clone git@code.dyne.org:pinolo.git

 - Install the needed python libraries (including the development
   libraries); with Debian/Ubuntu this is usually:

	apt-get intall python-gevent python-sqlalchemy

   Or with pip:

	pip install -r doc/requirements.txt

 - Install pinolo:

	python setup.py install


### Development mode

- Install pinolo in development mode:

	cd pinolo/
	pip install -e ./


## Notes

The code is messy and ugly.


## License

BSD, see included *LICENSE* file.
