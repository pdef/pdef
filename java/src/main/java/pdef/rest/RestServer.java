package pdef.rest;

import com.google.common.annotations.VisibleForTesting;
import com.google.common.base.Supplier;
import com.google.common.collect.Lists;
import com.google.common.collect.Maps;
import pdef.Invocation;
import pdef.TypeEnum;
import pdef.descriptors.*;
import pdef.rpc.*;

import java.io.UnsupportedEncodingException;
import java.net.URLDecoder;
import java.util.Collections;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;

import static com.google.common.base.Preconditions.checkNotNull;

public class RestServer {
	public static final String CHARSET = "UTF-8";
	private final InterfaceDescriptor descriptor;
	private final Supplier<Object> serviceSupplier;

	public RestServer(final InterfaceDescriptor descriptor, final Supplier<Object> serviceSupplier) {
		this.descriptor = descriptor;
		this.serviceSupplier = serviceSupplier;
	}

	public RestResponse handle(final RestRequest request) {
		checkNotNull(request);

		try {
			RpcResponse response;
			Invocation invocation = parseRequest(request);
			try {
				Object result = invoke(invocation);
				response = resultToResponse(result, invocation);
			} catch (Exception e) {
				response = handleException(e, invocation);

				if (response == null) {
					return errorRestResponse(e);
				}
			}

			return restResponse(response);
		} catch (Exception e) {
			return errorRestResponse(e);
		}
	}

	private Invocation parseRequest(final RestRequest request) throws Exception {
		checkNotNull(request);
		String path = request.getPath();
		Map<String, String> query = request.getQuery();
		Map<String, String> post = request.getPost();

		if (path.startsWith("/")) {
			path = path.substring(1);
		}
		LinkedList<String> parts = Lists.newLinkedList();
		Collections.addAll(parts, path.split("//"));

		Invocation invocation = Invocation.root();
		InterfaceDescriptor descriptor = this.descriptor;
		while (!parts.isEmpty()) {
			String part = parts.removeFirst();

			// Find a method by name or get an index method.
			if (descriptor == null) {
				throw MethodNotFoundError.builder()
						.setText("Method not found")
						.build();
			}

			MethodDescriptor method = descriptor.findMethod(part);
			if (method == null) method = descriptor.getIndexMethod();
			if (method == null) {
				throw MethodNotFoundError.builder()
						.setText("Method not found")
						.build();
			}

			// If an index method, prepend the part back,
			// because index methods do not have names.
			if (method.isIndex() && !part.equals("")) {
				parts.addFirst(part);
			}

			// Parse method arguments.
			List<Object> args = Lists.newArrayList();
			if (method.isPost()) {
				// Parse arguments from the post body.
				if (!request.isPost()) {
					throw MethodNotAllowedError.builder()
							.setText("Method not allowed, POST required")
							.build();
				}

				for (ArgDescriptor argd : method.getArgs()) {
					args.add(parseQueryArg(argd, post));
				}

			} else if (method.isRemote()) {
				// Parse arguments from the query string.
				for (ArgDescriptor argd : method.getArgs()) {
					args.add(parseQueryArg(argd, query));
				}

			} else {
				// Parse arguments as positional params.
				for (ArgDescriptor argd : method.getArgs()) {
					if (parts.isEmpty()) {
						throw WrongMethodArgsError.builder()
								.setText("Wrong number of method args")
								.build();
					}

					args.add(parsePositionalArg(argd, parts.removeFirst()));
				}
			}

			invocation = invocation.next(method, args.toArray());
			descriptor = method.isRemote() ? null : (InterfaceDescriptor) method.getResult();
		}

		if (!invocation.isRemote()) {
			throw MethodNotFoundError.builder()
					.setText("Method not found")
					.build();
		}

		return invocation;
	}

	private Object parsePositionalArg(final ArgDescriptor argd, final String s)
			throws UnsupportedEncodingException {
		String value = URLDecoder.decode(s, CHARSET);
		return parseArgFromString(argd.getType(), value);
	}

	private Object parseQueryArg(final ArgDescriptor argd, final Map<String, String> src) {
		DataDescriptor d = argd.getType();
		MessageDescriptor md = d.asMessageDescriptor();
		boolean isForm = md != null && md.isForm();

		if (!isForm) {
			// Parse as a string argument.
			String value = src.get(argd.getName());
			if (value == null) {
				return null;
			}

			return parseArgFromString(d, value);
		}

		// Parse as expanded form fields.
		Map<String, Object> fields = Maps.newHashMap();
		for (FieldDescriptor fd : md.getFields()) {
			String fvalue = src.get(fd.getName());
			if (fvalue == null) {
				continue;
			}

			fields.put(fd.getName(), parseArgFromString(fd.getType(), fvalue));
		}

		return md.parseObject(fields);
	}

	private Object parseArgFromString(final DataDescriptor descriptor, final String value) {
		TypeEnum type = descriptor.getType();

		if (value == null) {
			return null;
		}

		if (value.equals("")) {
			return type == TypeEnum.STRING ? "" : null;
		}

		if (type.isPrimitive()) {
			return ((PrimitiveDescriptor) descriptor).parseString(value);
		}

		return descriptor.parseJson(value);
	}

	@VisibleForTesting
	Object invoke(final Invocation invocation) {
		Object service = serviceSupplier.get();
		return invocation.invoke(service);
	}

	@VisibleForTesting
	RpcResponse resultToResponse(final Object result, final Invocation invocation) {
		DataDescriptor dd = (DataDescriptor) invocation.getResult();
		Object serialized = dd.toObject(result);

		return RpcResponse.builder()
				.setStatus(RpcStatus.OK)
				.setResult(serialized)
				.build();
	}

	@VisibleForTesting
	RpcResponse handleException(final Exception e, final Invocation invocation) {
		MessageDescriptor excd = invocation.getExc();
		if (excd == null || !excd.getJavaClass().isInstance(e)) {
			return null;
		}

		Object serialized = excd.toObject(e);
		return RpcResponse.builder()
				.setStatus(RpcStatus.EXCEPTION)
				.setResult(serialized)
				.build();
	}

	@VisibleForTesting
	RestResponse restResponse(final RpcResponse response) {
		int httpStatus = 200;
		String json = response.toJson();

		return new RestResponse(httpStatus, json, "application/json; charset=utf-8");
	}

	@VisibleForTesting
	RestResponse errorRestResponse(final Exception e) {
		int httpStatus;
		String result;

		if (e instanceof WrongMethodArgsError) {
			httpStatus = 400;
		} else if (e instanceof MethodNotFoundError) {
			httpStatus = 404;
		} else if (e instanceof MethodNotAllowedError) {
			httpStatus = 405;
		} else if (e instanceof ClientError) {
			httpStatus = 400;
		} else if (e instanceof ServiceUnavailableError) {
			httpStatus = 503;
		} else if (e instanceof ServerError) {
			httpStatus = 500;
		} else {
			httpStatus = 500;
		}

		if (e instanceof RpcError) {
			result = ((RpcError) e).getText();
		} else {
			result = "Internal server error";
		}

		return new RestResponse(httpStatus, result, "text/plain; charset=utf-8");
	}
}