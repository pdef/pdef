package io.pdef;

import io.pdef.test.UserEvent;
import org.junit.Test;

import static org.junit.Assert.assertNotNull;

public class PdefTest {

	@Test
	public void testMessage() throws Exception {
		Pdef.MessageInfo info = (Pdef.MessageInfo) Pdef.info(UserEvent.class);
		assertNotNull(info);
	}
}