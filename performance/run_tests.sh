# Performance test runner script


# Only configure the two variables below
JMETER_DIR=/opt/jmeter/apache-jmeter-2.6
PERF_BASE_DIR=/opt/openstack-jmeter/performance

NOVA_DIR=$PERF_BASE_DIR/nova
KEYSTONE_DIR=$PERF_BASE_DIR/keystone
COMMON_DIR=$PERF_BASE_DIR/common

SERVERS_TESTPLAN=$NOVA_DIR/test_plans/load/servers.jmx
KEYSTONE_TESTPLAN=$KEYSTONE_DIR/test_plans/load/keystone.jmx
NETWORKS_TESTPLAN=$NOVA_DIR/test_plans/load/create_networks.jmx

PROPERTIES_DIR=$COMMON_DIR/properties

SCRIPTS_DIR=$PERF_BASE_DIR/scripts
REPORTS_DIR=$PERF_BASE_DIR/reports

#------------------------------
# SERVERS API PERFORMANCE TESTS
#------------------------------

# Run SetUp test plans - Keystone and Networks

$JMETER_DIR/bin/jmeter.sh -n -l samples.log -q $PROPERTIES_DIR/perftest.properties -t $KEYSTONE_TESTPLAN
$JMETER_DIR/bin/jmeter.sh -n -l samples.log -q $PROPERTIES_DIR/perftest.properties -t $NETWORKS_TESTPLAN

# Run Servers Testplan
$JMETER_DIR/bin/jmeter.sh -n -l samples.log -q $PROPERTIES_DIR/perftest.properties -t $SERVERS_TESTPLAN

