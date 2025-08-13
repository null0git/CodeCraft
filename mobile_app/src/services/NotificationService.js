import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';
import { Platform } from 'react-native';

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

class NotificationService {
  constructor() {
    this.expoPushToken = null;
  }

  async initialize() {
    if (Device.isDevice) {
      const { status: existingStatus } = await Notifications.getPermissionsAsync();
      let finalStatus = existingStatus;
      
      if (existingStatus !== 'granted') {
        const { status } = await Notifications.requestPermissionsAsync();
        finalStatus = status;
      }
      
      if (finalStatus !== 'granted') {
        console.log('Failed to get push token for push notification!');
        return;
      }
      
      try {
        this.expoPushToken = (await Notifications.getExpoPushTokenAsync()).data;
        console.log('Expo push token:', this.expoPushToken);
      } catch (error) {
        console.error('Error getting push token:', error);
      }
    } else {
      console.log('Must use physical device for Push Notifications');
    }

    if (Platform.OS === 'android') {
      Notifications.setNotificationChannelAsync('default', {
        name: 'default',
        importance: Notifications.AndroidImportance.MAX,
        vibrationPattern: [0, 250, 250, 250],
        lightColor: '#FF231F7C',
      });
    }
  }

  async scheduleNotification(title, body, data = {}, trigger = null) {
    try {
      const id = await Notifications.scheduleNotificationAsync({
        content: {
          title,
          body,
          data,
          sound: 'default',
        },
        trigger: trigger || null,
      });
      return id;
    } catch (error) {
      console.error('Error scheduling notification:', error);
      throw error;
    }
  }

  async showJobCompleteNotification(jobName, passwordsFound) {
    return this.scheduleNotification(
      'Job Completed',
      `${jobName} finished. ${passwordsFound} passwords found.`,
      { type: 'job_complete', jobName, passwordsFound }
    );
  }

  async showPasswordFoundNotification(jobName, password) {
    return this.scheduleNotification(
      'Password Found!',
      `Job "${jobName}" found password: ${password}`,
      { type: 'password_found', jobName, password }
    );
  }

  async showClusterFailoverNotification(oldLeader, newLeader) {
    return this.scheduleNotification(
      'Cluster Failover',
      `Leader changed from ${oldLeader} to ${newLeader}`,
      { type: 'failover', oldLeader, newLeader }
    );
  }

  async showNodeFailureNotification(nodeName) {
    return this.scheduleNotification(
      'Node Failure',
      `Node ${nodeName} has become unresponsive`,
      { type: 'node_failure', nodeName }
    );
  }

  async cancelAllNotifications() {
    try {
      await Notifications.cancelAllScheduledNotificationsAsync();
    } catch (error) {
      console.error('Error canceling notifications:', error);
    }
  }

  async getBadgeCount() {
    try {
      return await Notifications.getBadgeCountAsync();
    } catch (error) {
      console.error('Error getting badge count:', error);
      return 0;
    }
  }

  async setBadgeCount(count) {
    try {
      await Notifications.setBadgeCountAsync(count);
    } catch (error) {
      console.error('Error setting badge count:', error);
    }
  }

  getExpoPushToken() {
    return this.expoPushToken;
  }

  // Listen for notification responses
  addNotificationResponseListener(listener) {
    return Notifications.addNotificationResponseReceivedListener(listener);
  }

  // Listen for foreground notifications
  addNotificationReceivedListener(listener) {
    return Notifications.addNotificationReceivedListener(listener);
  }
}

export { NotificationService };
export default new NotificationService();