import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  FlatList,
  RefreshControl,
  StyleSheet,
  TouchableOpacity,
} from 'react-native';
import {
  Card,
  Title,
  Paragraph,
  Chip,
  Surface,
  ActivityIndicator,
  ProgressBar,
  IconButton,
  Searchbar,
} from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialIcons';
import Toast from 'react-native-toast-message';

import ApiService from '../services/ApiService';
import { formatBytes, getStatusColor, formatDuration } from '../utils/helpers';

const NodesScreen = ({ navigation }) => {
  const [nodes, setNodes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filteredNodes, setFilteredNodes] = useState([]);

  const loadNodes = useCallback(async () => {
    try {
      const nodeData = await ApiService.getNodes();
      setNodes(nodeData);
      setFilteredNodes(nodeData);
    } catch (error) {
      Toast.show({
        type: 'error',
        text1: 'Failed to load nodes',
        text2: error.message
      });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    loadNodes();
  }, [loadNodes]);

  const handleSearch = useCallback((query) => {
    setSearchQuery(query);
    if (query.trim() === '') {
      setFilteredNodes(nodes);
    } else {
      const filtered = nodes.filter(node =>
        node.hostname?.toLowerCase().includes(query.toLowerCase()) ||
        node.client_id?.toLowerCase().includes(query.toLowerCase()) ||
        node.ip_address?.includes(query)
      );
      setFilteredNodes(filtered);
    }
  }, [nodes]);

  useEffect(() => {
    loadNodes();
    
    // Auto-refresh every 20 seconds
    const interval = setInterval(loadNodes, 20000);
    return () => clearInterval(interval);
  }, [loadNodes]);

  useEffect(() => {
    handleSearch(searchQuery);
  }, [nodes, searchQuery, handleSearch]);

  const renderNodeCard = ({ item: node }) => {
    const isOnline = node.status === 'online' || node.status === 'working';
    const cpuUsage = node.cpu_usage || 0;
    const ramUsage = node.ram_usage || 0;
    const diskUsage = node.disk_usage || 0;
    
    return (
      <TouchableOpacity
        onPress={() => navigation.navigate('NodeDetail', { nodeId: node.client_id })}
      >
        <Card style={styles.nodeCard}>
          <Card.Content>
            {/* Node Header */}
            <View style={styles.nodeHeader}>
              <View style={styles.nodeInfo}>
                <Title style={styles.nodeTitle}>
                  {node.hostname || 'Unknown Host'}
                </Title>
                <Paragraph style={styles.nodeId}>
                  {node.client_id?.slice(0, 12)}...
                </Paragraph>
              </View>
              <View style={styles.nodeStatus}>
                <Chip
                  mode="outlined"
                  style={[
                    styles.statusChip,
                    { backgroundColor: getStatusColor(node.status) }
                  ]}
                >
                  {node.status}
                </Chip>
                <View style={styles.statusIndicator}>
                  <Icon
                    name="circle"
                    size={12}
                    color={isOnline ? '#4CAF50' : '#F44336'}
                  />
                </View>
              </View>
            </View>

            {/* Node Details */}
            <View style={styles.nodeDetails}>
              <View style={styles.detailRow}>
                <Icon name="computer" size={16} color="#666" />
                <Paragraph style={styles.detailText}>
                  {node.ip_address} • {node.cpu_cores || 'N/A'} cores
                </Paragraph>
              </View>
              
              <View style={styles.detailRow}>
                <Icon name="schedule" size={16} color="#666" />
                <Paragraph style={styles.detailText}>
                  Last seen: {node.last_seen ? 
                    new Date(node.last_seen).toLocaleString() : 
                    'Never'
                  }
                </Paragraph>
              </View>
            </View>

            {/* Performance Metrics */}
            {isOnline && (
              <View style={styles.metricsContainer}>
                <View style={styles.metricItem}>
                  <View style={styles.metricHeader}>
                    <Paragraph style={styles.metricLabel}>CPU</Paragraph>
                    <Paragraph style={styles.metricValue}>{cpuUsage.toFixed(1)}%</Paragraph>
                  </View>
                  <ProgressBar
                    progress={cpuUsage / 100}
                    color="#FF9800"
                    style={styles.progressBar}
                  />
                </View>

                <View style={styles.metricItem}>
                  <View style={styles.metricHeader}>
                    <Paragraph style={styles.metricLabel}>RAM</Paragraph>
                    <Paragraph style={styles.metricValue}>{ramUsage.toFixed(1)}%</Paragraph>
                  </View>
                  <ProgressBar
                    progress={ramUsage / 100}
                    color="#2196F3"
                    style={styles.progressBar}
                  />
                </View>

                <View style={styles.metricItem}>
                  <View style={styles.metricHeader}>
                    <Paragraph style={styles.metricLabel}>Disk</Paragraph>
                    <Paragraph style={styles.metricValue}>{diskUsage.toFixed(1)}%</Paragraph>
                  </View>
                  <ProgressBar
                    progress={diskUsage / 100}
                    color="#4CAF50"
                    style={styles.progressBar}
                  />
                </View>
              </View>
            )}

            {/* Network Info */}
            <View style={styles.networkInfo}>
              <View style={styles.networkItem}>
                <Icon name="network-wifi" size={16} color="#666" />
                <Paragraph style={styles.networkText}>
                  Latency: {node.network_latency?.toFixed(0) || 'N/A'}ms
                </Paragraph>
              </View>
              
              {node.mac_address && (
                <View style={styles.networkItem}>
                  <Icon name="device-hub" size={16} color="#666" />
                  <Paragraph style={styles.networkText}>
                    MAC: {node.mac_address.slice(0, 8)}...
                  </Paragraph>
                </View>
              )}
            </View>

            {/* Quick Actions */}
            <View style={styles.actionButtons}>
              <IconButton
                icon="terminal"
                size={20}
                onPress={() => navigation.navigate('NodeTerminal', { 
                  nodeId: node.client_id,
                  hostname: node.hostname 
                })}
                style={styles.actionButton}
              />
              <IconButton
                icon="info"
                size={20}
                onPress={() => navigation.navigate('NodeDetail', { nodeId: node.client_id })}
                style={styles.actionButton}
              />
              <IconButton
                icon="refresh"
                size={20}
                onPress={() => refreshNode(node.client_id)}
                style={styles.actionButton}
              />
            </View>
          </Card.Content>
        </Card>
      </TouchableOpacity>
    );
  };

  const refreshNode = async (nodeId) => {
    try {
      // Refresh specific node data
      await loadNodes();
      Toast.show({
        type: 'success',
        text1: 'Node Refreshed',
        text2: 'Node data has been updated'
      });
    } catch (error) {
      Toast.show({
        type: 'error',
        text1: 'Refresh Failed',
        text2: error.message
      });
    }
  };

  const renderEmptyList = () => (
    <View style={styles.emptyContainer}>
      <Icon name="computer" size={64} color="#ccc" />
      <Title style={styles.emptyTitle}>No Nodes Found</Title>
      <Paragraph style={styles.emptyText}>
        {searchQuery ? 'No nodes match your search criteria' : 'No cluster nodes are currently connected'}
      </Paragraph>
    </View>
  );

  const renderHeader = () => (
    <View style={styles.header}>
      <View style={styles.headerStats}>
        <Surface style={styles.statItem}>
          <Title style={styles.statValue}>{filteredNodes.length}</Title>
          <Paragraph style={styles.statLabel}>
            {searchQuery ? 'Filtered' : 'Total'} Nodes
          </Paragraph>
        </Surface>
        
        <Surface style={styles.statItem}>
          <Title style={styles.statValue}>
            {filteredNodes.filter(n => n.status === 'online' || n.status === 'working').length}
          </Title>
          <Paragraph style={styles.statLabel}>Online</Paragraph>
        </Surface>
        
        <Surface style={styles.statItem}>
          <Title style={styles.statValue}>
            {filteredNodes.filter(n => n.status === 'working').length}
          </Title>
          <Paragraph style={styles.statLabel}>Working</Paragraph>
        </Surface>
      </View>
      
      <Searchbar
        placeholder="Search nodes..."
        onChangeText={handleSearch}
        value={searchQuery}
        style={styles.searchBar}
        iconColor="#666"
      />
    </View>
  );

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" />
        <Paragraph style={styles.loadingText}>Loading cluster nodes...</Paragraph>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={filteredNodes}
        renderItem={renderNodeCard}
        keyExtractor={(item) => item.id?.toString() || item.client_id}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
        ListHeaderComponent={renderHeader}
        ListEmptyComponent={renderEmptyList}
        contentContainerStyle={styles.listContainer}
        showsVerticalScrollIndicator={false}
      />
    </View>
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
  listContainer: {
    paddingBottom: 16,
  },
  header: {
    padding: 16,
    paddingBottom: 8,
  },
  headerStats: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  statItem: {
    flex: 1,
    padding: 12,
    marginHorizontal: 4,
    borderRadius: 8,
    alignItems: 'center',
    elevation: 1,
  },
  statValue: {
    fontSize: 20,
    fontWeight: 'bold',
  },
  statLabel: {
    fontSize: 12,
    opacity: 0.7,
  },
  searchBar: {
    elevation: 2,
  },
  nodeCard: {
    marginHorizontal: 16,
    marginBottom: 8,
  },
  nodeHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  nodeInfo: {
    flex: 1,
  },
  nodeTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  nodeId: {
    fontFamily: 'monospace',
    fontSize: 12,
    opacity: 0.7,
  },
  nodeStatus: {
    alignItems: 'flex-end',
  },
  statusChip: {
    marginBottom: 4,
  },
  statusIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  nodeDetails: {
    marginBottom: 16,
  },
  detailRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  detailText: {
    marginLeft: 8,
    fontSize: 14,
    opacity: 0.8,
  },
  metricsContainer: {
    marginBottom: 16,
  },
  metricItem: {
    marginBottom: 8,
  },
  metricHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  metricLabel: {
    fontSize: 14,
    fontWeight: '500',
  },
  metricValue: {
    fontSize: 14,
    fontWeight: 'bold',
  },
  progressBar: {
    height: 6,
    borderRadius: 3,
  },
  networkInfo: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  networkItem: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  networkText: {
    marginLeft: 4,
    fontSize: 12,
    opacity: 0.7,
  },
  actionButtons: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    borderTopWidth: 1,
    borderTopColor: '#eee',
    paddingTop: 8,
    marginTop: 8,
  },
  actionButton: {
    marginLeft: 8,
  },
  emptyContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 64,
  },
  emptyTitle: {
    marginTop: 16,
    fontSize: 20,
    fontWeight: 'bold',
  },
  emptyText: {
    marginTop: 8,
    textAlign: 'center',
    opacity: 0.7,
    paddingHorizontal: 32,
  },
});

export default NodesScreen;