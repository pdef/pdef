package pdef;

import com.google.common.base.Objects;
import static com.google.common.base.Preconditions.*;
import com.google.common.collect.Lists;
import pdef.descriptors.Descriptor;
import pdef.descriptors.MessageDescriptor;
import pdef.descriptors.MethodDescriptor;

import javax.annotation.Nullable;
import java.util.Arrays;
import java.util.List;

public class Invocation {
	private final MethodDescriptor method;
	private final Invocation parent;
	private final Object[] args;

	public static Invocation root() {
		return new Invocation(null, null, null);
	}

	private Invocation(final MethodDescriptor method, final Invocation parent,
			final Object[] args) {
		this.method = method;
		this.parent = parent;
		this.args = args == null ? new Object[0] : args.clone();

		checkArgument(this.args.length == method.getArgs().size(), "Wrong number of args");
	}

	@Override
	public String toString() {
		return Objects.toStringHelper(this)
				.addValue(method)
				.add("args", Arrays.toString(args))
				.toString();
	}

	public boolean isRoot() {
		return method == null;
	}

	public Object[] getArgs() {
		return args;
	}

	public MethodDescriptor getMethod() {
		return method;
	}

	public Descriptor getResult() {
		return method == null ? null : method.getResult();
	}

	/** Returns true when the method result is not an interface. */
	public boolean isRemote() {
		return method.isRemote();
	}

	/** Returns the method exception or the parent exception. */
	@Nullable
	public MessageDescriptor getExc() {
		if (method != null) return method.getExc();
		if (parent != null) return parent.getExc();
		return null;
	}

	/** Creates a child invocation. */
	public Invocation next(final MethodDescriptor method, final Object[] args) {
		return new Invocation(method, this, args);
	}

	/** Returns a list of invocation. */
	public List<Invocation> toChain() {
		List<Invocation> chain = parent != null ? parent.toChain() : Lists.<Invocation>newArrayList();
		if (!isRoot()) chain.add(this);

		return chain;
	}

	/** Invokes this invocation chain on an object. */
	public Object invoke(Object object) {
		checkNotNull(object);

		List<Invocation> chain = toChain();
		for (Invocation invocation : chain) {
			object = invocation.invokeSingle(object);
		}

		return object;
	}

	/** Invokes only this invocation (not a chain) on an object. */
	public Object invokeSingle(final Object object) {
		return method.invoke(object, args);
	}
}