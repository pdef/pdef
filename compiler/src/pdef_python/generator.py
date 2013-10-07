# encoding: utf-8
import os.path

from pdef_compiler import generator
from pdef_compiler.ast import TypeEnum


class PythonGenerator(generator.Generator):
    '''Python source code generator.'''
    def __init__(self, out, namespaces=None):
        self.out = out
        self.namespace = pynamespace(namespaces)
        self.templates = pytemplates()

    def generate(self, package):
        pymodules = [PythonModule(module, self.namespace) for module in package.modules]
        self._mark_modules_as_dirs(pymodules)

        for pm in pymodules:
            pm.write(self.out, self.templates)

    @staticmethod
    def _mark_modules_as_dirs(pymodules):
        parent_names = PythonGenerator._modules_with_children([pm.name for pm in pymodules])

        for pm in pymodules:
            if pm.name in parent_names:
                pm.is_directory = True

    @staticmethod
    def _modules_with_children(module_names):
        parent_names = set()

        for name in module_names:
            if '.' not in name:
                # It's a simple module without children.
                continue

            # Add all modules in a name as distinct modules, except for the last one,
            # i.e. mycompany.service.client.tests:
            # mycompany
            # mycompany.service
            # mycompany.service.client
            # but not mycompany.service.client.tests
            pname = ''
            parts = name.split('.')[:-1]
            for part in parts:
                pname = part if not pname else (pname + '.' + part)
                parent_names.add(pname)

        return parent_names


class PythonModule(object):
    '''Python module.'''
    template_name = 'module.template'

    def __init__(self, module, namespace=None):
        # Create a local module scope, which correctly handles
        # when definitions are referenced inside the declaring module.
        scope = lambda type0: pyreference(type0, module, namespace)

        self.name = namespace(module.name) if namespace else module.name
        self.doc = pydoc(module.doc)

        self.imports = [pyimport(im, namespace) for im in module.imported_modules]
        self.definitions = [PythonDefinition.create(def0, scope) for def0 in module.definitions]

        # The flag distinguishes between mymodule.py and mymodule/__init__.py.
        self.is_directory = False

    def write(self, out, templates):
        '''Write this module file.'''
        code = self.render(templates)

        dirpath = self.dirpath(out)
        generator.mkdir_p(dirpath)

        filepath = self.filepath(out)
        with open(filepath, 'wt') as f:
            f.write(code)

    def render(self, templates):
        '''Render this module and return its source code.'''
        defs = []
        for def0 in self.definitions:
            code = def0.render(templates)
            defs.append(code)

        template = templates.get(self.template_name)
        return template.render(name=self.name, doc=self.doc, imports=self.imports,
                               definitions=defs)

    @property
    def is_file(self):
        return not self.is_directory

    def dirpath(self, out):
        dirname = self.dirname
        if dirname is None:
            return out

        return os.path.join(out, dirname)

    def filepath(self, out):
        dirpath = self.dirpath(out)
        filename = self.filename
        return os.path.join(dirpath, filename)

    @property
    def filename(self):
        '''Return this module file name.'''
        if self.is_directory:
            return '__init__.py'

        name = self.name
        if '.' in self.name:
            # Get the last part, it's a module name.
            name = self.name.rsplit('.', 1)[1]

        return name + '.py'

    @property
    def dirname(self):
        '''Return this module directory name or None.'''
        if self.is_file and not '.' in self.name:
            return None

        name = self.name
        if self.is_file:
            # Get the first part without the module name.
            name = self.name.rsplit('.', 1)[0]

        parts = name.split('.')
        return os.path.join(*parts)


class PythonDefinition(object):
    template_name = None

    @classmethod
    def create(cls, def0, scope):
        '''Create a python definition.'''
        if def0.is_message:
            return PythonMessage(def0, scope)

        elif def0.is_enum:
            return PythonEnum(def0)

        elif def0.is_interface:
            return PythonInterface(def0, scope)

        raise ValueError('Unsupported definition %s' % def0)

    def render(self, templates):
        template = templates.get(self.template_name)
        return template.render(**self.__dict__)


class PythonEnum(PythonDefinition):
    template_name = 'enum.template'

    def __init__(self, enum):
        self.name = enum.name
        self.doc = pydoc(enum.doc)
        self.values = [value.name for value in enum.values]


class PythonMessage(PythonDefinition):
    template_name = 'message.template'

    def __init__(self, msg, scope):
        self.name = msg.name
        self.doc = pydoc(msg.doc)

        self.base = scope(msg.base)
        self.subtypes = [(scope(stype.discriminator_value), scope(stype))
                         for stype in msg.subtypes]
        self.discriminator_value = scope(msg.discriminator_value)
        self.discriminator = PythonField(msg.discriminator, scope) if msg.discriminator else None

        self.is_exception = msg.is_exception
        self.is_form = msg.is_form

        self.fields = [PythonField(field, scope) for field in msg.fields]
        self.inherited_fields = [PythonField(field, scope) for field in msg.inherited_fields]
        self.declared_fields = [PythonField(field, scope) for field in msg.declared_fields]

        self.root_or_base = self.base or ('pdef.Exc' if self.is_exception else 'pdef.Message')


class PythonField(object):
    def __init__(self, field, scope):
        self.name = field.name
        self.type = scope(field.type)
        self.is_discriminator = field.is_discriminator


class PythonInterface(PythonDefinition):
    template_name = 'interface.template'

    def __init__(self, iface, scope):
        self.name = iface.name
        self.doc = pydoc(iface.doc)
        self.exc = scope(iface.exc) if iface.exc else None
        self.declared_methods = [PythonMethod(m, scope) for m in iface.declared_methods]


class PythonMethod(object):
    def __init__(self, method, scope):
        self.name = method.name
        self.doc = pydoc(method.doc)

        self.result = scope(method.result)
        self.args = [PythonArg(arg, scope) for arg in method.args]

        self.is_index = method.is_index
        self.is_post = method.is_post


class PythonArg(object):
    def __init__(self, arg, scope):
        self.name = arg.name
        self.type = scope(arg.type)


class PythonReference(object):
    @classmethod
    def list(cls, type0, module, namespace):
        element = pyreference(type0.element, module, namespace)
        descriptor = 'descriptors.list0(%s)' % element.descriptor

        return PythonReference('list', descriptor)

    @classmethod
    def set(cls, type0, module, namespace):
        element = pyreference(type0.element, module, namespace)
        descriptor = 'descriptors.set0(%s)' % element.descriptor

        return PythonReference('set', descriptor)

    @classmethod
    def map(cls, type0, module, namespace):
        key = pyreference(type0.key, module, namespace)
        value = pyreference(type0.value, module, namespace)
        descriptor = 'descriptors.map0(%s, %s)' % (key.descriptor, value.descriptor)

        return PythonReference('dict', descriptor)

    @classmethod
    def enum_value(cls, type0, module, namespace):
        enum = pyreference(type0.enum, module, namespace)
        name = '%s.%s' % (enum.name, type0.name)

        return PythonReference(name, None)

    @classmethod
    def definition(cls, type0, module, namespace):
        if type0.module == module:
            # The definition is referenced from the declaring module.
            name = type0.name
        else:
            module_name = type0.module.name
            module_name = namespace(module_name) if namespace else module_name
            name = '%s.%s' % (module_name, type0.name)

        descriptor = '%s.__descriptor__' % name
        return PythonReference(name, descriptor)

    def __init__(self, name, descriptor):
        self.name = name
        self.descriptor = descriptor

    def __str__(self):
        return str(self.name)


NATIVE_TYPES = {
    TypeEnum.BOOL: PythonReference('bool', 'descriptors.bool0'),
    TypeEnum.INT16: PythonReference('int', 'descriptors.int16'),
    TypeEnum.INT32: PythonReference('int', 'descriptors.int32'),
    TypeEnum.INT64: PythonReference('int', 'descriptors.int64'),
    TypeEnum.FLOAT: PythonReference('float', 'descriptors.float0'),
    TypeEnum.DOUBLE: PythonReference('float', 'descriptors.double0'),
    TypeEnum.STRING: PythonReference('unicode', 'descriptors.string'),
    TypeEnum.OBJECT: PythonReference('object', 'descriptors.object0'),
    TypeEnum.VOID: PythonReference('object', 'descriptors.void'),
}


def pytemplates():
    '''Return python generator templates.'''
    return generator.Templates(__file__)


def pyreference(type0, module=None, namespace=None):
    '''Create a python reference.

        @param type0:   pdef definition.
        @param module:  pdef module in which the definition is referenced.
        @param namespace:  optional module name namespace.
        '''
    if type0 is None:
        return None

    elif type0.is_native:
        return NATIVE_TYPES[type0.type]

    elif type0.is_list:
        return PythonReference.list(type0, module, namespace)

    elif type0.is_set:
        return PythonReference.set(type0, module, namespace)

    elif type0.is_map:
        return PythonReference.map(type0, module, namespace)

    elif type0.is_enum_value:
        return PythonReference.enum_value(type0, module, namespace)

    return PythonReference.definition(type0, module, namespace)


def pyimport(imported_module, namespace=None):
    '''Create a python import string.'''
    if not namespace:
        return imported_module.module.name
    return namespace(imported_module.module.name)


def pynamespace(namespaces=None):
    return generator.Namespace(namespaces)


def pydoc(doc):
    if not doc:
        return ''

    # Escape the python docstrings delimiters,
    # and strip empty characters.
    s = doc.replace('"""', '\"\"\"').strip()

    if '\n' not in s:
        # It's a one-line comment.
        return s

    # It's a multi-line comment.
    return '\n' + s + '\n\n'
