# encoding: utf-8
from pdef import ast
from pdef.preconditions import *
from pdef.lang.symbols import SymbolTable
from pdef.lang.types import Type, ParameterizedType, Variable


class Message(Type):
    @classmethod
    def from_node(cls, node, module=None):
        check_isinstance(node, ast.Message)
        message = Message(node.name, variables=(Variable(var) for var in node.variables),
                          module=module)
        message.node = node
        return message

    def __init__(self, name, variables=None, module=None):
        super(Message, self).__init__(name, variables, module)

        self.base = None
        self.bases = None

        self.base_tree = None
        self.root_tree = None

        self.fields = None
        self.declared_fields = None

        self.node = None

    @property
    def parent(self):
        return self.module

    @property
    def tree(self):
        return self.root_tree if self.root_tree else self.base_tree

    def _do_init(self):
        if not self.node:
            return
        node = self.node

        # Force base initialization for correct type tree and fields checks.
        base = self.lookup(node.base) if node.base else None
        base.init()
        subtype = self.lookup(node.subtype) if node.subtype else None

        declared_fields = SymbolTable(self)
        for field_node in node.declared_fields:
            fname = field_node.name
            ftype = self.lookup(field_node.type)
            field = Field(fname, ftype)
            declared_fields.add(field)

        if node.type:
            type = self.lookup(node.type) if node.type else None
            type_field = declared_fields.get(node.type_field)
            if not type_field:
                raise ValueError('Tree field "%s" is not found in %s' % (node.type_field, self))
        else:
            type = None
            type_field = None

        self.build(type=type, type_field=type_field,
                   base=base, subtype=subtype,
                   declared_fields=declared_fields)

    def build(self, type=None, type_field=None, base=None, subtype=None, declared_fields=None):
        self._set_type(type, type_field)
        self._set_base(base, subtype)
        self._set_fields(*(declared_fields if declared_fields else ()))

        self.inited = True

    def _set_type(self, type, field):
        if type is None and field is None:
            return
        self.root_tree = RootTree(self, type, field)

    def _set_base(self, base, subtype):
        '''Set this message base message and its type.'''
        if base is None and subtype is None:
            self.bases = []
            return

        check_isinstance(base, Message)
        check_isinstance(subtype, EnumValue)
        check_argument(base.inited, '%s must be initialized to be used as base of %s', base, self)
        check_argument(self != base, '%s cannot inherit itself', self)
        check_argument(not self in base.bases, 'Circular inheritance: %s',
                       '->'.join(str(b) for b in ([self, base] + list(base.bases))))

        self.base = check_not_none(base)
        self.bases = tuple([base] + list(base.bases))
        self.base_tree = base.tree.subtree(self, subtype)

    def _set_fields(self, *declared_fields):
        self.fields = SymbolTable(self)
        self.declared_fields = SymbolTable(self)
        if self.base:
            self.fields += self.base.fields

        for field in declared_fields:
            self.declared_fields.add(field)
            self.fields.add(field)

    def _do_parameterize(self, *variables):
        '''Parameterize this message with the given arguments, return another message.'''
        return ParameterizedMessage(self, *variables)


class ParameterizedMessage(ParameterizedType):
    def __init__(self, rawtype, variables):
        super(ParameterizedMessage, self).__init__(rawtype, variables)

        self.base = None
        self.bases = None

        self.fields = None
        self.declared_fields = None

    @property
    def tree(self):
        return self.rawtype.tree

    @property
    def base_tree(self):
        return self.rawtype.base_tree

    @property
    def root_tree(self):
        return self.rawtype.root_tree

    def init(self):
        super(ParameterizedMessage, self).init()

        vmap = self.variables.as_map()
        rawtype = self.rawtype
        base = rawtype.base.bind(vmap) if rawtype.base else None

        self.base = base
        self.bases = tuple([base] + list(base.bases)) if base else tuple()

        self.fields = SymbolTable(self)
        self.declared_fields = SymbolTable(self)
        if base:
            self.fields += base.fields

        for field in rawtype.declared_fields:
            bfield = field.bind(vmap)
            self.declared_fields.add(bfield)


class Field(object):
    def __init__(self, name, type):
        self.name = name
        self.type = type

    def bind(self, vmap):
        '''Bind this field type and return a new field.'''
        btype = self.type.bind(vmap)
        if btype == self.type:
            return self

        return Field(self.name, btype)


class AbstractMessageTree(object):
    # Implement in subclasses
    field = None
    enum = None

    def __init__(self, message, type):
        self.basetree = None
        self.message = message
        self.type = type
        self.subtypes = SymbolTable(self)
        self.subtypes.add(message, type)

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self)

    def __str__(self):
        return 'tree on %s of %s in %s' % (self.field, self.enum, self.message)

    def subtree(self, submessage, subtype):
        self.add(submessage, subtype)
        return SubTree(submessage, subtype, self)

    def add(self, submessage, subtype):
        check_isinstance(submessage, Message)
        check_isinstance(subtype, EnumValue)

        message = self.message
        enum = self.enum
        subtypes = self.subtypes

        check_argument(message in (submessage.bases or ()),
                '%s must inherit %s', submessage, message)
        check_argument(subtype in enum,
                'Wrong subtype in %s, it must be a value of enum %s, got %s',
                submessage, enum, subtype)
        check_state(subtype not in subtypes,
                'Duplicate messages %s, %s for subtype %s in %s tree',
                submessage, subtypes.get(subtype), subtype, message)

        self.subtypes.add(submessage, subtype)
        if self.basetree:
            self.basetree.add(submessage, subtype)

    def as_map(self):
        return self.subtypes.as_map()


class RootTree(AbstractMessageTree):
    def __init__(self, message, type, field):
        super(RootTree, self).__init__(message, type)
        check_isinstance(type, EnumValue)
        check_isinstance(field, Field)
        check_argument(type in field.type)

        self.field = field
        self.enum = field.type


class SubTree(AbstractMessageTree):
    def __init__(self, message, type, basetree):
        super(SubTree, self).__init__(message, type)
        self.basetree = basetree

    @property
    def field(self):
        return self.basetree.field

    @property
    def enum(self):
        return self.basetree.enum


class Enum(Type):
    @classmethod
    def from_node(cls, node):
        check_isinstance(node, ast.Enum)
        enum = Enum(node.name)
        for name in node.values:
            EnumValue(name, enum)

        return enum

    def __init__(self, name, module=None, values=None):
        super(Enum, self).__init__(name, module=module)
        self.values = SymbolTable(self)
        if values:
            self.add_values(*values)

    def add_value(self, value):
        self.values.add(value)
        self.symbols.add(value)

    def add_values(self, *values):
        map(self.add_value, values)

    def __contains__(self, enum_value):
        return enum_value in self.values.as_map().values()


class EnumValue(Type):
    def __init__(self, name, enum):
        super(EnumValue, self).__init__(name, module=enum.module)
        self.enum = enum
        enum.add_value(self)

    @property
    def parent(self):
        return self.enum


class Native(Type):
    @classmethod
    def from_node(cls, node):
        return Native(node.name, variables=(Variable(var) for var in node.variables))

    def __init__(self, name, variables=None, options=None, module=None):
        super(Native, self).__init__(name, variables, module=module)
        self.options = options

    def _do_parameterize(self, variables):
        '''Parameterize this native with the given variables and return a new one.'''
        return ParameterizedNative(self, variables)


class NativeOptions(object):
    def __init__(self, java_type=None, java_boxed=None, java_descriptor=None, java_default=None):
        self.java_type = java_type
        self.java_boxed = java_boxed
        self.java_descriptor = java_descriptor
        self.java_default = java_default


class ParameterizedNative(ParameterizedType):
    @property
    def options(self):
        return self.rawtype.options
