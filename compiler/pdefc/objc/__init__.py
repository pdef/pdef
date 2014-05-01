# encoding: utf-8
from __future__ import unicode_literals

from pdefc import lang, __version__
from pdefc.templates import Templates, write_file, upper_first, lower_first


IMPL_TEMPLATE = 'impl.jinja2'
HEADER_TEMPLATE = 'header.jinja2'

STRUCT_SUFFIX = 'Struct'
INTERFACE_SUFFIX = 'Interface'
GENERATED_BY = 'Generated by Pdef compiler %s. DO NOT EDIT.' % __version__


def generate(package, dst, prefix=None):
    generator = Generator(prefix)
    return generator.generate(package, dst)


class Generator(object):
    def __init__(self, prefix=None):
        self.prefix = prefix or ''
        self.templates = Templates(__file__, filters=self)

    def generate(self, package, dst):
        for file in package.files:
            for type0 in file.types:
                name = self.objc_name(type0)
                template_h, template_m = self._template_names(type0)
                self._generate(type0, dst, '%s.h' % name, template_h)
                self._generate(type0, dst, '%s.m' % name, template_m)

    def _generate(self, type0, dst, filename, tmpl):
        name = self.objc_name(type0)
        code = self.templates.render(tmpl, definition=type0, name=name, generated_by=GENERATED_BY)
        write_file(dst, filename, code)
    
    def _template_names(self, type0):
        if type0.is_struct:
            return 'struct_h.jinja2', 'struct_m.jinja2'
        elif type0.is_interface:
            return 'interface_h.jinja2', 'interface_m.jinja2'
        elif type0.is_enum:
            return 'enum_h.jinja2', 'enum_m.jinja2'

    def objc_name(self, type0):
        name = self.prefix + type0.name
        suffix = STRUCT_SUFFIX if type0.is_struct \
            else INTERFACE_SUFFIX if type0.is_interface else None
        
        if not suffix or name.lower().endswith(suffix.lower()):
            return name

        return name + suffix

    def objc_type(self, type0):
        '''Return an objective-c type.'''
        if type0 in _TYPES:
            return _TYPES[type0]

        if type0.is_list:
            return 'NSArray *'
        elif type0.is_set:
            return 'NSSet *'
        elif type0.is_map:
            return 'NSDictionary *'
        elif type0.is_enum:
            return '%s ' % self.objc_name(type0)

        return '%s *' % (self.objc_name(type0))

    def objc_reflex(self, type0):
        '''Return an objective-c reflection type.'''
        if type0 in _REFLEX_TYPES:
            return _REFLEX_TYPES[type0]

        if type0.is_list:
            return '[PDList listWithItem:%s]' % self.objc_reflex(type0.element)
        elif type0.is_set:
            return '[PDSet setWithItem:%s]' % self.objc_reflex(type0.element)
        elif type0.is_map:
            key = self.objc_reflex(type0.key)
            value = self.objc_reflex(type0.value)
            return '[PDMap mapWithKey:%s value:%s]' % (key, value)
        elif type0.is_enum:
            return '%sEnum.class' % self.objc_name(type0)
        
        return '%s.class' % self.objc_name(type0)
    
    def objc_signature(self, method):
        '''Return a method signature.'''
        s = []
        if method.is_last:
            s.append('- (RACSignal *)')
        else:
            s.append('- (%s)' % self.objc_type(method.result))
        s.append(method.name)
        
        is_first = True
        colon_index = 0
        for arg in method.args:
            if is_first:
                s.append(upper_first(arg.name))
                s.append(':')
                is_first = False
                colon_index = ''.join(s).index(':')
            else:
                s.append('\n')
                spaces = max(colon_index - len(arg.name), 0)
                s.append(' ' * spaces)
                s.append(arg.name)
                s.append(':')

            s.append('(%s)' % self.objc_type(arg.type).strip())
            s.append(arg.name)
        
        return ''.join(s)
    
    def objc_selector(self, method):
        s = [method.name]
        
        is_first = True
        for arg in method.args:
            if is_first:
                s.append(upper_first(arg.name))
                is_first = False
            else:
                s.append(arg.name)
            s.append(':')
        
        return ''.join(s)
                    
    def objc_method_options(self, method):
        s = []
        if method.is_get:
            s.append('PDMethodGet')
        elif method.is_post:
            s.append('PDMethodPost')
        if method.is_request:
            s.append('|PDMethodRequest')
        return ''.join(s)


# Mind end spaces and pointers.
_TYPES = {
    lang.BOOL: 'BOOL ',
    lang.INT16: 'int16_t ',
    lang.INT32: 'int32_t ',
    lang.INT64: 'int64_t ',
    lang.FLOAT: 'float ',
    lang.DOUBLE: 'double ',
    lang.STRING: 'NSString *',
    lang.DATETIME: 'NSDate *',
    lang.VOID: 'void ',
}

_REFLEX_TYPES = {
    lang.BOOL: '@(PDTypeBool)',
    lang.INT16: '@(PDTypeInt16)',
    lang.INT32: '@(PDTypeInt32)',
    lang.INT64: '@(PDTypeInt64)',
    lang.FLOAT: '@(PDTypeFloat)',
    lang.DOUBLE: '@(PDTypeDouble)',
    lang.STRING: '@(PDTypeString)',
    lang.DATETIME: '@(PDTypeDate)',
    lang.VOID: '@(PDTypeVoid)',
}
