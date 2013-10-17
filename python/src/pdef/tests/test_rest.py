# encoding: utf-8
import httplib
import json
import unittest
import urllib
from mock import Mock
from StringIO import StringIO
from threading import Thread

import pdef
from pdef import descriptors
from pdef.rest import *
from pdef_test.messages import TestMessage, TestForm
from pdef_test.interfaces import TestInterface, TestException


class TestRestProtocol(unittest.TestCase):
    def setUp(self):
        handler = lambda inv: pdef.invoke.InvocationResult.from_data(inv)
        self.proxy = pdef.proxy(TestInterface, handler)
        self.protocol = RestProtocol()

    # Invocation serialization.

    def test_serialize_invocation(self):
        invocation = self.proxy.testIndex(arg0=1, arg1=2)
        request = self.protocol.serialize_invocation(invocation)

        assert request.method == 'GET'
        assert request.path == '/'
        assert request.query == {'arg0': '1', 'arg1': '2'}
        assert request.post == {}

    def test_serialize_invocation__post(self):
        invocation = self.proxy.testPost(arg0=1, arg1=2)
        request = self.protocol.serialize_invocation(invocation)

        assert request.method == 'POST'
        assert request.path == '/testPost'
        assert request.query == {}
        assert request.post == {'arg0': '1', 'arg1': '2'}

    def test_serialize_invocation__chained_methods(self):
        invocation = self.proxy.testInterface(1, 2).testString('hello')
        request = self.protocol.serialize_invocation(invocation)

        assert request.method == 'GET'
        assert request.path == '/testInterface/1/2/testString'
        assert request.query == {'text': 'hello'}
        assert request.post == {}

    def test_serialize_invocation__index_method(self):
        request = RestRequest()
        invocation = self.proxy.testIndex(arg0=1, arg1=2)
        self.protocol._serialize_single_invocation(invocation, request)

        assert request.path == '/'
        assert request.query == {'arg0': '1', 'arg1': '2'}
        assert request.post == {}

    def test_serialize_invocation__post_method(self):
        request = RestRequest()
        invocation = self.proxy.testPost(arg0=1, arg1=2)
        self.protocol._serialize_single_invocation(invocation, request)

        assert request.path == '/testPost'
        assert request.query == {}
        assert request.post == {'arg0': '1', 'arg1': '2'}

    def test_serialize_invocation__remote_method(self):
        request = RestRequest()
        invocation = self.proxy.testRemote(arg0=10, arg1=100)
        self.protocol._serialize_single_invocation(invocation, request)

        assert request.path == '/testRemote'
        assert request.query == {'arg0': '10', 'arg1': '100'}
        assert request.post == {}

    def test_serialize_invocation__interface_method(self):
        request = RestRequest()
        invocation = self.proxy.testInterface(arg0=1, arg1=2)._invocation
        self.protocol._serialize_single_invocation(invocation, request)

        assert request.path == '/testInterface/1/2'
        assert request.query == {}
        assert request.post == {}

    # Argument serialization.

    def test_serialize_path_argument(self):
        arg = descriptors.arg('arg', descriptors.string0)

        value = self.protocol._serialize_path_argument(arg, u'Привет')
        assert value == '%D0%9F%D1%80%D0%B8%D0%B2%D0%B5%D1%82'

    def test_serialize_param(self):
        arg = descriptors.arg('arg', descriptors.int32)

        dst = {}
        self.protocol._serialize_param(arg, 123, dst)
        assert dst == {'arg': '123'}

    def test_serialize_param__form(self):
        arg = descriptors.arg('arg', TestForm.DESCRIPTOR)

        dst = {}
        form = TestForm(formString=u'Привет', formList=[1, 2, 3], formBool=False)
        self.protocol._serialize_param(arg, form, dst)
        
        assert dst == {'formString': u'Привет', 'formList': '[1, 2, 3]', 'formBool': 'false'}

    def test_serialize_to_json__null(self):
        descriptor = descriptors.int32
        result = self.protocol._serialize_to_json(descriptor, None)

        assert result == 'null'

    def test_serialize_to_json__string(self):
        descriptor = descriptors.string0
        result = self.protocol._serialize_to_json(descriptor, u'привет+ромашки')

        assert result == u'привет+ромашки'

    def test_serialize_to_json__message(self):
        descriptor = TestMessage.DESCRIPTOR
        msg = TestMessage(string0='hello', bool0=False, short0=256)
        result = self.protocol._serialize_to_json(descriptor, msg)

        assert result == '{"string0": "hello", "bool0": false, "short0": 256}'

    # InvocationResult parsing.

    def test_parse_invocation_result__ok(self):
        msg = TestMessage(string0='hello', bool0=False, short0=127)

        result_class = self.protocol._result_class(TestMessage.DESCRIPTOR)
        result = result_class(ok=True, data=msg)
        content = result.to_json()

        response = RestResponse(content=content, content_type=RestResponse.JSON_CONTENT_TYPE)
        inv_result = self.protocol.parse_invocation_result(response, TestMessage.DESCRIPTOR)

        assert inv_result.ok
        assert inv_result.data == msg
        assert inv_result.exc is None

    def test_parse_parse_result__exc(self):
        exc = TestException(text='Application exception!')

        result_class = self.protocol._result_class(descriptors.string0, TestException.DESCRIPTOR)
        result = result_class(ok=False, exc=exc)
        content = result.to_json()

        response = RestResponse(content=content, content_type=RestResponse.JSON_CONTENT_TYPE)
        inv_result = self.protocol.parse_invocation_result(response, descriptors.string0,
                                                           TestException.DESCRIPTOR)

        assert inv_result.ok is False
        assert inv_result.data is None
        assert inv_result.exc == exc

    # Invocation parsing.

    def test_parse_invocation__index_method(self):
        request = RestRequest(path='/', query={'arg0': '123', 'arg1': '456'})

        invocation = self.protocol.parse_invocation(request, TestInterface.DESCRIPTOR)
        assert invocation.method.name == 'testIndex'
        assert invocation.args == {'arg0': 123, 'arg1': 456}

    def test_parse_invocation__post_method(self):
        request = RestRequest('POST', path='/testPost', post={'arg0': '1', 'arg1': '2'},)

        invocation = self.protocol.parse_invocation(request, TestInterface.DESCRIPTOR)
        assert invocation.method.name == 'testPost'
        assert invocation.args == {'arg0': 1, 'arg1': 2}

    def test_parse_invocation__post_method_not_allowed(self):
        request = RestRequest(path='/testPost', post={})
        try:
            self.protocol.parse_invocation(request, TestInterface.DESCRIPTOR)
            self.fail()
        except RestException as e:
            assert e.status == httplib.METHOD_NOT_ALLOWED

    def test_parse_invocation__remote_method(self):
        request = RestRequest(path='/testRemote', query={'arg0': '1', 'arg1': '2'})

        invocation = self.protocol.parse_invocation(request, TestInterface.DESCRIPTOR)
        assert invocation.method.name == 'testRemote'
        assert invocation.args == {'arg0': 1, 'arg1': 2}

    def test_parse_invocation__chained_method_index(self):
        request = RestRequest(path='/testInterface/1/2/', query={'arg0': '3'})

        chain = self.protocol.parse_invocation(request, TestInterface.DESCRIPTOR).to_chain()
        invocation0 = chain[0]
        invocation1 = chain[1]

        assert len(chain) == 2
        assert invocation0.method.name == 'testInterface'
        assert invocation0.args == {'arg0': 1, 'arg1': 2}
        assert invocation1.method.name == 'testIndex'
        assert invocation1.args == {'arg0': 3, 'arg1': None}

    def test_parse_invocation__chained_method_remote(self):
        request = RestRequest(path='/testInterface/1/2/testString', query={'text': u'привет'})

        chain = self.protocol.parse_invocation(request, TestInterface.DESCRIPTOR).to_chain()
        invocation0 = chain[0]
        invocation1 = chain[1]

        assert len(chain) == 2
        assert invocation0.method.name == 'testInterface'
        assert invocation0.args == {'arg0': 1, 'arg1': 2}
        assert invocation1.method.name == 'testString'
        assert invocation1.args == {'text': u'привет'}

    def test_parse_invocation__interface_method_not_remote(self):
        request = RestRequest(path='/testInterface/1/2')

        try:
            self.protocol.parse_invocation(request, TestInterface.DESCRIPTOR)
            self.fail()
        except RestException as e:
            assert e.status == httplib.NOT_FOUND

    # Arguments parsing.

    def test_parse_path_argument(self):
        arg = descriptors.arg('arg', descriptors.string0)
        part = '%D0%9F%D1%80%D0%B8%D0%B2%D0%B5%D1%82'

        value = self.protocol._parse_path_argument(arg, part)
        assert value == u'Привет'

    def test_parse_param__form(self):
        arg = descriptors.arg('arg', TestForm.DESCRIPTOR)

        expected = TestForm(formString=u'Привет', formList=[1, 2, 3], formBool=True)
        src = {'formString': u'Привет', 'formList': '[1,2,3]', 'formBool': 'true'}

        result = self.protocol._parse_param(arg, src)
        assert result == expected

    def test_parse_param__primitive(self):
        arg = descriptors.arg('arg', lambda: descriptors.int32)
        src = {'arg': '123'}

        value = self.protocol._parse_param(arg, src)
        assert value == 123

    def test_parse_from_json(self):
        descriptor = descriptors.int32

        value = self.protocol._parse_from_json(descriptor, '123')
        assert value == 123

    def test_parse_from_json__null(self):
        descriptor = descriptors.int32

        value = self.protocol._parse_from_json(descriptor, 'null')
        assert value is None

    def test_parse_from_json__string(self):
        descriptor = descriptors.string0

        value = self.protocol._parse_from_json(descriptor, u'привет, мир!')
        assert value == u'привет, мир!'

    def test_parse_from_json__message(self):
        descriptor = TestMessage.DESCRIPTOR

        msg = TestMessage(string0=u'привет', bool0=True, short0=123)
        value = msg.to_json()

        msg0 = self.protocol._parse_from_json(descriptor, value)
        assert msg0 == msg

    # InvocationResult serialization.

    def test_serialize_invocation_result(self):
        msg = TestMessage(string0=u'привет', bool0=False, short0=0)
        inv_result = pdef.invoke.InvocationResult.from_data(msg)
        response = self.protocol.serialize_invocation_result(inv_result, TestMessage.DESCRIPTOR)

        result_class = self.protocol._result_class(TestMessage.DESCRIPTOR)
        content = result_class(ok=True, data=msg).to_json(indent=True)

        assert response.status == httplib.OK
        assert response.content_type == RestResponse.JSON_CONTENT_TYPE
        assert response.content == content

    def test_serialize_invocation_result_exc(self):
        exc = TestException(u'Привет, мир')
        inv_result = pdef.invoke.InvocationResult.from_exc(exc)
        response = self.protocol.serialize_invocation_result(inv_result, descriptors.string0,
                                                             TestException.DESCRIPTOR)

        result_class = self.protocol._result_class(descriptors.string0, TestException.DESCRIPTOR)
        content = result_class(ok=False, exc=exc).to_json(indent=True)

        assert response.status == httplib.OK
        assert response.content_type == RestResponse.JSON_CONTENT_TYPE
        assert response.content == content


class TestRestClient(unittest.TestCase):
    def test_error_response(self):
        response = RestResponse(status=500, content='Internal server error')
        client = RestClient(None)
        exc = client._rest_error(response)

        assert isinstance(exc, RestException)
        assert exc.status == 500
        assert exc.message == 'Internal server error'


class TestRestServer(unittest.TestCase):
    def setUp(self):
        invoker = lambda inv: pdef.invoke.InvocationResult.from_data(inv)
        self.server = RestServer(TestInterface.DESCRIPTOR, invoker)

    def get_request(self, path, query=None, post=None):
        return RestRequest.get(path, query=query, post=post)

    def post_request(self, path, query=None, post=None):
        return RestRequest.post(path, query=query, post=post)

    def test_handle(self):
        request = RestRequest.get(path='/', query={'a': '1', 'b': '2'})
        server = RestServer(TestInterface.DESCRIPTOR,
                            lambda invocation: pdef.invoke.InvocationResult.from_data(3))
        response = server.handle(request)

        assert response.status == httplib.OK
        assert response.content_type == RestResponse.JSON_CONTENT_TYPE
        assert json.loads(response.content) == {'ok': True, 'data': 3}

    def test_handle__unhandled_exception(self):
        def invoker(inv):
            raise ValueError('Internal server error')

        request = RestRequest.get(path='/', query={'a': '1', 'b': '2'})
        server = RestServer(TestInterface.DESCRIPTOR, invoker)

        try:
            server.handle(request)
            self.fail()
        except ValueError as e:
            assert e.message == 'Internal server error'

    def test_error_response(self):
        e = RestException(u'Метод не найден', httplib.NOT_FOUND)
        resp = self.server._error_response(e)

        assert resp.status == 404
        assert resp.content == e.message


class TestWsgiRestServer(unittest.TestCase):
    def env(self):
        return {
            'REQUEST_METHOD': 'GET',
            'CONTENT_TYPE': 'application/x-www-form-urlencoded',
            'CONTENT_LENGTH': 0,
            'SCRIPT_NAME': '/myapp',
            'PATH_INFO': '/method0/method1'
        }

    def test_handle(self):
        hello = u'Привет, мир'
        response = RestResponse(status=200, content=hello, content_type='text/plain')
        start_response = Mock()

        server = WsgiRestServer(lambda x: response)
        content = ''.join(server.handle(self.env(), start_response))

        assert content.decode('utf-8') == hello
        start_response.assert_called_with('200 OK',
            [('Content-Type', 'text/plain'), ('Content-Length', '%s' % len(content))])

    def test_parse_invocation(self):
        query = urllib.quote(u'привет=мир'.encode('utf-8'), '=')
        body = urllib.quote(u'пока=мир'.encode('utf-8'), '=')
        env = {
            'REQUEST_METHOD': 'POST',
            'CONTENT_TYPE': 'application/x-www-form-urlencoded',
            'CONTENT_LENGTH': len(body),
            'SCRIPT_NAME': '/myapp',
            'PATH_INFO': '/method0/method1',
            'QUERY_STRING': query,
            'wsgi.input': StringIO(body),
        }

        server = WsgiRestServer(None)
        request = server._parse_request(env)

        assert request.method == 'POST'
        assert request.path == '/method0/method1'
        assert request.query == {u'привет': u'мир'}
        assert request.post == {u'пока': u'мир'}


class TestIntegration(unittest.TestCase):
    def setUp(self):
        from wsgiref.simple_server import make_server
        service = IntegrationService()
        app = rest_wsgi_server(TestInterface, service)

        self.server = make_server('localhost', 0, app)
        self.server_thread = Thread(target=self.server.serve_forever)
        self.server_thread.start()

        import logging
        FORMAT = '%(name)s %(levelname)s - %(message)s'
        logging.basicConfig(level=logging.DEBUG, format=FORMAT)

    def tearDown(self):
        self.server.shutdown()

    def client(self):
        url = 'http://localhost:%s/' % self.server.server_port
        return rest_client(TestInterface, url)

    def test(self):
        client = self.client()
        msg = TestMessage(u'Привет', True, 0)
        form = TestForm(formBool=True, formString=u'Привет', formList=[1, 2, 3])

        assert client.testIndex(1, 2) == 3
        assert client.testRemote(1, 2) == 3
        assert client.testPost(1, 2) == 3
        assert client.testMessage(msg) == msg
        assert client.testForm(form) == form
        assert client.testVoid() is None
        assert client.testString(u'Как дела?') == u'Как дела?'
        assert client.testInterface(1, 2).testIndex(3, 4) == 7
        self.assertRaises(TestException, client.testExc)


class IntegrationService(TestInterface):
    def testIndex(self, arg0=None, arg1=None):
        return arg0 + arg1

    def testRemote(self, arg0=None, arg1=None):
        return arg0 + arg1

    def testPost(self, arg0=None, arg1=None):
        return arg0 + arg1

    def testString(self, text=None):
        return text

    def testMessage(self, msg=None):
        return msg

    def testForm(self, form=None):
        return form

    def testPolymorphic(self, msg=None):
        return msg

    def testCollections(self, list0=None, set0=None, map0=None):
        return len(list0) + len(set0) + len(map0)

    def testVoid(self):
        return

    def testExc(self):
        raise TestException('Test exception')

    def testInterface(self, arg0=None, arg1=None):
        return self
