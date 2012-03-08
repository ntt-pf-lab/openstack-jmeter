# Performance test runner script

JMETER_DIR=/home/rohit/jmeter/apache-jmeter-2.6
CMD_RUNNER=$JMETER_DIR/lib/ext/CMDRunner.jar

PERF_BASE_DIR=/home/rohit/openstack-jmeter/performance
NOVA_DIR=$PERF_BASE_DIR/nova
KEYSTONE_DIR=$PERF_BASE_DIR/keystone
COMMON_DIR=$PERF_BASE_DIR/common

SERVERS_TESTPLAN=$NOVA_DIR/test_plans/load/servers.jmx
KEYSTONE_TESTPLAN=$KEYSTONE_DIR/test_plans/load/keystone.jmx
NETWORKS_TESTPLAN=$NOVA_DIR/test_plans/load/create_networks.jmx

PROPERTIES_DIR=$COMMON_DIR/properties

SCRIPTS_DIR=$PERF_BASE_DIR/scripts
REPORTS_DIR=$PERF_BASE_DIR/reports

# Run SetUp test plans

$JMETER_DIR/bin/jmeter.sh -n -l samples.log -q $PROPERTIES_DIR/perftest.properties -t $KEYSTONE_TESTPLAN
$JMETER_DIR/bin/jmeter.sh -n -l samples.log -q $PROPERTIES_DIR/perftest.properties -t $NETWORKS_TESTPLAN

# Run Servers Testplan
$JMETER_DIR/bin/jmeter.sh -n -l samples.log -q $PROPERTIES_DIR/perftest.properties -t $SERVERS_TESTPLAN

# Generate Reports

python $SCRIPTS_DIR/jmeter_report_generator.py $REPORTS_DIR/jtls $REPORTS_DIR/stats $CMD_RUNNER_DIR
