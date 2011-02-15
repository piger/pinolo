#!/usr/bin/zsh

# if [[ ! -e lib/python2.6/dist-packages ]]; then
#     mkdir lib/python2.6/dist-packages
# fi

if [[ ! -e share ]]; then
    mkdir share
fi

ln -s /usr/lib/python2.6/dist-packages/_xapian.so lib/python2.6/site-packages/
ln -s /usr/share/pyshared share/
ln -s /usr/share/pyshared-data share/
ln -s /usr/lib/python2.6/dist-packages/xapian.py lib/python2.6/site-packages/
