# encoding: utf-8
import os.path
import unittest
from pdef.parser import Parser


class TestParser(unittest.TestCase):

    def _read(self, filename):
        filepath = os.path.join(os.path.dirname(__file__), filename)
        with open(filepath, 'r') as f:
            return f.read()

    def test_parse(self):
        '''Should parse a test pdef file.'''
        s = self._read('test.pdef')
        parser = Parser()
        module = parser.parse(s)
        defs = dict((d.name, d) for d in module.definitions)

        assert module.name == 'pdef.test'
        assert 'Message' in defs

        assert 'Enum' in defs
        assert 'Interface' in defs
