import React, { useEffect, useState } from 'react';
import { StatusBar } from 'expo-status-bar';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createStackNavigator } from '@react-navigation/stack';
import { Provider as PaperProvider } from 'react-native-paper';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import Toast from 'react-native-toast-message';
import Icon from 'react-native-vector-icons/MaterialIcons';

// Screens
import DashboardScreen from './src/screens/DashboardScreen';
import ClusterScreen from './src/screens/ClusterScreen';
import NodesScreen from './src/screens/NodesScreen';
import JobsScreen from './src/screens/JobsScreen';
import SettingsScreen from './src/screens/SettingsScreen';
import LoginScreen from './src/screens/LoginScreen';
import NodeDetailScreen from './src/screens/NodeDetailScreen';
import JobDetailScreen from './src/screens/JobDetailScreen';

// Services
import { AuthService } from './src/services/AuthService';
import { NotificationService } from './src/services/NotificationService';

// Theme
import { theme } from './src/theme/theme';

const Tab = createBottomTabNavigator();
const Stack = createStackNavigator();

function MainTabNavigator() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: ({ focused, color, size }) => {
          let iconName;

          if (route.name === 'Dashboard') {
            iconName = 'dashboard';
          } else if (route.name === 'Cluster') {
            iconName = 'device-hub';
          } else if (route.name === 'Nodes') {
            iconName = 'computer';
          } else if (route.name === 'Jobs') {
            iconName = 'work';
          } else if (route.name === 'Settings') {
            iconName = 'settings';
          }

          return <Icon name={iconName} size={size} color={color} />;
        },
        tabBarActiveTintColor: theme.colors.primary,
        tabBarInactiveTintColor: 'gray',
        headerStyle: {
          backgroundColor: theme.colors.primary,
        },
        headerTintColor: '#fff',
        headerTitleStyle: {
          fontWeight: 'bold',
        },
      })}
    >
      <Tab.Screen 
        name="Dashboard" 
        component={DashboardScreen}
        options={{ title: 'CrackPi Dashboard' }}
      />
      <Tab.Screen 
        name="Cluster" 
        component={ClusterScreen}
        options={{ title: 'Cluster Status' }}
      />
      <Tab.Screen 
        name="Nodes" 
        component={NodesScreen}
        options={{ title: 'Cluster Nodes' }}
      />
      <Tab.Screen 
        name="Jobs" 
        component={JobsScreen}
        options={{ title: 'Cracking Jobs' }}
      />
      <Tab.Screen 
        name="Settings" 
        component={SettingsScreen}
        options={{ title: 'Settings' }}
      />
    </Tab.Navigator>
  );
}

function AppNavigator() {
  return (
    <Stack.Navigator>
      <Stack.Screen 
        name="Main" 
        component={MainTabNavigator}
        options={{ headerShown: false }}
      />
      <Stack.Screen 
        name="NodeDetail" 
        component={NodeDetailScreen}
        options={{ title: 'Node Details' }}
      />
      <Stack.Screen 
        name="JobDetail" 
        component={JobDetailScreen}
        options={{ title: 'Job Details' }}
      />
    </Stack.Navigator>
  );
}

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    checkAuthStatus();
    initializeNotifications();
  }, []);

  const checkAuthStatus = async () => {
    try {
      const token = await AuthService.getToken();
      setIsAuthenticated(!!token);
    } catch (error) {
      console.error('Auth check failed:', error);
      setIsAuthenticated(false);
    } finally {
      setIsLoading(false);
    }
  };

  const initializeNotifications = async () => {
    try {
      await NotificationService.initialize();
    } catch (error) {
      console.error('Notification initialization failed:', error);
    }
  };

  const handleLogin = () => {
    setIsAuthenticated(true);
  };

  if (isLoading) {
    return null; // Or a loading screen
  }

  return (
    <SafeAreaProvider>
      <PaperProvider theme={theme}>
        <NavigationContainer>
          {isAuthenticated ? (
            <AppNavigator />
          ) : (
            <LoginScreen onLogin={handleLogin} />
          )}
        </NavigationContainer>
        <StatusBar style="light" />
        <Toast />
      </PaperProvider>
    </SafeAreaProvider>
  );
}