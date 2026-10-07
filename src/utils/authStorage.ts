import AsyncStorage from '@react-native-async-storage/async-storage';

const KEY_AUTH_TOKEN = '@auth_token';
const KEY_USER_ID = '@auth_user_id';
const KEY_USER_NAME = '@auth_user_name';

/**
 * Saves the authentication token and user metadata to persistent storage.
 */
export async function saveAuthSession(token: string, userId: number, userName: string): Promise<void> {
  try {
    console.log('[AuthStorage] Saving session:', token, userId, userName);
    await AsyncStorage.setItem(KEY_AUTH_TOKEN, token);
    await AsyncStorage.setItem(KEY_USER_ID, userId.toString());
    await AsyncStorage.setItem(KEY_USER_NAME, userName);
    console.log('[AuthStorage] Session saved successfully.');
  } catch (error) {
    console.error('[AuthStorage] Error saving auth session:', error);
  }
}

/**
 * Retrieves the stored session API key/token.
 */
export async function getAuthToken(): Promise<string | null> {
  try {
    const token = await AsyncStorage.getItem(KEY_AUTH_TOKEN);
    console.log('[AuthStorage] Retrieved token:', token);
    return token;
  } catch (error) {
    console.error('[AuthStorage] Error getting auth token:', error);
    return null;
  }
}

/**
 * Retrieves the stored user metadata.
 */
export async function getAuthUser(): Promise<{ id: number; name: string } | null> {
  try {
    const idStr = await AsyncStorage.getItem(KEY_USER_ID);
    const name = await AsyncStorage.getItem(KEY_USER_NAME);
    console.log('[AuthStorage] Retrieved user:', idStr, name);
    if (idStr && name) {
      return { id: parseInt(idStr, 10), name };
    }
    return null;
  } catch (error) {
    console.error('[AuthStorage] Error getting auth user:', error);
    return null;
  }
}

/**
 * Clears the session credentials from storage.
 */
export async function clearAuthSession(): Promise<void> {
  try {
    console.log('[AuthStorage] Clearing session storage...');
    await AsyncStorage.removeItem(KEY_AUTH_TOKEN);
    await AsyncStorage.removeItem(KEY_USER_ID);
    await AsyncStorage.removeItem(KEY_USER_NAME);
    console.log('[AuthStorage] Session storage cleared.');
  } catch (error) {
    console.error('[AuthStorage] Error clearing auth session:', error);
  }
}
