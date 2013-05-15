# encoding: utf-8
import json
from pdef.java.translator import JavaTranslator
from pdef.lang import Pdef
from pdef.parser import Parser


class Compiler(object):
    def __init__(self):
        self.pdef = Pdef()
        self.parser = Parser()
        self.paths = []
        self.deps = []

        self._defs = None

    @property
    def defs(self):
        for path in self.deps:
            file_node = self.parser.parse_file(path)
            self.pdef.add_file_node(file_node)

        defs = []
        for path in self.paths:
            file_node = self.parser.parse_file(path)
            module, file_defs = self.pdef.add_file_node(file_node)
            defs += file_defs

        self._defs = tuple(defs)
        self.pdef.link()
        return self._defs

    def package(self):
        '''Generates a package from the package.json in the current directory.'''
        with open('package.json', 'rt') as f:
            text = f.read()

        info = json.loads(text)
        self.add_paths(*info['path'])
        del info['path']

        if 'deps' in info:
            self.add_deps(*info['deps'])
            del info['deps']

        for key, value in info.items():
            getattr(self, key)(**value)

    def add_deps(self, *deps):
        '''Add dependency paths.'''
        self.deps += deps

    def add_paths(self, *paths):
        '''Add definition paths.'''
        self.paths += paths

    def java(self, out, async=True):
        translator = JavaTranslator(out, async)
        for def0 in self.defs:
            translator.write_definition(def0)
