package pdef;

import com.google.common.base.Objects;
import static com.google.common.base.Preconditions.*;
import com.google.common.collect.ImmutableMap;

import java.util.Map;

public class ImmutableMessageTree implements MessageTree {
	private final EnumType type;
	private final FieldDescriptor field;
	private final ImmutableMap<EnumType, MessageDescriptor> map;

	public static Builder builder() {
		return new Builder();
	}

	private ImmutableMessageTree(final EnumType type, final FieldDescriptor field,
			final ImmutableMap<EnumType, MessageDescriptor> map) {
		this.type = checkNotNull(type);
		this.field = checkNotNull(field);
		this.map = checkNotNull(map);
	}

	@Override
	public String toString() {
		return Objects.toStringHelper(this)
				.addValue(type)
				.addValue(field)
				.addValue(map)
				.toString();
	}

	@Override
	public EnumType getType() {
		return type;
	}

	@Override
	public FieldDescriptor getField() {
		return field;
	}

	@Override
	public ImmutableMap<EnumType, MessageDescriptor> getMap() {
		return map;
	}

	@Override
	public MessageTree.Builder subtreeBuilder(final EnumType subtype) {
		return builder().setField(field).setType(subtype);

	}

	public static class Builder implements MessageTree.Builder {
		private EnumType type;
		private FieldDescriptor field;
		private ImmutableMap.Builder<EnumType, MessageDescriptor> map;

		private Builder() {
			map = ImmutableMap.builder();
		}

		@Override
		public Builder setType(final EnumType type) {
			checkState(this.type == null, "type is already set to %s", this.type);
			this.type = type;
			return this;
		}

		@Override
		public Builder setField(final FieldDescriptor field) {
			checkState(this.field == null, "field is already set to %s", this.field);
			this.field = field;
			return this;
		}

		@Override
		public Builder put(final EnumType enumType, final MessageDescriptor message) {
			map.put(enumType, message);
			return this;
		}

		@Override
		public Builder putAll(final Map<? extends EnumType, ? extends MessageDescriptor> map) {
			this.map.putAll(map);
			return this;
		}

		public ImmutableMessageTree build() {
			return new ImmutableMessageTree(type, field, map.build());
		}
	}
}
