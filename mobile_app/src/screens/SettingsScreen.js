import React, { useState, useEffect } from 'react';
import {
  View,
  ScrollView,
  StyleSheet,
  Alert,
} from 'react-native';
import {
  Card,
  Title,
  Paragraph,
  List,
  Switch,
  Button,
  TextInput,
  Divider,
  Avatar,
  Surface,
  Chip,
} from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialIcons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import Toast from 'react-native-toast-message';

import ApiService from '../services/ApiService';
import { AuthService } from '../services/AuthService';
import NotificationService from '../services/NotificationService';

const SettingsScreen = ({ navigation }) => {
  const [userInfo, setUserInfo] = useState(null);
  const [serverUrl, setServerUrl] = useState('');
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [vibrationEnabled, setVibrationEnabled] = useState(true);
  const [darkMode, setDarkMode] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState('30');
  const [debugMode, setDebugMode] = useState(false);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      // Load user info
      const user = await AuthService.getUserInfo();
      setUserInfo(user);

      // Load server URL
      const url = await ApiService.getServerUrl();
      setServerUrl(url);

      // Load notification settings
      const notifEnabled = await AsyncStorage.getItem('notifications_enabled');
      setNotificationsEnabled(notifEnabled !== 'false');

      const soundEn = await AsyncStorage.getItem('sound_enabled');
      setSoundEnabled(soundEn !== 'false');

      const vibrationEn = await AsyncStorage.getItem('vibration_enabled');
      setVibrationEnabled(vibrationEn !== 'false');

      // Load app settings
      const darkModeEnabled = await AsyncStorage.getItem('dark_mode');
      setDarkMode(darkModeEnabled === 'true');

      const autoRefreshEnabled = await AsyncStorage.getItem('auto_refresh');
      setAutoRefresh(autoRefreshEnabled !== 'false');

      const interval = await AsyncStorage.getItem('refresh_interval');
      setRefreshInterval(interval || '30');

      const debug = await AsyncStorage.getItem('debug_mode');
      setDebugMode(debug === 'true');

    } catch (error) {
      console.error('Error loading settings:', error);
    }
  };

  const saveServerUrl = async () => {
    try {
      await ApiService.setServerUrl(serverUrl);
      
      // Test connection
      await ApiService.ping();
      
      Toast.show({
        type: 'success',
        text1: 'Server Updated',
        text2: 'Connection successful'
      });
    } catch (error) {
      Toast.show({
        type: 'error',
        text1: 'Connection Failed',
        text2: error.message
      });
    }
  };

  const toggleNotifications = async (enabled) => {
    setNotificationsEnabled(enabled);
    await AsyncStorage.setItem('notifications_enabled', enabled.toString());
    
    if (enabled) {
      await NotificationService.initialize();
    }
  };

  const toggleSound = async (enabled) => {
    setSoundEnabled(enabled);
    await AsyncStorage.setItem('sound_enabled', enabled.toString());
  };

  const toggleVibration = async (enabled) => {
    setVibrationEnabled(enabled);
    await AsyncStorage.setItem('vibration_enabled', enabled.toString());
  };

  const toggleDarkMode = async (enabled) => {
    setDarkMode(enabled);
    await AsyncStorage.setItem('dark_mode', enabled.toString());
    
    Toast.show({
      type: 'info',
      text1: 'Theme Changed',
      text2: 'Restart app to apply changes'
    });
  };

  const toggleAutoRefresh = async (enabled) => {
    setAutoRefresh(enabled);
    await AsyncStorage.setItem('auto_refresh', enabled.toString());
  };

  const saveRefreshInterval = async () => {
    await AsyncStorage.setItem('refresh_interval', refreshInterval);
    Toast.show({
      type: 'success',
      text1: 'Interval Updated',
      text2: `Refresh every ${refreshInterval} seconds`
    });
  };

  const toggleDebugMode = async (enabled) => {
    setDebugMode(enabled);
    await AsyncStorage.setItem('debug_mode', enabled.toString());
  };

  const handleLogout = () => {
    Alert.alert(
      'Logout',
      'Are you sure you want to logout?',
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Logout', style: 'destructive', onPress: performLogout }
      ]
    );
  };

  const performLogout = async () => {
    try {
      await AuthService.logout();
      await ApiService.logout();
      
      // Navigate to login screen
      navigation.reset({
        index: 0,
        routes: [{ name: 'Login' }],
      });
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  const clearCache = async () => {
    Alert.alert(
      'Clear Cache',
      'This will clear all cached data. Continue?',
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Clear', style: 'destructive', onPress: performClearCache }
      ]
    );
  };

  const performClearCache = async () => {
    try {
      // Clear specific cache keys (keep auth and settings)
      const keysToKeep = [
        'auth_token',
        'user_info',
        'server_url',
        'notifications_enabled',
        'sound_enabled',
        'vibration_enabled',
        'dark_mode',
        'auto_refresh',
        'refresh_interval',
        'debug_mode'
      ];
      
      const allKeys = await AsyncStorage.getAllKeys();
      const keysToRemove = allKeys.filter(key => !keysToKeep.includes(key));
      
      await AsyncStorage.multiRemove(keysToRemove);
      
      Toast.show({
        type: 'success',
        text1: 'Cache Cleared',
        text2: 'Application cache has been cleared'
      });
    } catch (error) {
      Toast.show({
        type: 'error',
        text1: 'Clear Failed',
        text2: error.message
      });
    }
  };

  const exportLogs = async () => {
    // This would export debug logs in a real implementation
    Toast.show({
      type: 'info',
      text1: 'Export Logs',
      text2: 'Feature coming soon'
    });
  };

  return (
    <ScrollView style={styles.container}>
      {/* User Profile */}
      <Card style={styles.card}>
        <Card.Content>
          <View style={styles.profileHeader}>
            <Avatar.Icon size={64} icon="account" />
            <View style={styles.profileInfo}>
              <Title>{userInfo?.username || 'Unknown User'}</Title>
              <Paragraph>{userInfo?.email || 'No email'}</Paragraph>
              <Chip
                mode="outlined"
                style={styles.roleChip}
              >
                {userInfo?.is_admin ? 'Administrator' : 'User'}
              </Chip>
            </View>
          </View>
        </Card.Content>
      </Card>

      {/* Server Configuration */}
      <Card style={styles.card}>
        <Card.Content>
          <Title style={styles.sectionTitle}>Server Configuration</Title>
          
          <TextInput
            label="Server URL"
            value={serverUrl}
            onChangeText={setServerUrl}
            mode="outlined"
            style={styles.input}
            left={<TextInput.Icon name="server" />}
            placeholder="http://192.168.1.100:5000"
          />
          
          <Button
            mode="contained"
            onPress={saveServerUrl}
            style={styles.saveButton}
          >
            Test & Save Connection
          </Button>
        </Card.Content>
      </Card>

      {/* Notification Settings */}
      <Card style={styles.card}>
        <Card.Content>
          <Title style={styles.sectionTitle}>Notifications</Title>
          
          <List.Item
            title="Push Notifications"
            description="Receive alerts for job completion and system events"
            left={(props) => <List.Icon {...props} icon="bell" />}
            right={() => (
              <Switch
                value={notificationsEnabled}
                onValueChange={toggleNotifications}
              />
            )}
          />
          
          <Divider />
          
          <List.Item
            title="Sound"
            description="Play sound for notifications"
            left={(props) => <List.Icon {...props} icon="volume-high" />}
            right={() => (
              <Switch
                value={soundEnabled}
                onValueChange={toggleSound}
                disabled={!notificationsEnabled}
              />
            )}
          />
          
          <Divider />
          
          <List.Item
            title="Vibration"
            description="Vibrate for notifications"
            left={(props) => <List.Icon {...props} icon="vibrate" />}
            right={() => (
              <Switch
                value={vibrationEnabled}
                onValueChange={toggleVibration}
                disabled={!notificationsEnabled}
              />
            )}
          />
        </Card.Content>
      </Card>

      {/* App Settings */}
      <Card style={styles.card}>
        <Card.Content>
          <Title style={styles.sectionTitle}>App Settings</Title>
          
          <List.Item
            title="Dark Mode"
            description="Use dark theme (restart required)"
            left={(props) => <List.Icon {...props} icon="theme-light-dark" />}
            right={() => (
              <Switch
                value={darkMode}
                onValueChange={toggleDarkMode}
              />
            )}
          />
          
          <Divider />
          
          <List.Item
            title="Auto Refresh"
            description="Automatically refresh data"
            left={(props) => <List.Icon {...props} icon="refresh" />}
            right={() => (
              <Switch
                value={autoRefresh}
                onValueChange={toggleAutoRefresh}
              />
            )}
          />
          
          {autoRefresh && (
            <>
              <Divider />
              <View style={styles.intervalContainer}>
                <TextInput
                  label="Refresh Interval (seconds)"
                  value={refreshInterval}
                  onChangeText={setRefreshInterval}
                  mode="outlined"
                  keyboardType="numeric"
                  style={styles.intervalInput}
                />
                <Button
                  mode="outlined"
                  onPress={saveRefreshInterval}
                  compact
                  style={styles.intervalButton}
                >
                  Save
                </Button>
              </View>
            </>
          )}
        </Card.Content>
      </Card>

      {/* Developer Settings */}
      <Card style={styles.card}>
        <Card.Content>
          <Title style={styles.sectionTitle}>Developer</Title>
          
          <List.Item
            title="Debug Mode"
            description="Enable detailed logging"
            left={(props) => <List.Icon {...props} icon="bug" />}
            right={() => (
              <Switch
                value={debugMode}
                onValueChange={toggleDebugMode}
              />
            )}
          />
          
          <Divider />
          
          <List.Item
            title="Export Logs"
            description="Export application logs"
            left={(props) => <List.Icon {...props} icon="file-export" />}
            onPress={exportLogs}
          />
          
          <Divider />
          
          <List.Item
            title="Clear Cache"
            description="Clear application cache"
            left={(props) => <List.Icon {...props} icon="delete" />}
            onPress={clearCache}
          />
        </Card.Content>
      </Card>

      {/* About */}
      <Card style={styles.card}>
        <Card.Content>
          <Title style={styles.sectionTitle}>About</Title>
          
          <View style={styles.aboutInfo}>
            <Paragraph style={styles.aboutItem}>
              <Title style={styles.aboutLabel}>Version:</Title> 1.0.0
            </Paragraph>
            <Paragraph style={styles.aboutItem}>
              <Title style={styles.aboutLabel}>Build:</Title> {new Date().getFullYear()}.08.13
            </Paragraph>
            <Paragraph style={styles.aboutItem}>
              <Title style={styles.aboutLabel}>Platform:</Title> React Native
            </Paragraph>
          </View>
        </Card.Content>
      </Card>

      {/* Logout */}
      <Card style={[styles.card, styles.logoutCard]}>
        <Card.Content>
          <Button
            mode="contained"
            onPress={handleLogout}
            style={styles.logoutButton}
            buttonColor="#f44336"
            textColor="#ffffff"
            icon="logout"
          >
            Logout
          </Button>
        </Card.Content>
      </Card>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  card: {
    margin: 16,
    marginBottom: 8,
  },
  profileHeader: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  profileInfo: {
    marginLeft: 16,
    flex: 1,
  },
  roleChip: {
    alignSelf: 'flex-start',
    marginTop: 8,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 16,
  },
  input: {
    marginBottom: 16,
  },
  saveButton: {
    alignSelf: 'flex-start',
  },
  intervalContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  intervalInput: {
    flex: 1,
    marginRight: 12,
  },
  intervalButton: {
    alignSelf: 'flex-end',
  },
  aboutInfo: {
    marginTop: 8,
  },
  aboutItem: {
    marginBottom: 8,
  },
  aboutLabel: {
    fontSize: 14,
    fontWeight: 'bold',
  },
  logoutCard: {
    marginBottom: 32,
  },
  logoutButton: {
    alignSelf: 'stretch',
  },
});

export default SettingsScreen;