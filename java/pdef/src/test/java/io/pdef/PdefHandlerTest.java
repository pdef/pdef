package io.pdef;

import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.ImmutableSet;
import io.pdef.test.TestInterface;
import io.pdef.test.TestNumber;
import io.pdef.test.TestStruct;
import io.pdef.test.TestSubInterface;
import org.hamcrest.Matcher;
import static org.hamcrest.MatcherAssert.assertThat;
import static org.hamcrest.core.IsEqual.equalTo;
import org.junit.Test;
import static org.mockito.Mockito.*;

import java.lang.reflect.Method;
import java.util.Date;
import java.util.Map;

public class PdefHandlerTest {
	@Test
	public void testHandle() throws Exception {
		TestInterface iface = mock(TestInterface.class);
		TestSubInterface subface = mock(TestSubInterface.class);
		PdefHandler<TestInterface> server = new PdefHandler<TestInterface>(
				TestInterface.class, iface);
		when(iface.interface0(true, -32, "привет")).thenReturn(subface);

		PdefRequest request = new PdefRequest()
				.setRelativePath("/interface0/true/-32/%D0%BF%D1%80%D0%B8%D0%B2%D0%B5%D1%82/get")
				.setQuery(ImmutableMap.of("int0", "0", "string0", "привет"));
		server.handle(request);
		verify(subface).get(0, "привет");
	}

	@Test
	public void testParseInvocation() throws Exception {
		PdefRequest request = new PdefRequest()
				.setRelativePath("/interface0/false/-32/hello/get")
				.setQuery(ImmutableMap.of("int0", "-1", "string0", "hello"));
		PdefInvocation invocation = PdefHandler.parseRequest(request, TestInterface.class);

		assertThat(invocation.getMethod(), equalToMethod(TestSubInterface.class, "get"));
		assertThat(invocation.getArgs(), equalTo(new Object[]{-1, "hello"}));

		PdefInvocation parent = invocation.getParent();
		assertThat(parent.getMethod(), equalToMethod(TestInterface.class, "interface0"));
		assertThat(parent.getArgs(), equalTo(new Object[]{false, -32, "hello"}));
	}

	@Test
	public void testParseInvocation_request() throws Exception {
		Map<String, String> query = ImmutableMap.<String, String>builder()
				.put("bool0", "1")
				.put("short0", "-16")
				.put("int0", "-32")
				.put("long0", "-64")
				.put("float0", "-1.5")
				.put("double0", "-2.5")
				.put("string0", "привет")
				.put("datetime0", "1970-01-01T00:00:01Z")
				.put("list0", "[1, 2, 3]")
				.put("set0", "[4, 5, 6]")
				.put("map0", "{\"1\": \"a\"}")
				.put("enum0", "one")
				.put("struct0", "{\"int0\": 32}")
				.build();

		PdefRequest request = new PdefRequest()
				.setRelativePath("/request")
				.setQuery(query);

		PdefInvocation invocation = PdefHandler.parseRequest(request, TestInterface.class);
		TestStruct struct = (TestStruct) invocation.getArgs()[0];
		TestStruct expected = new TestStruct()
				.setBool0(true)
				.setShort0((short) -16)
				.setInt0(-32)
				.setLong0(-64)
				.setFloat0(-1.5f)
				.setDouble0(-2.5)
				.setString0("привет")
				.setDatetime0(new Date(1000))
				.setList0(ImmutableList.of(1, 2, 3))
				.setSet0(ImmutableSet.of(4, 5, 6))
				.setMap0(ImmutableMap.of(1, "a"))
				.setEnum0(TestNumber.ONE)
				.setStruct0(new TestStruct().setInt0(32));

		assertThat(struct, equalTo(expected));
	}

	@Test
	public void testParseInvocation_post() throws Exception {
		PdefRequest request = new PdefRequest()
				.setMethod("POST")
				.setRelativePath("/post")
				.setPost(ImmutableMap.of("bool0", "1", "short0", "-16", "int0", "-32"));

		PdefInvocation invocation = PdefHandler.parseRequest(request, TestInterface.class);
		Object[] args = new Object[13];
		args[0] = true;
		args[1] = (short) -16;
		args[2] = -32;

		assertThat(invocation.getMethod(), equalToMethod(TestInterface.class, "post"));
		assertThat(invocation.getArgs(), equalTo(args));
	}

	public static Matcher<Method> equalToMethod(final Class<?> cls, final String name) {
		Method method = PdefHandler.getMethod(cls, name);
		assert method != null;
		return equalTo(method);
	}
}