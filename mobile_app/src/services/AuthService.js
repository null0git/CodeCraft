import AsyncStorage from '@react-native-async-storage/async-storage';

class AuthService {
  async setToken(token) {
    try {
      await AsyncStorage.setItem('auth_token', token);
    } catch (error) {
      console.error('Error storing auth token:', error);
      throw error;
    }
  }

  async getToken() {
    try {
      return await AsyncStorage.getItem('auth_token');
    } catch (error) {
      console.error('Error retrieving auth token:', error);
      return null;
    }
  }

  async removeToken() {
    try {
      await AsyncStorage.removeItem('auth_token');
    } catch (error) {
      console.error('Error removing auth token:', error);
    }
  }

  async setUserInfo(userInfo) {
    try {
      await AsyncStorage.setItem('user_info', JSON.stringify(userInfo));
    } catch (error) {
      console.error('Error storing user info:', error);
      throw error;
    }
  }

  async getUserInfo() {
    try {
      const userInfo = await AsyncStorage.getItem('user_info');
      return userInfo ? JSON.parse(userInfo) : null;
    } catch (error) {
      console.error('Error retrieving user info:', error);
      return null;
    }
  }

  async isAuthenticated() {
    const token = await this.getToken();
    return !!token;
  }

  async logout() {
    try {
      await this.removeToken();
      await AsyncStorage.removeItem('user_info');
    } catch (error) {
      console.error('Error during logout:', error);
    }
  }
}

export { AuthService };
export default new AuthService();