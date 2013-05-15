# -*- coding: utf-8


# http://stackoverflow.com/questions/2082152/case-insensitive-dictionary
class CaseInsensitiveDict(dict):
    def __setitem__(self, key, value):
        super(Caseinsensitivedict, self).__setitem__(key.lower(), value)

    def __getitem__(self, key):
        return super(Caseinsensitivedict, self).__getitem__(key.lower())
