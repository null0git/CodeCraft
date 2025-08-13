import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  ScrollView,
  RefreshControl,
  StyleSheet,
  Dimensions,
} from 'react-native';
import {
  Card,
  Title,
  Paragraph,
  Surface,
  Button,
  Chip,
  ProgressBar,
  ActivityIndicator,
} from 'react-native-paper';
import { LineChart, PieChart } from 'react-native-chart-kit';
import Icon from 'react-native-vector-icons/MaterialIcons';
import Toast from 'react-native-toast-message';

import ApiService from '../services/ApiService';
import { formatBytes, formatDuration, getStatusColor } from '../utils/helpers';

const screenWidth = Dimensions.get('window').width;

const DashboardScreen = ({ navigation }) => {
  const [dashboardData, setDashboardData] = useState(null);
  const [clusterMetrics, setClusterMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadDashboardData = useCallback(async () => {
    try {
      const [dashboard, metrics] = await Promise.all([
        ApiService.getDashboardData(),
        ApiService.getClusterMetrics()
      ]);
      
      setDashboardData(dashboard);
      setClusterMetrics(metrics);
    } catch (error) {
      Toast.show({
        type: 'error',
        text1: 'Failed to load dashboard',
        text2: error.message
      });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    loadDashboardData();
  }, [loadDashboardData]);

  useEffect(() => {
    loadDashboardData();
    
    // Auto-refresh every 30 seconds
    const interval = setInterval(loadDashboardData, 30000);
    return () => clearInterval(interval);
  }, [loadDashboardData]);

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" />
        <Paragraph style={styles.loadingText}>Loading dashboard...</Paragraph>
      </View>
    );
  }

  const chartConfig = {
    backgroundColor: '#ffffff',
    backgroundGradientFrom: '#ffffff',
    backgroundGradientTo: '#ffffff',
    decimalPlaces: 1,
    color: (opacity = 1) => `rgba(0, 122, 255, ${opacity})`,
    labelColor: (opacity = 1) => `rgba(0, 0, 0, ${opacity})`,
    style: {
      borderRadius: 16,
    },
  };

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }
    >
      {/* System Status Cards */}
      <View style={styles.statusCards}>
        <Card style={styles.statusCard}>
          <Card.Content>
            <View style={styles.statusContent}>
              <Icon name="device-hub" size={24} color="#4CAF50" />
              <View style={styles.statusText}>
                <Title style={styles.statusValue}>
                  {dashboardData?.cluster_status?.total_nodes || 0}
                </Title>
                <Paragraph>Active Nodes</Paragraph>
              </View>
            </View>
          </Card.Content>
        </Card>

        <Card style={styles.statusCard}>
          <Card.Content>
            <View style={styles.statusContent}>
              <Icon name="work" size={24} color="#2196F3" />
              <View style={styles.statusText}>
                <Title style={styles.statusValue}>
                  {dashboardData?.active_jobs || 0}
                </Title>
                <Paragraph>Active Jobs</Paragraph>
              </View>
            </View>
          </Card.Content>
        </Card>

        <Card style={styles.statusCard}>
          <Card.Content>
            <View style={styles.statusContent}>
              <Icon name="lock-open" size={24} color="#FF9800" />
              <View style={styles.statusText}>
                <Title style={styles.statusValue}>
                  {dashboardData?.total_cracked || 0}
                </Title>
                <Paragraph>Passwords Cracked</Paragraph>
              </View>
            </View>
          </Card.Content>
        </Card>
      </View>

      {/* Cluster Health */}
      <Card style={styles.card}>
        <Card.Content>
          <Title>Cluster Health</Title>
          {clusterMetrics && (
            <View style={styles.healthContainer}>
              <View style={styles.healthMetric}>
                <Paragraph>CPU Usage</Paragraph>
                <ProgressBar
                  progress={clusterMetrics.cluster_averages.cpu_usage / 100}
                  color="#FF9800"
                  style={styles.progressBar}
                />
                <Paragraph>{clusterMetrics.cluster_averages.cpu_usage.toFixed(1)}%</Paragraph>
              </View>
              
              <View style={styles.healthMetric}>
                <Paragraph>Memory Usage</Paragraph>
                <ProgressBar
                  progress={clusterMetrics.cluster_averages.memory_usage / 100}
                  color="#2196F3"
                  style={styles.progressBar}
                />
                <Paragraph>{clusterMetrics.cluster_averages.memory_usage.toFixed(1)}%</Paragraph>
              </View>
              
              <View style={styles.healthMetric}>
                <Paragraph>Disk Usage</Paragraph>
                <ProgressBar
                  progress={clusterMetrics.cluster_averages.disk_usage / 100}
                  color="#4CAF50"
                  style={styles.progressBar}
                />
                <Paragraph>{clusterMetrics.cluster_averages.disk_usage.toFixed(1)}%</Paragraph>
              </View>
            </View>
          )}
        </Card.Content>
      </Card>

      {/* Performance Chart */}
      {clusterMetrics && (
        <Card style={styles.card}>
          <Card.Content>
            <Title>Cluster Performance</Title>
            <LineChart
              data={{
                labels: ['5m ago', '4m ago', '3m ago', '2m ago', '1m ago', 'Now'],
                datasets: [
                  {
                    data: [
                      0, 0, 0, 0, 0,
                      clusterMetrics.cluster_averages.cpu_usage
                    ],
                    color: (opacity = 1) => `rgba(255, 152, 0, ${opacity})`,
                    strokeWidth: 2,
                  },
                  {
                    data: [
                      0, 0, 0, 0, 0,
                      clusterMetrics.cluster_averages.memory_usage
                    ],
                    color: (opacity = 1) => `rgba(33, 150, 243, ${opacity})`,
                    strokeWidth: 2,
                  },
                ],
                legend: ['CPU %', 'Memory %'],
              }}
              width={screenWidth - 60}
              height={220}
              chartConfig={chartConfig}
              style={styles.chart}
            />
          </Card.Content>
        </Card>
      )}

      {/* Recent Jobs */}
      <Card style={styles.card}>
        <Card.Content>
          <View style={styles.cardHeader}>
            <Title>Recent Jobs</Title>
            <Button
              mode="text"
              onPress={() => navigation.navigate('Jobs')}
            >
              View All
            </Button>
          </View>
          
          {dashboardData?.recent_jobs?.length > 0 ? (
            dashboardData.recent_jobs.slice(0, 3).map((job, index) => (
              <Surface key={index} style={styles.jobItem}>
                <View style={styles.jobHeader}>
                  <Paragraph style={styles.jobName}>{job.name}</Paragraph>
                  <Chip
                    mode="outlined"
                    style={[styles.statusChip, { backgroundColor: getStatusColor(job.status) }]}
                  >
                    {job.status}
                  </Chip>
                </View>
                <ProgressBar
                  progress={job.progress_percent / 100}
                  color="#4CAF50"
                  style={styles.progressBar}
                />
                <Paragraph style={styles.jobProgress}>
                  {job.progress_percent.toFixed(1)}% - {job.cracked_hashes}/{job.total_hashes} cracked
                </Paragraph>
              </Surface>
            ))
          ) : (
            <Paragraph>No recent jobs</Paragraph>
          )}
        </Card.Content>
      </Card>

      {/* Node Distribution */}
      {clusterMetrics && Object.keys(clusterMetrics.node_metrics).length > 0 && (
        <Card style={styles.card}>
          <Card.Content>
            <Title>Node Distribution</Title>
            <PieChart
              data={Object.entries(clusterMetrics.node_metrics).map(([nodeId, node], index) => ({
                name: node.hostname || nodeId.slice(0, 8),
                load: node.load_metrics?.cpu_usage || 0,
                color: `hsl(${index * 60}, 70%, 50%)`,
                legendFontColor: '#333',
                legendFontSize: 12,
              }))}
              width={screenWidth - 60}
              height={220}
              chartConfig={chartConfig}
              accessor="load"
              backgroundColor="transparent"
              paddingLeft="15"
              style={styles.chart}
            />
          </Card.Content>
        </Card>
      )}

      {/* Quick Actions */}
      <Card style={styles.card}>
        <Card.Content>
          <Title>Quick Actions</Title>
          <View style={styles.actionButtons}>
            <Button
              mode="contained"
              icon="add"
              onPress={() => navigation.navigate('Jobs', { screen: 'CreateJob' })}
              style={styles.actionButton}
            >
              New Job
            </Button>
            <Button
              mode="outlined"
              icon="device-hub"
              onPress={() => navigation.navigate('Cluster')}
              style={styles.actionButton}
            >
              Cluster Status
            </Button>
            <Button
              mode="outlined"
              icon="computer"
              onPress={() => navigation.navigate('Nodes')}
              style={styles.actionButton}
            >
              View Nodes
            </Button>
          </View>
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
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 16,
  },
  statusCards: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingTop: 16,
  },
  statusCard: {
    flex: 1,
    marginHorizontal: 4,
  },
  statusContent: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  statusText: {
    marginLeft: 12,
    flex: 1,
  },
  statusValue: {
    fontSize: 20,
    fontWeight: 'bold',
  },
  card: {
    margin: 16,
    marginTop: 16,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  healthContainer: {
    marginTop: 16,
  },
  healthMetric: {
    marginBottom: 16,
  },
  progressBar: {
    height: 8,
    borderRadius: 4,
    marginVertical: 8,
  },
  chart: {
    marginTop: 16,
    borderRadius: 16,
  },
  jobItem: {
    padding: 16,
    marginBottom: 8,
    borderRadius: 8,
    elevation: 1,
  },
  jobHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  jobName: {
    fontWeight: 'bold',
    flex: 1,
  },
  statusChip: {
    height: 28,
  },
  jobProgress: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
  },
  actionButtons: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 16,
  },
  actionButton: {
    flex: 1,
    marginHorizontal: 4,
  },
});

export default DashboardScreen;