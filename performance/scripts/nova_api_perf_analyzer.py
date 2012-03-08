#!/usr/bin/env python
"""
A script that analyzes Nova API performance.

Assumption:
The Nova services are configured for centralized logging using the syslog tool.

Usage:
python nova_api_perf_analyzer.py <api_name> <request_id> <tenant_id> <user_id>
<thread_group> [<log_filename>]
"""
import gettext
import os
import sys
import time
import utils
from optparse import OptionParser


#default date-time format of Nova service logs.
DATETIME_REGEX = '(?P<date_time>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})'
DATE_FORMAT = "%Y-%m-%d %H:%M:%S,%f"

gettext.install('nova_api_perf_analyzer', unicode=1)


class NovaAPIAnalyzer(object):
    def __init__(self, api, request_id, tenant_id, user_id, thread_group,
                 test_start_ms, instance_type, log_name, output_format='csv'):
        self.api = api
        self.request_id = request_id.strip()
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.thread_group = thread_group
        self.config = utils.PerfAnalyzerConfig()
        self.results_dir = os.path.join(self.config.result_file_dir,\
                                        test_start_ms,
                                        "stats")
        if not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir)
        self.output_format = output_format
        self.instance_type = instance_type
        results_file = self._get_results_filename()
        self.result_logger = utils.PerfResultsLogger(output_format,
                                                     results_file)
        self.log_analyzer = utils.LogAnalyzer(log_name,
                                              DATETIME_REGEX,
                                              DATE_FORMAT)

    def _get_results_filename(self):
        """Return the master results file name."""
        #read the prefix from config file and generate results file name.
        filename = self.config.result_file_prefix + "_" + self.api +\
                   "_index." + self.output_format
        return os.path.join(self.results_dir, filename)

    def _get_service_results_filename(self, service_name):
        """Return the result file name for the service."""
        #read the prefix from config file and generate service level file name.
        filename = self.config.result_file_prefix + "_" + self.api + "_" + \
                   service_name + "." + self.output_format
        return os.path.join(self.results_dir, filename)

    def _get_common_result_fields(self):
        """Return fields and values common to result log record."""
        result_dict = {'request_id': self.request_id,
                       'tenant_id': self.tenant_id,
                       'user_id': self.user_id,
                       'thread_group': self.thread_group,
                       'api_name': self.api}
        result_fields_ordered = ['api_name', 'request_id', 'tenant_id',
                                  'user_id', 'thread_group']
        if self.api == 'create':
            result_dict['instance_type'] = self.instance_type
            result_fields_ordered.append('instance_type')
        return result_dict, result_fields_ordered

    def _fetch_service_tasks(self, service_name):
        """Returns the list of tasks in a service."""
        tasks = []
        if service_name == 'nova-api':
            tasks = self._fetch_nova_api_tasks()
        elif service_name == 'compute':
            tasks = self._fetch_compute_tasks()
        elif service_name == 'scheduler':
            tasks = self._fetch_scheduler_tasks()
        elif service_name == 'network':
            tasks = self._fetch_network_tasks()
        return tasks

    def log_result(self, metrics, ordered_fields_list):
        """Logs the service level time breakdown"""
        result_record, ordered_fields = self._get_common_result_fields()
        result_record.update(metrics)
        ordered_fields.extend(ordered_fields_list)
        self.result_logger.log_results(ordered_fields, [result_record])

    def log_service_result(self, service_name, metrics):
        """Logs the function level time breakdown for service"""
        filename = self._get_service_results_filename(service_name)
        result_logger = utils.PerfResultsLogger(self.output_format,
                                                filename)
        result_record, ordered_fields = self._get_common_result_fields()
        result_record.update(metrics['task_time'])
        ordered_fields_list = self._fetch_service_tasks(service_name)
        ordered_fields.extend(ordered_fields_list)
        result_logger.log_results(ordered_fields, [result_record])

    def fetch_service_response_time(self, service_name, metrics):
        """Fetch the response time for each service."""
        tasks = self._fetch_service_tasks(service_name)
        service_time = 0
        for task in tasks:
            service_time += metrics[task]
        return service_time

    def fetch_metrics(self, server_logs):
        metrics = self.log_analyzer.fetch_request_metrics(self.request_id,
                                                     server_logs)
        if not metrics:
            msg = _("Request-id '%s' logs not available" % self.request_id)
            print msg
            sys.exit(1)
        return metrics

    def analyze_logs(self):
        """This method must be implemented by derived class."""
        raise NotImplementedError(_('Dervied class must implement me!'))


class ListServersAnalyzer(NovaAPIAnalyzer):
    server_logs = [('routing', '%s nova-api INFO [\s\S]+ GET [\S]+\/'
                   'servers$'),
                   ('fetch_options', '%s nova-api DEBUG [\s\S]+get_all'),
                   ('db_lookup', '%s nova-api INFO [\s\S]+ returned with '
                   'HTTP')]

    def _fetch_nova_api_tasks(self):
        return ['routing', 'fetch_options', 'db_lookup']

    def _fetch_nova_api_time(self, task_time):
        """Calculates the time taken by Nova API service"""
        return task_time['routing'] +\
               task_time['fetch_options'] +\
               task_time['db_lookup']

    def generate_master_results(self, task_time):
        """Return the list of fields in master results file."""
        ordered_fields = ['nova_api_time', 'api_response_time']
        metrics = {'nova_api_time': self._fetch_nova_api_time(task_time),
                   'api_response_time': task_time['api_response_time']}
        self.log_result(metrics, ordered_fields)

    def analyze_logs(self):
        """Fetches the metrics and logs the results."""
        metrics = self.fetch_metrics(self.server_logs)

        #write result to the master csv file
        self.generate_master_results(metrics['task_time'])
        #write result to the nova-api csv file.
        self.log_service_result('nova-api', metrics)


class CreateServerAnalyzer(NovaAPIAnalyzer):
    server_logs = [('routing', '%s nova-api INFO [\s\S]+ POST '\
                '[\S]+\/servers$'),
            ('check_params', '%s nova-api DEBUG [\s\S]+ Checked create '\
                'parameters'),
            ('start_bdm', '%s nova-api DEBUG [\s\S]+ block_device_mapping'),
            ('create_db_entry', '%s nova-api DEBUG [\s\S]+ '\
                'Created db entry for instance'),
            ('schedule_start', '%s nova-compute AUDIT [\s\S]+ instance '\
                                  '\d+: starting'),
            ('start_instance', '%s nova-compute DEBUG [\s\S]+ Making '\
                              'asynchronous call on network'),
            ('network_schedule', '%s nova-network DEBUG [\s\S]+ floating IP '\
                                'allocation for instance'),
            ('ip_allocation', '%s nova-compute DEBUG [\s\S]+ instance '\
                             'network_info'),
            ('start_xml_gen', '%s nova-compute DEBUG [\s\S]+ starting toXML'),
            ('xml_gen', '%s nova-compute DEBUG [\s\S]+ finished toXML'),
            ('start_firewall_setup', '%s nova-compute INFO [\s\S]+ called '\
                                    'setup_basic_filtering in nwfilter'),
            ('firewall_setup', '%s nova-compute INFO [\s\S]+ Creating image'),
            ('start_krn_img_fetch', '%s nova-compute DEBUG [\s\S]+ Fetching '\
                                   '\S+kernel image'),
            ('krn_img_fetch', '%s nova-compute DEBUG [\s\S]+ Fetched '\
                             '\S+kernel image'),
            ('krn_img_create', '%s nova-compute DEBUG [\s\S]+ Created kernel '\
                              'image'),
            ('start_rd_img_fetch', '%s nova-compute DEBUG [\s\S]+ Fetching '\
                                  '\S+ramdisk image'),
            ('rd_img_fetch', '%s nova-compute DEBUG [\s\S]+ Fetched '\
                             '\S+ramdisk image'),
            ('rd_img_create', '%s nova-compute DEBUG [\s\S]+ Created ramdisk '\
                             'image'),
            ('start_disk_img_fetch', '%s nova-compute DEBUG [\s\S]+ Fetching '\
                                    '\S+disk image'),
            ('disk_img_fetch', '%s nova-compute DEBUG [\s\S]+ Fetched '\
                               '\S+disk image'),
            ('disk_img_create', '%s nova-compute DEBUG [\s\S]+ Created disk '\
                               'image'),
            ('boot', '%s nova-compute INFO [\s\S]+ Instance \S+ spawned '\
                    'successfully')]

    def _fetch_compute_name(self):
        """Fetch the compute server on which instance is spawned."""
        compute_name_regex = "^\S{3}\s+\d{1,2} \d{2}\:\d{2}\:\d{2} "\
                             "(?P<compute_name>[\S]+) [\s\S]+ spawned "\
                             "successfully"
        log_parser = self.log_analyzer.log_parser
        match_obj = log_parser.fetch_regex_value(self.request_id,
                                                 compute_name_regex)
        compute_name = 'Not Available'
        if match_obj:
            compute_name = match_obj.group('compute_name')
        return compute_name

    def _fetch_nova_api_tasks(self):
        return ['routing', 'check_params', 'start_bdm', 'create_db_entry']

    def _fetch_image_fetch_tasks(self):
        return ['krn_img_fetch', 'rd_img_fetch', 'disk_img_fetch']

    def _fetch_image_create_tasks(self):
        return ['krn_img_create', 'rd_img_create', 'disk_img_create']

    def _fetch_compute_tasks(self):
        tasks = ['start_instance', 'xml_gen', 'firewall_setup', 'boot']
        tasks.extend(self._fetch_image_fetch_tasks())
        tasks.extend(self._fetch_image_create_tasks())
        return tasks

    def _fetch_scheduler_tasks(self):
        return ['schedule_start', 'network_schedule']

    def _fetch_network_tasks(self):
        return ['ip_allocation']

    def generate_master_results(self, task_time):
        """Return the list of fields in master results file."""
        ordered_fields = ['nova_api_time', 'scheduler_time', 'compute_time',
                          'compute_host', 'network_time', 'api_response_time']
        metrics = {'nova_api_time': self.fetch_service_response_time(
                                    'nova-api', task_time),
                   'compute_time': self.fetch_service_response_time(
                                   'compute', task_time),
                   'scheduler_time': self.fetch_service_response_time(
                                    'scheduler', task_time),
                   'network_time': self.fetch_service_response_time(
                                   'network', task_time),
                   'api_response_time': task_time['api_response_time'],
                   'compute_host': self._fetch_compute_name()}
        self.log_result(metrics, ordered_fields)

    def analyze_logs(self):
        """Fetches the metrics and logs the results."""
        metrics = self.fetch_metrics(self.server_logs)

        #write result to the master csv file
        self.generate_master_results(metrics['task_time'])

        #write result to the nova-api csv file.
        self.log_service_result('nova-api', metrics)
        #write result to the compute csv file.
        self.log_service_result('compute', metrics)
        #write result to the scheduler csv file.
        self.log_service_result('scheduler', metrics)
        #write result to the network csv file.
        self.log_service_result('network', metrics)


class DeleteServerAnalyzer(NovaAPIAnalyzer):
    server_logs = [
        ('routing', '%s nova-api INFO [\s\S]+ DELETE'),
        ('nova_api', '%s nova-api DEBUG [\s\S]+ Going to try to terminate'),
        ('db_fetch_update', '%s nova-api DEBUG [\s\S]+ Making asynchronous '\
         'cast on compute'),
        ('compute_schedule', '%s nova-compute DEBUG [\s\S]+ received'),
        ('start_lock_acquire', '%s nova-compute INFO [\s\S]+ '\
         'check_instance_lock: decorating'),
        ('lock_acquisition', '%s nova-compute INFO [\s\S]+ '\
         'check_instance_lock: executing'),
        ('db_fetch', '%s nova-compute AUDIT [\s\S]+ Terminating instance'),
        ('schedule_get_nw_info', '%s nova-network DEBUG [\s\S]+ received'),
        ('cast_deallocate', '%s nova-compute DEBUG[\s\S]+ Making '\
         'asynchronous cast on network'),
        ('schedule_deallocate', '%s nova-network DEBUG [\s\S]+ floating IP '\
         'deallocation for instance'),
        ('deallocate_network', '%s nova-network DEBUG [\s\S]+ Completed '\
         'floating IP deallocation'),
        ('destroy_instance', '%s nova-compute INFO [\s\S]+ Instance [\S]+ '\
         'destroyed successfully'),
        ('firewall_update', '%s nova-compute INFO [\s\S]+ deleting instance '\
         'files')]

    def _fetch_nova_api_tasks(self):
        return ['routing', 'nova_api', 'db_fetch_update']

    def _fetch_compute_tasks(self):
        return ['start_lock_acquire', 'lock_acquisition', 'db_fetch',
                 'destroy_instance', 'firewall_update']

    def _fetch_scheduler_tasks(self):
        return ['compute_schedule', 'schedule_get_nw_info',
                'schedule_deallocate']

    def _fetch_network_tasks(self):
        return ['deallocate_network']

    def generate_master_results(self, task_time):
        """Return the list of fields in master results file."""
        ordered_fields = ['nova_api_time', 'scheduler_time', 'compute_time',
                          'network_time', 'api_response_time']
        metrics = {'nova_api_time': self.fetch_service_response_time(
                                    'nova-api', task_time),
                   'compute_time': self.fetch_service_response_time(
                                   'compute', task_time),
                   'scheduler_time': self.fetch_service_response_time(
                                    'scheduler', task_time),
                   'network_time': self.fetch_service_response_time(
                                   'network', task_time),
                   'api_response_time': task_time['api_response_time']}
        self.log_result(metrics, ordered_fields)

    def analyze_logs(self):
        """Fetches the metrics and logs the results."""
        metrics = self.fetch_metrics(self.server_logs)
        #write result to the master csv file
        self.generate_master_results(metrics['task_time'])
        #write result to the nova-api csv file.
        self.log_service_result('nova-api', metrics)
        #write result to the compute csv file.
        self.log_service_result('compute', metrics)
        #write result to the scheduler csv file.
        self.log_service_result('scheduler', metrics)
        #write result to the network csv file.
        self.log_service_result('network', metrics)


class CreateSnapshotAnalyzer(NovaAPIAnalyzer):
    server_logs = [('routing', '%s nova-api INFO [\s\S]+ POST [\S]+\/action$'),
            ('register_image', '%s nova-api DEBUG [\s\S]+ Creating image in '\
                'Glance'),
            ('add_image', '%s nova-api DEBUG [\s\S]+ Metadata returned from '\
                'Glance'),
            ('cast_compute', '%s nova-api DEBUG [\s\S]+ Making asynchronous '\
                'cast on compute'),
            ('compute_schedule', '%s nova-compute DEBUG [\s\S]+ received'),
            ('unpack_ctxt', '%s nova-compute DEBUG [\s\S]+ Checking state'),
            ('check_state', '%s nova-compute AUDIT [\s\S]+ snapshotting'),
            ('export_snapshot', '%s nova-compute DEBUG [\s\S]+ Exported '\
                'instance \S+ snapshot'),
            ('upload_snapshot', '%s nova-compute DEBUG [\s\S]+ Uploaded '\
                'instance \S+ snapshot'),
            ('snapshot', '%s nova-compute DEBUG [\s\S]+ snapshot taken'),
            ('db_updation', '%s nova-compute DEBUG [\s\S]+ Updated task '\
                'state of instance')]

    def _fetch_nova_api_tasks(self):
        return ['routing', 'register_image', 'add_image']

    def _fetch_compute_tasks(self):
        return ['unpack_ctxt', 'check_state', 'export_snapshot',
                 'upload_snapshot', 'snapshot', 'db_updation']

    def _fetch_scheduler_tasks(self):
        return ['compute_schedule']

    def generate_master_results(self, task_time):
        """Return the list of fields in master results file."""
        ordered_fields = ['nova_api_time', 'scheduler_time', 'compute_time',
                          'api_response_time']
        metrics = {'nova_api_time': self.fetch_service_response_time(
                                    'nova-api', task_time),
                   'compute_time': self.fetch_service_response_time(
                                   'compute', task_time),
                   'scheduler_time': self.fetch_service_response_time(
                                    'scheduler', task_time),
                   'api_response_time': task_time['api_response_time']}
        self.log_result(metrics, ordered_fields)

    def analyze_logs(self):
        """Fetches the metrics and logs the results."""
        metrics = self.fetch_metrics(self.server_logs)
        #write result to the master csv file
        self.generate_master_results(metrics['task_time'])
        #write result to the nova-api csv file.
        self.log_service_result('nova-api', metrics)
        #write result to the compute csv file.
        self.log_service_result('compute', metrics)
        #write result to the scheduler csv file.
        self.log_service_result('scheduler', metrics)


APIS = {
    'list': ListServersAnalyzer,
    'create': CreateServerAnalyzer,
    'delete': DeleteServerAnalyzer,
    'snapshot': CreateSnapshotAnalyzer}


def create_options(parser):
    """Set up the options that may be parsed as program commands."""
    parser.add_option('-l', '--log_name', default="/var/log/syslog",
                      action="store", help="Nova service log file path")


def main():
    oparser = OptionParser()
    create_options(oparser)
    (options, args) = oparser.parse_args(sys.argv[1:])
    if not args or len(args) < 6:
        print _("API name, request id, tenant_id, user_id, thread_group and "\
                "test start time are mandatory.")
        sys.exit(0)

    api = args[0]
    if api not in APIS:
        print _("Unknown API %s") % api
        sys.exit(0)
    if api == 'create':
        if len(args) < 7:
            print _("Instance type is mandatory for Create Server API.")
            sys.exit(0)
        instance_type = args[6]
    else:
        instance_type = None
    #create the APIAnalyzer object and call analyze_logs( ) method.
    analyzer = APIS[api](api, args[1], args[2], args[3], args[4], args[5],
                         instance_type, log_name=options.log_name)
    analyzer.analyze_logs()


if __name__ == '__main__':
    main()
