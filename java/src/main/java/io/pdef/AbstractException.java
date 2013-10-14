package io.pdef;

import io.pdef.descriptors.FieldDescriptor;
import io.pdef.descriptors.MessageDescriptor;
import io.pdef.format.JsonFormat;
import io.pdef.format.NativeFormat;

import java.io.Serializable;
import java.util.Map;

/**
 * Abstract class for a generated Pdef exception.
 * */
public abstract class AbstractException extends RuntimeException implements Message, Serializable {
	protected AbstractException() {}

	@SuppressWarnings("unchecked")
	private MessageDescriptor<Message> thisDescriptor() {
		return (MessageDescriptor<Message>) descriptor();
	}

	@Override
	public Message copy() {
		return thisDescriptor().copy(this);
	}

	@SuppressWarnings("unchecked")
	@Override
	public Map<String, Object> serializeToMap() {
		return (Map<String, Object>) NativeFormat.instance().serialize(this, thisDescriptor());
	}

	@Override
	public String serializeToJson() {
		return serializeToJson(true);
	}

	@Override
	public String serializeToJson(final boolean indent) {
		return JsonFormat.instance().serialize(this, thisDescriptor(), indent);
	}

	@Override
	public String toString() {
		StringBuilder sb = new StringBuilder(getClass().getSimpleName());
		sb.append('{');

		String nextSeparator = "";
		MessageDescriptor<Message> descriptor = thisDescriptor();
		for (FieldDescriptor<? super Message, ?> field : descriptor.getFields()) {
			Object value = field.get(this);
			if (value == null) {
				continue;
			}

			sb.append(nextSeparator);
			sb.append(field.getName()).append('=').append(value);
			nextSeparator = ", ";
		}

		sb.append('}');
		return sb.toString();
	}

	@Override
	public boolean equals(final Object o) {
		if (this == o) return true;
		if (o == null || getClass() != o.getClass()) return false;

		AbstractException cast = (AbstractException) o;
		MessageDescriptor<Message> descriptor = thisDescriptor();
		for (FieldDescriptor<? super Message, ?> field : descriptor.getFields()) {
			Object value0 = field.get(this);
			Object value1 = field.get(cast);
			if (value0 != null ? !value0.equals(value1) : value1 != null) {
				return false;
			}
		}

		return true;
	}

	@Override
	public int hashCode() {
		int result = 0;

		MessageDescriptor<Message> descriptor = thisDescriptor();
		for (FieldDescriptor<? super Message, ?> field : descriptor.getFields()) {
			Object value = field.get(this);
			result = 31 * result + (value == null ? 0 : value.hashCode());
		}

		return result;
	}
}