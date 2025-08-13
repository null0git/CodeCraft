import React, { useState } from 'react';
import {
  View,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  Image,
} from 'react-native';
import {
  Card,
  Title,
  TextInput,
  Button,
  Paragraph,
  Snackbar,
  ActivityIndicator,
} from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialIcons';

import ApiService from '../services/ApiService';
import { AuthService } from '../services/AuthService';

const LoginScreen = ({ onLogin }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [serverUrl, setServerUrl] = useState('http://localhost:5000');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [showServerConfig, setShowServerConfig] = useState(false);

  const handleLogin = async () => {
    if (!username.trim() || !password.trim()) {
      setError('Please enter username and password');
      return;
    }

    setLoading(true);
    setError('');

    try {
      // Set server URL first
      await ApiService.setServerUrl(serverUrl);
      
      // Test connection
      await ApiService.ping();
      
      // Attempt login
      const response = await ApiService.login(username, password);
      
      if (response.success) {
        await AuthService.setToken(response.token);
        await AuthService.setUserInfo(response.user);
        onLogin();
      } else {
        setError(response.message || 'Login failed');
      }
    } catch (error) {
      setError(error.message || 'Connection failed');
    } finally {
      setLoading(false);
    }
  };

  const testConnection = async () => {
    setLoading(true);
    try {
      await ApiService.setServerUrl(serverUrl);
      await ApiService.ping();
      setError('');
      setShowServerConfig(false);
    } catch (error) {
      setError('Cannot connect to server: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView contentContainerStyle={styles.scrollContainer}>
        <View style={styles.content}>
          {/* Logo */}
          <View style={styles.logoContainer}>
            <Icon name="security" size={80} color="#6200ee" />
            <Title style={styles.title}>CrackPi Mobile</Title>
            <Paragraph style={styles.subtitle}>
              Remote Monitoring & Management
            </Paragraph>
          </View>

          {/* Login Form */}
          <Card style={styles.loginCard}>
            <Card.Content>
              <View style={styles.formContainer}>
                <TextInput
                  label="Username"
                  value={username}
                  onChangeText={setUsername}
                  mode="outlined"
                  autoCapitalize="none"
                  style={styles.input}
                  left={<TextInput.Icon name="account" />}
                />

                <TextInput
                  label="Password"
                  value={password}
                  onChangeText={setPassword}
                  mode="outlined"
                  secureTextEntry={!showPassword}
                  style={styles.input}
                  left={<TextInput.Icon name="lock" />}
                  right={
                    <TextInput.Icon
                      name={showPassword ? 'eye-off' : 'eye'}
                      onPress={() => setShowPassword(!showPassword)}
                    />
                  }
                />

                {showServerConfig && (
                  <View style={styles.serverConfig}>
                    <TextInput
                      label="Server URL"
                      value={serverUrl}
                      onChangeText={setServerUrl}
                      mode="outlined"
                      autoCapitalize="none"
                      autoCorrect={false}
                      style={styles.input}
                      left={<TextInput.Icon name="server" />}
                      placeholder="http://192.168.1.100:5000"
                    />
                    <Button
                      mode="outlined"
                      onPress={testConnection}
                      loading={loading}
                      style={styles.testButton}
                    >
                      Test Connection
                    </Button>
                  </View>
                )}

                <Button
                  mode="text"
                  onPress={() => setShowServerConfig(!showServerConfig)}
                  style={styles.configButton}
                >
                  {showServerConfig ? 'Hide' : 'Configure'} Server Settings
                </Button>

                <Button
                  mode="contained"
                  onPress={handleLogin}
                  loading={loading}
                  disabled={loading}
                  style={styles.loginButton}
                  contentStyle={styles.loginButtonContent}
                >
                  {loading ? 'Connecting...' : 'Sign In'}
                </Button>
              </View>
            </Card.Content>
          </Card>

          {/* Quick Setup */}
          <Card style={styles.helpCard}>
            <Card.Content>
              <Title style={styles.helpTitle}>Quick Setup</Title>
              <Paragraph style={styles.helpText}>
                1. Ensure your CrackPi server is running
              </Paragraph>
              <Paragraph style={styles.helpText}>
                2. Use default credentials: admin / admin123
              </Paragraph>
              <Paragraph style={styles.helpText}>
                3. Configure server URL if not on localhost
              </Paragraph>
            </Card.Content>
          </Card>
        </View>

        <Snackbar
          visible={!!error}
          onDismiss={() => setError('')}
          duration={4000}
          style={styles.snackbar}
        >
          {error}
        </Snackbar>
      </ScrollView>
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  scrollContainer: {
    flexGrow: 1,
    justifyContent: 'center',
    paddingHorizontal: 20,
  },
  content: {
    flex: 1,
    justifyContent: 'center',
  },
  logoContainer: {
    alignItems: 'center',
    marginBottom: 40,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    marginTop: 16,
    textAlign: 'center',
  },
  subtitle: {
    fontSize: 16,
    textAlign: 'center',
    opacity: 0.7,
    marginTop: 8,
  },
  loginCard: {
    marginBottom: 20,
  },
  formContainer: {
    padding: 10,
  },
  input: {
    marginBottom: 16,
  },
  serverConfig: {
    marginBottom: 16,
  },
  testButton: {
    marginTop: 8,
  },
  configButton: {
    marginBottom: 20,
  },
  loginButton: {
    marginTop: 10,
  },
  loginButtonContent: {
    paddingVertical: 8,
  },
  helpCard: {
    backgroundColor: '#e3f2fd',
  },
  helpTitle: {
    fontSize: 18,
    marginBottom: 12,
  },
  helpText: {
    fontSize: 14,
    marginBottom: 4,
    opacity: 0.8,
  },
  snackbar: {
    backgroundColor: '#f44336',
  },
});

export default LoginScreen;