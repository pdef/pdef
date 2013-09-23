package pdef;

import com.google.common.base.Function;
import org.apache.http.client.fluent.Request;
import org.apache.http.client.fluent.Response;
import pdef.descriptors.InterfaceDescriptor;
import pdef.invocation.Invocation;
import pdef.invocation.InvocationProxy;
import pdef.invocation.InvocationResult;
import pdef.rest.RestClientHandler;
import pdef.rest.RestClientSender;
import pdef.rest.RestRequest;
import pdef.rest.RestResponse;

import javax.annotation.Nullable;

import static com.google.common.base.Preconditions.checkArgument;
import static com.google.common.base.Preconditions.checkNotNull;

/** Pdef client constructors. */
public class Clients {
	private Clients() {}

	/** Creates a default REST client. */
	public static <T> T client(final Class<T> cls, final String url) {
		checkNotNull(cls);
		checkNotNull(url);

		return client(cls, url, null);
	}

	/** Creates a default REST client with a custom session. */
	public static <T> T client(final Class<T> cls, final String url,
			@Nullable final Function<Request, Response> session) {
		checkNotNull(cls);
		checkNotNull(url);

		RestClientSender sender = sender(url, session);
		RestClientHandler handler = handler(sender);
		return client(cls, handler);
	}

	/** Creates a custom client. */
	public static <T> T client(final Class<T> cls,
			final Function<Invocation, InvocationResult> invocationHandler) {
		checkNotNull(cls);
		checkNotNull(invocationHandler);

		InterfaceDescriptor descriptor = InterfaceDescriptor.findDescriptor(cls);
		checkArgument(descriptor != null, "Cannot find an interface descriptor in " + cls);

		return InvocationProxy.create(cls, descriptor, invocationHandler);
	}

	/** Creates a REST client invocation handler with a custom sender. */
	public static RestClientHandler handler(final Function<RestRequest, RestResponse> sender) {
		checkNotNull(sender);
		return new RestClientHandler(sender);
	}

	/** Creates a REST client sender. */
	public static RestClientSender sender(final String url) {
		checkNotNull(url);
		return sender(url, null);
	}

	/** Creates a REST client sender with a custom session or a default one. */
	public static RestClientSender sender(final String url,
			@Nullable final Function<Request, Response> session) {
		checkNotNull(url);
		return new RestClientSender(url, session);
	}
}