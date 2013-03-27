package pdef.formats;

import org.junit.Test;
import pdef.fixtures.Profile;
import pdef.fixtures.Sex;
import pdef.fixtures.User;

public class StringSerializerTest {
	@Test
	public void testSerialize() throws Exception {
		Profile profile = Profile.builder()
				.setAvatar(123L)
				.setComplete(true)
				.setWallpaper(7L)
				.setFirstName("John")
				.setLastName("Doe")
				.build();

		User user = User.builder()
				.setName("John Doe")
				.setSex(Sex.MALE)
				.setProfile(profile)
				.build();

		StringSerializer serializer = new StringSerializer();
		String s = (String) serializer.serialize(user);
		System.out.println(s);
	}
}
