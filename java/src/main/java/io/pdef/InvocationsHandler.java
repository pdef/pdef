package io.pdef;

import java.util.List;

public interface InvocationsHandler {

	Object handle(List<Pdef.Invocation> invocations);
}
