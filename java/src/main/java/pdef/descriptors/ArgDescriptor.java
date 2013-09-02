package pdef.descriptors;

import com.google.common.base.Supplier;

import static com.google.common.base.Preconditions.checkNotNull;

public class ArgDescriptor {
	private final String name;
	private final Supplier<DataDescriptor> type;
	private final MethodDescriptor method;

	private ArgDescriptor(final Builder builder, final MethodDescriptor method) {
		this.method = checkNotNull(method);
		name = checkNotNull(builder.name);
		type = checkNotNull(builder.type);
	}

	public String getName() {
		return name;
	}

	public DataDescriptor getType() {
		return type.get();
	}

	public MethodDescriptor getMethod() {
		return method;
	}

	public static Builder builder() {
		return new Builder();
	}

	public static class Builder {
		private String name;
		private Supplier<DataDescriptor> type;

		private Builder() {}

		public Builder setName(final String name) {
			this.name = name;
			return this;
		}

		public Builder setType(final Supplier<DataDescriptor> type) {
			this.type = type;
			return this;
		}

		public ArgDescriptor build(final MethodDescriptor method) {
			return new ArgDescriptor(this, method);
		}
	}
}
