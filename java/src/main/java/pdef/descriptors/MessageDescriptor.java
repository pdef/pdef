package pdef.descriptors;

import static com.google.common.base.Preconditions.*;
import com.google.common.base.Supplier;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.Lists;
import com.google.common.collect.Maps;
import pdef.Message;
import pdef.TypeEnum;

import java.util.List;
import java.util.Map;

public class MessageDescriptor extends DataDescriptor {
	private final MessageDescriptor base;
	private final Enum<?> baseType;
	private final Supplier<? extends Message.Builder> builderSupplier;
	private final List<FieldDescriptor> declaredFields;
	private final List<FieldDescriptor> fields;
	private final FieldDescriptor discriminator;
	private final Map<Enum<?>, Supplier<MessageDescriptor>> subtypes;

	public static Builder builder() {
		return new Builder();
	}

	private MessageDescriptor(final Builder builder) {
		super(TypeEnum.MESSAGE);
		base = builder.base;
		baseType = builder.baseType;
		builderSupplier = checkNotNull(builder.builder);

		declaredFields = buildDeclaredFields(builder.declaredFields, this);
		fields = buildFields(declaredFields, base);
		subtypes = ImmutableMap.copyOf(builder.subtypes);
		discriminator = getDiscriminator(fields);
	}

	public MessageDescriptor getBase() {
		return base;
	}

	public Enum<?> getBaseType() {
		return baseType;
	}

	public List<FieldDescriptor> getDeclaredFields() {
		return declaredFields;
	}

	public List<FieldDescriptor> getInheritedFields() {
		return base != null ? base.getFields() : ImmutableList.<FieldDescriptor>of();
	}

	public Map<Enum<?>, Supplier<MessageDescriptor>> getSubtypes() {
		return subtypes;
	}

	public List<FieldDescriptor> getFields() {
		return fields;
	}

	public FieldDescriptor getDiscriminator() {
		return discriminator;
	}

	public Message.Builder createBuilder() {
		return builderSupplier.get();
	}

	public Message.Builder toBuilder(final Message message) {
		if (message == null) return null;
		return createBuilder().merge(message);
	}

	@Override
	public Map<String, Object> toObject(final Object object) {
		if (object == null) return null;
		Message message = (Message) object;

		Map<String, Object> map = Maps.newLinkedHashMap();
		for (FieldDescriptor field : fields) {
			Object value = field.get(message);
			Object serialized = field.getType().toObject(value);
			if (serialized == null) {
				continue;
			}

			map.put(field.getName(), serialized);
		}

		return map;
	}

	@Override
	public Message parseObject(final Object object) {
		if (object == null) return null;
		Map<?, ?> map = (Map<?, ?>) object;

		if (discriminator != null) {
			Object value = map.get(discriminator.getName());
			Object subtype = discriminator.getType().parseObject(value);
			Supplier<MessageDescriptor> supplier = subtypes.get(subtype);
			MessageDescriptor subtypeDescriptor = supplier == null ? null : supplier.get();
			if (subtypeDescriptor != null && subtypeDescriptor != this) {
				return subtypeDescriptor.parseObject(object);
			}
		}

		Message.Builder builder = createBuilder();
		for (FieldDescriptor field : getFields()) {
			Object value = map.get(field.getName());
			Object parsed = field.getType().parseObject(value);
			if (parsed == null) {
				continue;
			}

			field.set(builder, parsed);
		}

		return builder.build();
	}

	public static class Builder {
		private MessageDescriptor base;
		private Enum<?> baseType;
		private Supplier<? extends Message.Builder> builder;
		private final List<FieldDescriptor.Builder> declaredFields;
		private final Map<Enum<?>, Supplier<MessageDescriptor>> subtypes;

		private Builder() {
			declaredFields = Lists.newArrayList();
			subtypes = Maps.newLinkedHashMap();
		}

		public Builder setBase(final MessageDescriptor base) {
			this.base = base;
			return this;
		}

		public Builder setBaseType(final Enum<?> baseType) {
			this.baseType = baseType;
			return this;
		}

		public Builder setBuilder(final Supplier<? extends Message.Builder> builder) {
			this.builder = builder;
			return this;
		}

		public Builder addField(final FieldDescriptor.Builder field) {
			declaredFields.add(field);
			return this;
		}

		public Builder addSubtype(final Enum<?> type, final Supplier<MessageDescriptor> subtype) {
			subtypes.put(type, subtype);
			return this;
		}

		public MessageDescriptor build() {
			return new MessageDescriptor(this);
		}
	}

	private static ImmutableList<FieldDescriptor> buildDeclaredFields(
			final Iterable<FieldDescriptor.Builder> fields, final MessageDescriptor message) {
		ImmutableList.Builder<FieldDescriptor> temp = ImmutableList.builder();
		for (FieldDescriptor.Builder fb : fields) {
			FieldDescriptor field = fb.build(message);
			temp.add(field);
		}
		return temp.build();
	}

	private static ImmutableList<FieldDescriptor> buildFields(
			final Iterable<FieldDescriptor> declaredFields, final MessageDescriptor base) {
		return ImmutableList.<FieldDescriptor>builder()
				.addAll(base == null ? ImmutableList.<FieldDescriptor>of() : base.getFields())
				.addAll(declaredFields)
				.build();
	}

	private static FieldDescriptor getDiscriminator(final Iterable<FieldDescriptor> fields) {
		for (FieldDescriptor field : fields) {
			if (field.isDiscriminator()) {
				return field;
			}
		}
		return null;
	}
}