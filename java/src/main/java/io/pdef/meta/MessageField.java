package io.pdef.meta;

import com.google.common.base.Objects;
import static com.google.common.base.Preconditions.*;
import com.google.common.base.Supplier;
import com.google.common.base.Suppliers;

/**
 * MessageField holds a field name, type, setters and getters.
 * @param <M> Message class.
 * @param <V> Field value class.
 */
public class MessageField<M, V> {
	private final String name;
	private final Supplier<DataType<V>> type;
	private final MessageFieldGetter<M, V> getter;
	private final MessageFieldSetter<M, V> setter;
	private final boolean discriminator;

	protected MessageField(final Builder<M, V> builder) {
		name = checkNotNull(builder.name);
		type = checkNotNull(builder.type);
		getter = checkNotNull(builder.getter);
		setter = checkNotNull(builder.setter);
		discriminator = builder.discriminator;
	}

	public static <M, V> Builder<M, V> builder() {
		return new Builder<M, V>();
	}

	@Override
	public String toString() {
		return Objects.toStringHelper(this)
				.addValue(name)
				.toString();
	}

	public String getName() {
		return name;
	}

	public boolean isDiscriminator() {
		return discriminator;
	}

	public DataType<V> getType() {
		return type.get();
	}

	public V get(final M message) {
		return getter.get(message);
	}

	public void set(final M message, final V value) {
		setter.set(message, value);
	}

	public void copy(final M src, final M dst) {
		V value = get(src);
		V copied = getType().copy(value);
		set(dst, copied);
	}

	public static class Builder<M, V> {
		private String name;
		private boolean discriminator;
		private Supplier<DataType<V>> type;
		private MessageFieldGetter<M, V> getter;
		private MessageFieldSetter<M, V> setter;

		protected Builder() {}

		public Builder<M, V> setName(final String name) {
			this.name = name;
			return this;
		}

		public Builder<M, V> setDiscriminator(final boolean discriminator) {
			this.discriminator = discriminator;
			return this;
		}

		public Builder<M, V> setType(final Supplier<DataType<V>> type) {
			this.type = type;
			return this;
		}

		public Builder<M, V> setType(final DataType<V> type) {
			checkNotNull(type);
			this.type = Suppliers.ofInstance(type);
			return this;
		}

		public Builder<M, V> setGetter(final MessageFieldGetter<M, V> getter) {
			this.getter = getter;
			return this;
		}

		public Builder<M, V> setSetter(final MessageFieldSetter<M, V> setter) {
			this.setter = setter;
			return this;
		}

		public Builder<M, V> setAccessor(final MessageFieldAccessor<M, V> accessor) {
			setGetter(accessor);
			setSetter(accessor);
			return this;
		}

		public MessageField<M, V> build() {
			return new MessageField<M, V>(this);
		}
	}
}
