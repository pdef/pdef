# encoding: utf-8
from collections import defaultdict
import logging
import re
import itertools
import yaml
from pdefc.exc import CompilerException


class Package(object):
    '''Protocol definition.'''
    name_pattern = re.compile(r'^[a-zA-Z]{1}[a-zA-Z0-9_\-]*$')

    def __init__(self, name, info=None, modules=None, dependencies=None):
        self.name = name
        self.info = info
        self.modules = []
        self.dependencies = []

        if modules:
            for module in modules:
                self.add_module(module)

        if dependencies:
            for dep in dependencies:
                self.add_dependency(dep)

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<Package %r at %s>' % (self.name, hex(id(self)))

    def add_dependency(self, package):
        '''Adds all modules from another package to this package dependencies.'''
        if package is self:
            raise ValueError('Cannot include itself %r' % self)

        self.dependencies.append(package)
        logging.debug('%s: added a dependency "%s"', self, package.name)

    def get_dependency(self, name):
        '''Return a package by a name.'''
        for dep in self.dependencies:
            if dep.name == name:
                return dep

    def add_module(self, module):
        '''Add a module to this package.'''
        self.modules.append(module)
        logging.debug('%s: added a module "%s"', self, module.name)

    def get_module(self, name):
        '''Find a module in this package by a name.'''
        for module in self.modules:
            if module.name == name:
                return module

    def lookup_module(self, absolute_name):
        '''Find a module in this package or its dependencies by an absolute name.'''
        if '.' not in absolute_name:
            absolute_name = '%s.%s' % (absolute_name, absolute_name)

        pname, mname = absolute_name.split('.', 1)
        if pname == self.name:
            return self.get_module(mname)

        package = self.get_dependency(pname)
        if package:
            return package.get_module(mname)

        return None

    def compile(self):
        '''Compile this package and return a list of errors.'''
        logging.info('Compiling %s', self)

        errors = self._link()
        if errors:
            raise CompilerException('Linking errors', errors)

        errors = self._build()
        if errors:
            raise CompilerException('Building errors', errors)

        errors = self._validate()
        if errors:
            raise CompilerException('Validation errors', errors)

        return []

    def _link(self):
        '''Link this package and return a list of errors.'''
        logging.debug('Linking the package')

        errors = []

        # Prevent duplicate module names.
        names = set()
        for module in self.modules:
            if module.name in names:
                errors.append(self._error('Duplicate module %r', module.name))
            names.add(module.name)

        if errors:
            return errors

        # Link modules.
        for module in self.modules:
            errors += module.link(self)

        return errors

    def _build(self):
        '''Build this package and return a list of errors.'''
        logging.debug('Building the package')

        errors = []
        for module in self.modules:
            errors += module.build()
        return errors

    def _validate(self):
        '''Validate this package and return a list of errors.'''
        logging.debug('Validating the package')

        errors = []
        errors += self._validate_name()
        for module in self.modules:
            errors += module.validate()

        if errors:
            return errors

        return self._validate_namespaces()

    def _validate_name(self):
        if not self.name:
            return [self._error('Package name required, add it to the YAML file')]
        if self.name_pattern.match(self.name):
            return []
        return [self._error('Wrong package name "%s". A name must contain only latin letters, '
                            'digits and underscores, and must start with a letter, for example, '
                            '"mycompany_project_api"', self.name)]

    def _validate_namespaces(self):
        errors = []
        names_to_modules = defaultdict(set)

        for package in itertools.chain([self], self.dependencies):
            for module in package.modules:
                for def0 in module.definitions:
                    names_to_modules[def0.fullname].add(def0.module)

        for name, modules in names_to_modules.items():
            if len(modules) == 1:
                continue

            msg = self._error('Duplicate definition "%s":', name)
            errors.append(msg)
            for module in modules:
                errors.append(self._error('  %s', module.filename or module.name))

        return errors

    def _error(self, msg, *args):
        record = msg % args if args else msg
        logging.error(record)
        return record


class PackageInfo(object):
    @classmethod
    def from_yaml(cls, s):
        d = yaml.load(s)
        return PackageInfo.from_dict(d)

    @classmethod
    def from_dict(cls, d):
        p = d.get('package', {})
        name = p.get('name')
        url = p.get('url')
        description = p.get('description')
        sources = p.get('sources')
        dependencies = p.get('dependencies')

        return PackageInfo(name, url=url, description=description, sources=sources,
                           dependencies=dependencies)

    def __init__(self, name, url=None, description=None, sources=None, dependencies=None):
        self.name = name or ''
        self.url = url
        self.description = description or ''
        self.sources = list(sources) if sources else []
        self.dependencies = list(dependencies) if dependencies else []

    def to_dict(self):
        return {
            'package': {
                'name': self.name,
                'url': self.url,
                'description': self.description,
                'sources': list(self.sources),
                'dependencies': list(self.dependencies)
            }
        }

    def to_yaml(self):
        return yaml.dump(self.to_dict())
