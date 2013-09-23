# encoding: utf-8
import unittest
from mock import Mock

from pdef import descriptors
from pdef_test import messages, inheritance, interfaces


class TestMessageDescriptor(unittest.TestCase):
    cls = messages.SimpleMessage
    descriptor = cls.__descriptor__

    def _fixture(self):
        return self.cls(aString='hello', aBool=True, anInt16=123)

    def _fixture_dict(self):
        return {'aString': 'hello', 'aBool': True, 'anInt16': 123}

    def _fixture_json(self):
        return '{"aString": "hello", "aBool": true, "anInt16": 123}'

    def test_subtype(self):
        subtype = self.descriptor.subtype(None)
        assert subtype is self.cls

    def test_to_object(self):
        msg = self._fixture()
        d = self.descriptor.to_object(msg)
        assert d == self._fixture_dict()

    def test_to_object__none(self):
        assert self.descriptor.to_object(None) is None

    def test_to_object__check_type(self):
        msg = self._fixture()
        msg.aString = True

        self.assertRaises(TypeError, self.descriptor.to_object, msg)

    def test_parse_object(self):
        d = self._fixture_dict()
        msg = self.descriptor.parse_object(d)
        assert msg == self._fixture()

    def test_parse_object__none(self):
        assert self.descriptor.parse_object(None) is None

    def test_parse_json(self):
        s = self._fixture_json()
        msg = self.descriptor.parse_json(s)
        assert msg == self._fixture()

    def test_to_json(self):
        msg = self._fixture()
        s = self.descriptor.to_json(msg)
        msg1 = self.descriptor.parse_json(s)
        assert msg == msg1


class TestPolymorphicMessageDescriptor(unittest.TestCase):
    descriptor = inheritance.Base.__descriptor__

    def test_subtype(self):
        d = self.descriptor

        assert d.subtype(inheritance.PolymorphicType.SUBTYPE) is inheritance.Subtype
        assert d.subtype(inheritance.PolymorphicType.SUBTYPE2) is inheritance.Subtype2
        assert d.subtype(inheritance.PolymorphicType.MULTILEVEL_SUBTYPE) \
            is inheritance.MultiLevelSubtype

    def test_parse_object(self):
        subtype_d = {'type': 'subtype', 'subfield': 'hello'}
        subtype2_d = {'type': 'subtype2', 'subfield2': 'hello'}
        mlevel_subtype_d = {'type': 'multilevel_subtype', 'mfield': 'hello'}

        d = self.descriptor
        assert d.parse_object(subtype_d) == inheritance.Subtype(subfield='hello')
        assert d.parse_object(subtype2_d) == inheritance.Subtype2(subfield2='hello')
        assert d.parse_object(mlevel_subtype_d) == inheritance.MultiLevelSubtype(mfield='hello')


class TestFieldDescriptor(unittest.TestCase):
    cls = messages.SimpleMessage
    descriptor = cls.__descriptor__
    field = descriptor.find_field('aString')

    def test_set(self):
        msg = self.cls()
        self.field.set(msg, 'hello')
        assert msg.aString == 'hello'

    def test_set__check_type(self):
        msg = self.cls()
        self.assertRaises(TypeError, self.field.set, msg, 123)

    def test_get(self):
        msg = self.cls(aString='hello')
        assert self.field.get(msg) == 'hello'

    def test_get__check_type(self):
        msg = self.cls(aString=123)
        self.assertRaises(TypeError, self.field.get, msg)


class TestInterfaceDescriptor(unittest.TestCase):
    descriptor = interfaces.TestInterface.__descriptor__

    def test_exc(self):
        assert self.descriptor.exc is interfaces.TestException.__descriptor__

    def test_methods(self):
        assert  len(self.descriptor.methods) == 9


class TestMethodDescriptor(unittest.TestCase):
    def test_result(self):
        method = descriptors.method('method', lambda: descriptors.void)
        assert method.result is descriptors.void

    def test_is_remote__datatype(self):
        method = descriptors.method('method', lambda: descriptors.string)
        assert method.is_remote

    def test_is_remote__void(self):
        method = descriptors.method('method', lambda: descriptors.void)
        assert method.is_remote

    def test_is_remote__interface(self):
        method = descriptors.method('method', lambda: descriptors.interface(object))
        assert method.is_remote is False

    def test_invoke(self):
        service = Mock()
        method = descriptors.method('method', lambda: descriptors.void)
        method.invoke(service)
        service.method.assert_called_with()


class TestPrimitiveDescriptor(unittest.TestCase):
    descriptor = descriptors.int32

    def parse(self):
        assert self.descriptor.parse_object(123) == 123

    def parse__none(self):
        assert self.descriptor.parse_object(None) is None

    def parse__string(self):
        assert self.descriptor.parse_object('123') == 123

    def parse_string__none(self):
        assert self.descriptor.parse_string(None) is None

    def serialize(self):
        assert self.descriptor.to_object(123) == 123

    def serialize__none(self):
        assert self.descriptor.to_object(None) is None

    def serialize_to_string(self):
        assert self.descriptor.to_string(123) == '123'

    def serialize_to_string__none(self):
        assert self.descriptor.to_string(None) is None


class TestBoolDescriptor(unittest.TestCase):
    descriptor = descriptors.bool0

    def parse_string__true(self):
        assert self.descriptor.parse_string('TruE') is True

    def parse_string__false(self):
        assert self.descriptor.parse_string('FalsE') is False

    def parse_string__value_error(self):
        self.assertRaises(ValueError, self.descriptor.parse_string, 'wrong value')

    def serialize_to_string(self):
        assert self.descriptor.to_string(True) == 'true'


class TestEnumDescriptor(unittest.TestCase):
    cls = messages.TestEnum
    descriptor = cls.__descriptor__

    def test_parse(self):
        enum = self.descriptor.parse_object('one')
        assert enum == self.cls.ONE

    def test_parse__none(self):
        assert self.descriptor.parse_object(None) is None

    def test_parse_string(self):
        assert self.descriptor.parse_string('TwO') == self.cls.TWO

    def test_parse_string__none(self):
        assert self.descriptor.parse_string(None) is None

    def test_serialize(self):
        assert self.descriptor.to_object(self.cls.THREE) == 'three'

    def test_serialize__none(self):
        assert self.descriptor.to_object(None) is None

    def test_serialize_to_string(self):
        assert self.descriptor.to_string(self.cls.THREE) == 'three'

    def test_serialize_to_string__none(self):
        assert self.descriptor.to_string(None) is None


class TestListDescriptor(unittest.TestCase):
    descriptor = descriptors.list0(descriptors.int32)

    def test_parse(self):
        assert self.descriptor.parse_object(['1', 2]) == [1, 2]

    def test_parse__none(self):
        assert self.descriptor.parse_object(None) is None

    def test_serialize(self):
        assert self.descriptor.to_object([1, 2]) == [1, 2]

    def test_serialize__none(self):
        assert self.descriptor.to_object(None) is None


class TestSetDescriptor(unittest.TestCase):
    descriptor = descriptors.set0(descriptors.int32)

    def test_parse(self):
        assert self.descriptor.parse_object(['1', 2, '2']) == {1, 2}

    def test_parse__none(self):
        assert self.descriptor.parse_object(None) is None

    def test_serialize(self):
        assert self.descriptor.to_object({1, 2}) == {1, 2}

    def test_serialize__none(self):
        assert self.descriptor.to_object(None) is None


class TestMapDescriptor(unittest.TestCase):
    descriptor = descriptors.map0(descriptors.int32, descriptors.int32)

    def test_parse(self):
        assert self.descriptor.parse_object({'1': '2'}) == {1: 2}

    def test_parse__none(self):
        assert self.descriptor.parse_object(None) is None

    def test_serialize(self):
        assert self.descriptor.to_object({1: 2}) == {1: 2}

    def test_serialize__none(self):
        assert self.descriptor.to_object(None) is None
