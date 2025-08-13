import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  ScrollView,
  RefreshControl,
  StyleSheet,
  Alert,
} from 'react-native';
import {
  Card,
  Title,
  Paragraph,
  Button,
  Chip,
  Surface,
  ActivityIndicator,
  Divider,
  IconButton,
} from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialIcons';
import Toast from 'react-native-toast-message';

import ApiService from '../services/ApiService';
import { formatDuration, getStatusColor } from '../utils/helpers';

const ClusterScreen = ({ navigation }) => {
  const [clusterInfo, setClusterInfo] = useState(null);
  const [clusterStatus, setClusterStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadClusterData = useCallback(async () => {
    try {
      const [info, status] = await Promise.all([
        ApiService.getClusterInfo(),
        ApiService.getClusterStatus()
      ]);
      
      setClusterInfo(info);
      setClusterStatus(status);
    } catch (error) {
      Toast.show({
        type: 'error',
        text1: 'Failed to load cluster data',
        text2: error.message
      });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    loadClusterData();
  }, [loadClusterData]);

  const handleForceElection = () => {
    Alert.alert(
      'Force Election',
      'Are you sure you want to force a new leader election? This may temporarily disrupt cluster operations.',
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Force Election', style: 'destructive', onPress: forceElection }
      ]
    );
  };

  const forceElection = async () => {
    try {
      await ApiService.forceElection();
      Toast.show({
        type: 'success',
        text1: 'Election Initiated',
        text2: 'New leader election has been started'
      });
      // Reload data after a short delay
      setTimeout(loadClusterData, 2000);
    } catch (error) {
      Toast.show({
        type: 'error',
        text1: 'Election Failed',
        text2: error.message
      });
    }
  };

  useEffect(() => {
    loadClusterData();
    
    // Auto-refresh every 15 seconds
    const interval = setInterval(loadClusterData, 15000);
    return () => clearInterval(interval);
  }, [loadClusterData]);

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" />
        <Paragraph style={styles.loadingText}>Loading cluster status...</Paragraph>
      </View>
    );
  }

  const isLeader = clusterInfo?.node_id === clusterInfo?.leader_id;
  const healthyNodes = clusterInfo?.healthy_nodes || 0;
  const totalNodes = clusterInfo?.node_count || 0;

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }
    >
      {/* Cluster Overview */}
      <Card style={styles.card}>
        <Card.Content>
          <View style={styles.headerRow}>
            <Title>Cluster Overview</Title>
            <IconButton
              icon="refresh"
              size={24}
              onPress={loadClusterData}
            />
          </View>
          
          <View style={styles.overviewGrid}>
            <View style={styles.overviewItem}>
              <Icon name="device-hub" size={32} color="#4CAF50" />
              <Title style={styles.overviewValue}>{totalNodes + 1}</Title>
              <Paragraph>Total Nodes</Paragraph>
            </View>
            
            <View style={styles.overviewItem}>
              <Icon name="check-circle" size={32} color="#2196F3" />
              <Title style={styles.overviewValue}>{healthyNodes}</Title>
              <Paragraph>Healthy</Paragraph>
            </View>
            
            <View style={styles.overviewItem}>
              <Icon name="schedule" size={32} color="#FF9800" />
              <Title style={styles.overviewValue}>{clusterInfo?.term || 0}</Title>
              <Paragraph>Term</Paragraph>
            </View>
          </View>
        </Card.Content>
      </Card>

      {/* Current Node Status */}
      <Card style={styles.card}>
        <Card.Content>
          <Title>Current Node</Title>
          <Surface style={styles.nodeStatus}>
            <View style={styles.nodeHeader}>
              <View style={styles.nodeInfo}>
                <Paragraph style={styles.nodeId}>
                  ID: {clusterInfo?.node_id?.slice(0, 12) || 'Unknown'}...
                </Paragraph>
                <Chip
                  mode="outlined"
                  style={[
                    styles.roleChip,
                    { backgroundColor: isLeader ? '#FFF3E0' : '#E3F2FD' }
                  ]}
                  textStyle={{ color: isLeader ? '#FF8F00' : '#1976D2' }}
                >
                  {isLeader ? 'Leader' : 'Follower'}
                </Chip>
              </View>
              {isLeader && (
                <Icon name="star" size={24} color="#FF8F00" />
              )}
            </View>
            
            {clusterStatus?.current_node && (
              <View style={styles.nodeMetrics}>
                <View style={styles.metricRow}>
                  <Paragraph>CPU: {clusterStatus.current_node.load_metrics?.cpu_usage?.toFixed(1) || 0}%</Paragraph>
                  <Paragraph>Memory: {clusterStatus.current_node.load_metrics?.memory_usage?.toFixed(1) || 0}%</Paragraph>
                </View>
                <View style={styles.metricRow}>
                  <Paragraph>Threads: {clusterStatus.threads_active || 0}</Paragraph>
                  <Paragraph>Uptime: {formatDuration(clusterStatus.uptime || 0)}</Paragraph>
                </View>
              </View>
            )}
          </Surface>
        </Card.Content>
      </Card>

      {/* Leader Information */}
      {clusterInfo?.leader_id && (
        <Card style={styles.card}>
          <Card.Content>
            <View style={styles.headerRow}>
              <Title>Cluster Leader</Title>
              <Button
                mode="outlined"
                onPress={handleForceElection}
                compact
                style={styles.electionButton}
              >
                Force Election
              </Button>
            </View>
            
            <Surface style={styles.leaderInfo}>
              <View style={styles.leaderHeader}>
                <Icon name="account-circle" size={40} color="#FF8F00" />
                <View style={styles.leaderDetails}>
                  <Paragraph style={styles.leaderTitle}>Current Leader</Paragraph>
                  <Paragraph style={styles.leaderId}>
                    {clusterInfo.leader_id.slice(0, 16)}...
                  </Paragraph>
                  <Paragraph style={styles.leaderTerm}>Term: {clusterInfo.term}</Paragraph>
                </View>
              </View>
              
              {isLeader && (
                <View style={styles.leaderBadge}>
                  <Chip
                    mode="outlined"
                    style={styles.currentLeaderChip}
                    textStyle={{ color: '#FF8F00' }}
                  >
                    You are the leader
                  </Chip>
                </View>
              )}
            </Surface>
          </Card.Content>
        </Card>
      )}

      {/* Cluster Health */}
      <Card style={styles.card}>
        <Card.Content>
          <Title>Cluster Health</Title>
          
          <View style={styles.healthGrid}>
            <View style={styles.healthItem}>
              <View style={styles.healthIndicator}>
                <Icon 
                  name="circle" 
                  size={16} 
                  color={healthyNodes === totalNodes + 1 ? '#4CAF50' : '#FF9800'} 
                />
                <Paragraph style={styles.healthLabel}>Overall</Paragraph>
              </View>
              <Paragraph style={styles.healthValue}>
                {healthyNodes === totalNodes + 1 ? 'Healthy' : 'Warning'}
              </Paragraph>
            </View>
            
            <View style={styles.healthItem}>
              <View style={styles.healthIndicator}>
                <Icon name="computer" size={16} color="#2196F3" />
                <Paragraph style={styles.healthLabel}>Nodes</Paragraph>
              </View>
              <Paragraph style={styles.healthValue}>
                {healthyNodes}/{totalNodes + 1} Active
              </Paragraph>
            </View>
            
            <View style={styles.healthItem}>
              <View style={styles.healthIndicator}>
                <Icon name="network-check" size={16} color="#9C27B0" />
                <Paragraph style={styles.healthLabel}>Network</Paragraph>
              </View>
              <Paragraph style={styles.healthValue}>Connected</Paragraph>
            </View>
          </View>
        </Card.Content>
      </Card>

      {/* Quick Actions */}
      <Card style={styles.card}>
        <Card.Content>
          <Title>Cluster Actions</Title>
          
          <View style={styles.actionGrid}>
            <Button
              mode="contained"
              icon="people"
              onPress={() => navigation.navigate('Nodes')}
              style={styles.actionButton}
            >
              View Nodes
            </Button>
            
            <Button
              mode="outlined"
              icon="analytics"
              onPress={() => navigation.navigate('ClusterMetrics')}
              style={styles.actionButton}
            >
              Metrics
            </Button>
            
            <Button
              mode="outlined"
              icon="history"
              onPress={() => navigation.navigate('FailoverHistory')}
              style={styles.actionButton}
            >
              Failover Log
            </Button>
            
            <Button
              mode="outlined"
              icon="settings"
              onPress={() => navigation.navigate('ClusterSettings')}
              style={styles.actionButton}
            >
              Settings
            </Button>
          </View>
        </Card.Content>
      </Card>

      {/* Connection Status */}
      <Card style={styles.card}>
        <Card.Content>
          <Title>Connection Status</Title>
          
          <View style={styles.connectionStatus}>
            <View style={styles.connectionItem}>
              <Icon name="wifi" size={24} color="#4CAF50" />
              <View style={styles.connectionDetails}>
                <Paragraph style={styles.connectionLabel}>Server Connection</Paragraph>
                <Paragraph style={styles.connectionValue}>Connected</Paragraph>
              </View>
            </View>
            
            <Divider style={styles.divider} />
            
            <View style={styles.connectionItem}>
              <Icon name="sync" size={24} color="#2196F3" />
              <View style={styles.connectionDetails}>
                <Paragraph style={styles.connectionLabel}>Last Sync</Paragraph>
                <Paragraph style={styles.connectionValue}>
                  {new Date().toLocaleTimeString()}
                </Paragraph>
              </View>
            </View>
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
  card: {
    margin: 16,
    marginBottom: 8,
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  overviewGrid: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginTop: 16,
  },
  overviewItem: {
    alignItems: 'center',
    flex: 1,
  },
  overviewValue: {
    fontSize: 24,
    fontWeight: 'bold',
    marginTop: 8,
  },
  nodeStatus: {
    padding: 16,
    borderRadius: 8,
    marginTop: 16,
  },
  nodeHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  nodeInfo: {
    flex: 1,
  },
  nodeId: {
    fontFamily: 'monospace',
    fontSize: 12,
    marginBottom: 8,
  },
  roleChip: {
    alignSelf: 'flex-start',
  },
  nodeMetrics: {
    marginTop: 12,
  },
  metricRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  electionButton: {
    borderColor: '#FF9800',
  },
  leaderInfo: {
    padding: 16,
    borderRadius: 8,
    marginTop: 16,
  },
  leaderHeader: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  leaderDetails: {
    marginLeft: 16,
    flex: 1,
  },
  leaderTitle: {
    fontWeight: 'bold',
    fontSize: 16,
  },
  leaderId: {
    fontFamily: 'monospace',
    fontSize: 12,
    opacity: 0.7,
  },
  leaderTerm: {
    fontSize: 12,
    opacity: 0.7,
  },
  leaderBadge: {
    marginTop: 12,
    alignItems: 'flex-start',
  },
  currentLeaderChip: {
    backgroundColor: '#FFF3E0',
  },
  healthGrid: {
    marginTop: 16,
  },
  healthItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
  },
  healthIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  healthLabel: {
    marginLeft: 8,
    fontWeight: '500',
  },
  healthValue: {
    fontWeight: 'bold',
  },
  actionGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    marginTop: 16,
  },
  actionButton: {
    width: '48%',
    marginBottom: 8,
  },
  connectionStatus: {
    marginTop: 16,
  },
  connectionItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
  },
  connectionDetails: {
    marginLeft: 16,
    flex: 1,
  },
  connectionLabel: {
    fontSize: 14,
    opacity: 0.7,
  },
  connectionValue: {
    fontSize: 16,
    fontWeight: '500',
  },
  divider: {
    marginVertical: 8,
  },
});

export default ClusterScreen;