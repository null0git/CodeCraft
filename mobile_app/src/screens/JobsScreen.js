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
  Button,
  ProgressBar,
  ActivityIndicator,
  FAB,
  Searchbar,
  Surface,
  IconButton,
} from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialIcons';
import Toast from 'react-native-toast-message';

import ApiService from '../services/ApiService';
import { formatDuration, getStatusColor, formatNumber } from '../utils/helpers';

const JobsScreen = ({ navigation }) => {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filteredJobs, setFilteredJobs] = useState([]);
  const [filter, setFilter] = useState('all'); // all, running, completed, failed

  const loadJobs = useCallback(async () => {
    try {
      const jobData = await ApiService.getJobs();
      setJobs(jobData);
      setFilteredJobs(jobData);
    } catch (error) {
      Toast.show({
        type: 'error',
        text1: 'Failed to load jobs',
        text2: error.message
      });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    loadJobs();
  }, [loadJobs]);

  const handleSearch = useCallback((query) => {
    setSearchQuery(query);
    applyFilters(jobs, query, filter);
  }, [jobs, filter]);

  const handleFilterChange = useCallback((newFilter) => {
    setFilter(newFilter);
    applyFilters(jobs, searchQuery, newFilter);
  }, [jobs, searchQuery]);

  const applyFilters = useCallback((jobList, query, statusFilter) => {
    let filtered = jobList;

    // Apply status filter
    if (statusFilter !== 'all') {
      filtered = filtered.filter(job => job.status === statusFilter);
    }

    // Apply search filter
    if (query.trim() !== '') {
      filtered = filtered.filter(job =>
        job.name?.toLowerCase().includes(query.toLowerCase()) ||
        job.hash_type?.toLowerCase().includes(query.toLowerCase()) ||
        job.job_id?.toLowerCase().includes(query.toLowerCase())
      );
    }

    setFilteredJobs(filtered);
  }, []);

  useEffect(() => {
    loadJobs();
    
    // Auto-refresh every 15 seconds
    const interval = setInterval(loadJobs, 15000);
    return () => clearInterval(interval);
  }, [loadJobs]);

  useEffect(() => {
    applyFilters(jobs, searchQuery, filter);
  }, [jobs, searchQuery, filter, applyFilters]);

  const stopJob = async (jobId) => {
    try {
      await ApiService.stopJob(jobId);
      Toast.show({
        type: 'success',
        text1: 'Job Stopped',
        text2: 'Job has been stopped successfully'
      });
      loadJobs();
    } catch (error) {
      Toast.show({
        type: 'error',
        text1: 'Stop Failed',
        text2: error.message
      });
    }
  };

  const deleteJob = async (jobId) => {
    try {
      await ApiService.deleteJob(jobId);
      Toast.show({
        type: 'success',
        text1: 'Job Deleted',
        text2: 'Job has been deleted successfully'
      });
      loadJobs();
    } catch (error) {
      Toast.show({
        type: 'error',
        text1: 'Delete Failed',
        text2: error.message
      });
    }
  };

  const renderJobCard = ({ item: job }) => {
    const isRunning = job.status === 'running' || job.status === 'working';
    const progress = job.progress_percent || 0;
    const crackedCount = job.cracked_hashes || 0;
    const totalCount = job.total_hashes || 0;
    
    return (
      <TouchableOpacity
        onPress={() => navigation.navigate('JobDetail', { jobId: job.id })}
      >
        <Card style={styles.jobCard}>
          <Card.Content>
            {/* Job Header */}
            <View style={styles.jobHeader}>
              <View style={styles.jobInfo}>
                <Title style={styles.jobTitle}>
                  {job.name || `Job ${job.id}`}
                </Title>
                <Paragraph style={styles.jobId}>
                  ID: {job.job_id?.slice(0, 12) || job.id}...
                </Paragraph>
              </View>
              <Chip
                mode="outlined"
                style={[
                  styles.statusChip,
                  { backgroundColor: getStatusColor(job.status) }
                ]}
              >
                {job.status}
              </Chip>
            </View>

            {/* Job Details */}
            <View style={styles.jobDetails}>
              <View style={styles.detailRow}>
                <Icon name="lock" size={16} color="#666" />
                <Paragraph style={styles.detailText}>
                  {job.hash_type || 'Unknown'} • {formatNumber(totalCount)} hashes
                </Paragraph>
              </View>
              
              <View style={styles.detailRow}>
                <Icon name="schedule" size={16} color="#666" />
                <Paragraph style={styles.detailText}>
                  Created: {job.created_at ? 
                    new Date(job.created_at).toLocaleDateString() : 
                    'Unknown'
                  }
                </Paragraph>
              </View>
              
              {job.duration && (
                <View style={styles.detailRow}>
                  <Icon name="timer" size={16} color="#666" />
                  <Paragraph style={styles.detailText}>
                    Duration: {formatDuration(job.duration)}
                  </Paragraph>
                </View>
              )}
            </View>

            {/* Progress */}
            <View style={styles.progressContainer}>
              <View style={styles.progressHeader}>
                <Paragraph style={styles.progressLabel}>Progress</Paragraph>
                <Paragraph style={styles.progressValue}>
                  {progress.toFixed(1)}%
                </Paragraph>
              </View>
              <ProgressBar
                progress={progress / 100}
                color={isRunning ? "#2196F3" : "#4CAF50"}
                style={styles.progressBar}
              />
              <View style={styles.progressStats}>
                <Paragraph style={styles.statsText}>
                  {formatNumber(crackedCount)} / {formatNumber(totalCount)} cracked
                </Paragraph>
                {job.passwords_found && job.passwords_found > 0 && (
                  <Paragraph style={styles.passwordsFound}>
                    🔓 {job.passwords_found} found
                  </Paragraph>
                )}
              </View>
            </View>

            {/* Assigned Nodes */}
            {job.assigned_nodes && job.assigned_nodes.length > 0 && (
              <View style={styles.nodesContainer}>
                <Paragraph style={styles.nodesLabel}>
                  Nodes ({job.assigned_nodes.length}):
                </Paragraph>
                <View style={styles.nodesList}>
                  {job.assigned_nodes.slice(0, 3).map((node, index) => (
                    <Chip
                      key={index}
                      mode="outlined"
                      style={styles.nodeChip}
                      compact
                    >
                      {node.hostname || node.slice(0, 8)}
                    </Chip>
                  ))}
                  {job.assigned_nodes.length > 3 && (
                    <Chip
                      mode="outlined"
                      style={styles.nodeChip}
                      compact
                    >
                      +{job.assigned_nodes.length - 3}
                    </Chip>
                  )}
                </View>
              </View>
            )}

            {/* Quick Actions */}
            <View style={styles.actionButtons}>
              <IconButton
                icon="info"
                size={20}
                onPress={() => navigation.navigate('JobDetail', { jobId: job.id })}
                style={styles.actionButton}
              />
              
              {isRunning && (
                <IconButton
                  icon="stop"
                  size={20}
                  onPress={() => stopJob(job.id)}
                  style={styles.actionButton}
                />
              )}
              
              {!isRunning && (
                <IconButton
                  icon="delete"
                  size={20}
                  onPress={() => deleteJob(job.id)}
                  style={styles.actionButton}
                />
              )}
              
              <IconButton
                icon="refresh"
                size={20}
                onPress={() => refreshJob(job.id)}
                style={styles.actionButton}
              />
            </View>
          </Card.Content>
        </Card>
      </TouchableOpacity>
    );
  };

  const refreshJob = async (jobId) => {
    try {
      await loadJobs();
    } catch (error) {
      Toast.show({
        type: 'error',
        text1: 'Refresh Failed',
        text2: error.message
      });
    }
  };

  const renderFilterChips = () => (
    <View style={styles.filterContainer}>
      {['all', 'running', 'completed', 'failed'].map((filterOption) => (
        <Chip
          key={filterOption}
          mode={filter === filterOption ? 'flat' : 'outlined'}
          selected={filter === filterOption}
          onPress={() => handleFilterChange(filterOption)}
          style={styles.filterChip}
        >
          {filterOption.charAt(0).toUpperCase() + filterOption.slice(1)}
        </Chip>
      ))}
    </View>
  );

  const renderEmptyList = () => (
    <View style={styles.emptyContainer}>
      <Icon name="work" size={64} color="#ccc" />
      <Title style={styles.emptyTitle}>No Jobs Found</Title>
      <Paragraph style={styles.emptyText}>
        {searchQuery || filter !== 'all' 
          ? 'No jobs match your current filters' 
          : 'No password cracking jobs have been created yet'
        }
      </Paragraph>
      {(!searchQuery && filter === 'all') && (
        <Button
          mode="contained"
          onPress={() => navigation.navigate('CreateJob')}
          style={styles.createButton}
        >
          Create Your First Job
        </Button>
      )}
    </View>
  );

  const renderHeader = () => (
    <View style={styles.header}>
      <View style={styles.headerStats}>
        <Surface style={styles.statItem}>
          <Title style={styles.statValue}>{filteredJobs.length}</Title>
          <Paragraph style={styles.statLabel}>
            {filter === 'all' ? 'Total' : filter.charAt(0).toUpperCase() + filter.slice(1)} Jobs
          </Paragraph>
        </Surface>
        
        <Surface style={styles.statItem}>
          <Title style={styles.statValue}>
            {jobs.filter(j => j.status === 'running' || j.status === 'working').length}
          </Title>
          <Paragraph style={styles.statLabel}>Active</Paragraph>
        </Surface>
        
        <Surface style={styles.statItem}>
          <Title style={styles.statValue}>
            {jobs.filter(j => j.status === 'completed').length}
          </Title>
          <Paragraph style={styles.statLabel}>Completed</Paragraph>
        </Surface>
      </View>
      
      <Searchbar
        placeholder="Search jobs..."
        onChangeText={handleSearch}
        value={searchQuery}
        style={styles.searchBar}
        iconColor="#666"
      />
      
      {renderFilterChips()}
    </View>
  );

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" />
        <Paragraph style={styles.loadingText}>Loading jobs...</Paragraph>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={filteredJobs}
        renderItem={renderJobCard}
        keyExtractor={(item) => item.id?.toString() || item.job_id}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
        ListHeaderComponent={renderHeader}
        ListEmptyComponent={renderEmptyList}
        contentContainerStyle={styles.listContainer}
        showsVerticalScrollIndicator={false}
      />
      
      {/* Floating Action Button */}
      <FAB
        icon="plus"
        style={styles.fab}
        onPress={() => navigation.navigate('CreateJob')}
        label="New Job"
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
    paddingBottom: 80,
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
    marginBottom: 16,
  },
  filterContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  filterChip: {
    marginRight: 8,
    marginBottom: 8,
  },
  jobCard: {
    marginHorizontal: 16,
    marginBottom: 8,
  },
  jobHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  jobInfo: {
    flex: 1,
  },
  jobTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  jobId: {
    fontFamily: 'monospace',
    fontSize: 12,
    opacity: 0.7,
  },
  statusChip: {
    alignSelf: 'flex-start',
  },
  jobDetails: {
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
  progressContainer: {
    marginBottom: 16,
  },
  progressHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  progressLabel: {
    fontSize: 14,
    fontWeight: '500',
  },
  progressValue: {
    fontSize: 14,
    fontWeight: 'bold',
  },
  progressBar: {
    height: 8,
    borderRadius: 4,
    marginBottom: 8,
  },
  progressStats: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  statsText: {
    fontSize: 12,
    opacity: 0.7,
  },
  passwordsFound: {
    fontSize: 12,
    fontWeight: 'bold',
    color: '#4CAF50',
  },
  nodesContainer: {
    marginBottom: 12,
  },
  nodesLabel: {
    fontSize: 14,
    fontWeight: '500',
    marginBottom: 8,
  },
  nodesList: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 4,
  },
  nodeChip: {
    height: 28,
    marginRight: 4,
    marginBottom: 4,
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
    marginBottom: 24,
  },
  createButton: {
    marginTop: 16,
  },
  fab: {
    position: 'absolute',
    margin: 16,
    right: 0,
    bottom: 0,
    backgroundColor: '#6200ee',
  },
});

export default JobsScreen;