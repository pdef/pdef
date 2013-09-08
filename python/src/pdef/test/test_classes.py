# encoding: utf-8
import unittest
from mock import Mock
from pdef import Proxy, Invocation, InvocationResult
from pdef.test.messages_pd import SimpleMessage
from pdef.test.interfaces_pd import TestInterface, TestException


class TestMessage(unittest.TestCase):
    JSON = '''{"aString": "hello", "aBool": true}'''

    def _fixture(self):
        return SimpleMessage(aString="hello", aBool=True)

    def _fixture_dict(self):
        return {'aString': 'hello', 'aBool': True}

    def test_parse_json(self):
        msg = SimpleMessage.parse_json(self.JSON)
        assert msg == self._fixture()

    def test_parse_dict(self):
        msg = self._fixture()
        d = msg.to_dict()

        msg1 = SimpleMessage.parse_dict(d)
        assert msg == msg1

    def test_to_json(self):
        msg = self._fixture()
        s = msg.to_json()

        msg1 = SimpleMessage.parse_json(s)
        assert msg == msg1

    def test_to_dict(self):
        d = self._fixture().to_dict()

        assert d == self._fixture_dict()

    def test_eq(self):
        msg0 = self._fixture()
        msg1 = self._fixture()
        assert msg0 == msg1

        msg1.aString = 'qwer'
        assert msg0 != msg1


class TestProxy(unittest.TestCase):
    def proxy(self):
        return Proxy(TestInterface.__descriptor__, lambda invocation: InvocationResult(invocation))

    def test_invoke_capture(self):
        subproxy = self.proxy().interfaceMethod(1, 2)

        invocation = subproxy._invocation
        assert invocation.method.name == 'interfaceMethod'
        assert invocation.args == {'a': 1, 'b': 2}

    def test_invoke_capture_chain(self):
        chain = self.proxy().interfaceMethod(1, 2).remoteMethod().to_chain()
        invocation0 = chain[0]
        invocation1 = chain[1]

        assert invocation0.method.name == 'interfaceMethod'
        assert invocation0.args == {'a': 1, 'b': 2}

        assert invocation1.method.name == 'remoteMethod'
        assert invocation1.args == {}

    def test_invoke_handle_ok(self):
        proxy = Proxy(TestInterface.__descriptor__, lambda inv: InvocationResult(3))
        result = proxy.indexMethod(1, 2)

        assert result == 3

    def test_invoke_handle_exc(self):
        exc = TestException('hello')
        proxy = Proxy(TestInterface.__descriptor__, lambda inv: InvocationResult(exc, ok=False))

        try:
            proxy.indexMethod(1, 2)
            assert False
        except TestException, e:
            assert e == exc


class TestInvocation(unittest.TestCase):
    def method(self):
        return TestInterface.__descriptor__.find_method('indexMethod')

    def interface_method(self):
        return TestInterface.__descriptor__.find_method('interfaceMethod')

    def test_init(self):
        method = self.method()
        invocation = Invocation(method, None, args=[1, 2])

        assert invocation.method is method
        assert invocation.args == {'a': 1, 'b': 2}
        assert invocation.exc is TestException.__descriptor__
        assert invocation.result is method.result

    def test_init__check_arg_types(self):
        method = self.method()
        self.assertRaises(TypeError, Invocation, method, None, args=[1, 'string'])

    def test_next(self):
        method = self.method()

        root = Invocation.root()
        invocation = root.next(method, 1, 2)

        assert invocation.parent is root
        assert invocation.method is method
        assert invocation.args == {'a': 1, 'b': 2}

    def test_to_chain(self):
        method0 = self.interface_method()
        method1 = method0.result.methods[0]

        root = Invocation.root()
        invocation0 = root.next(method0)
        invocation1 = invocation0.next(method1)

        chain = invocation1.to_chain()
        assert chain == [invocation0, invocation1]

    def test_build_args(self):
        method = self.method()
        build = lambda args, kwargs: Invocation._build_args(method, args, kwargs)
        expected = {'a': 1, 'b': 2}

        assert build([1, 2], None) == expected
        assert build(None, {'a': 1, 'b': 2}) == expected
        assert build([1], {'b': 2}) == expected
        assert build(None, None) == {'a': None, 'b': None}

        self.assertRaises(TypeError, build, [1, 2, 3], None)
        self.assertRaises(TypeError, build, [1, 2], {'a': 1, 'b': 2})
        self.assertRaises(TypeError, build, None, {'a': 1, 'b': 2, 'c': 3})
        self.assertRaises(TypeError, build, None, {'c': 3})

    def test_invoke(self):
        class Service(TestInterface):
            def indexMethod(self, a=None, b=None):
                return a + b

        method = self.method()
        invocation = Invocation.root().next(method, 1, 2)
        result = invocation.invoke(Service())

        assert result.ok
        assert result.data == 3

    def test_invoke_exc(self):
        class Service(TestInterface):
            def indexMethod(self, a=None, b=None):
                raise TestException('hello')

        method = self.method()
        invocation = Invocation.root().next(method, 1, 2)
        result = invocation.invoke(Service())

        assert result.ok is False
        assert result.data == TestException('hello')
