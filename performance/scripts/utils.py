import ConfigParser
import codecs
import csv
import os
import re
from datetime import datetime, timedelta


def convert_timedelta_to_milliseconds(td):
    """convert timedelta to milliseconds"""
    ms = td.days * 86400 * 1E3 + td.seconds * 1E3 + td.microseconds / 1E3
    return int(ms)


class CustomLogParser(object):
    def __init__(self, filename):
        self.filename = filename
        self.data = []

    def __load_log_messages(self):
        fp = codecs.open(self.filename, "r", "utf-8")
        self.data = fp.readlines()
        fp.close()

    def fetch_request_logs(self, request_id):
        if os.path.exists(self.filename) and os.access(self.filename, os.R_OK):
            self.__load_log_messages()
            filtered_logs = []
            for line in self.data:
                if line.find(request_id) != -1:
                    filtered_logs.append(line)
            self.data = []
            return filtered_logs
        else:
            print _("Unable to read log file %s") % self.filename
            return False

    def fetch_regex_value(self, request_id, regex):
        logs = self.fetch_request_logs(request_id)
        value = None
        if logs:
            for line in logs:
                mObj = re.search(regex, line)
                if mObj:
                    return mObj
        return None


class LogAnalyzer(object):
    def __init__(self, file_name, date_regex, date_format):
        self.log_parser = CustomLogParser(file_name)
        self.date_regex = date_regex
        self.date_format = date_format

    def fetch_request_metrics(self, request_id, task_name_log_map,
                              timedelta_convertor=None):
        """Fetch the request logs and calculate metrics"""
        metrics = {}

        request_logs = self.log_parser.fetch_request_logs(request_id)
        if request_logs:
            if not timedelta_convertor:
                timedelta_convertor = convert_timedelta_to_milliseconds

            mObj = re.search(self.date_regex, request_logs[0])
            if not mObj:
                print _("Date field not available in log message. Please"\
                        "check the date format in configuration.")
                return metrics
            start_time = datetime.strptime(mObj.group('date_time'),
                                           self.date_format)

            mObj = re.search(self.date_regex, request_logs[-1])
            end_time = datetime.strptime(mObj.group('date_time'),
                                         self.date_format)

            task_time = {}
            last_time = start_time
            start_index = 0
            for task, log_msg in task_name_log_map:
                found = False
                for index in range(start_index, len(request_logs)):
                    mObj = re.search(log_msg % self.date_regex,
                                     request_logs[index])
                    if mObj:
                        #log found.
                        current_time = datetime.strptime(
                            mObj.group('date_time'), self.date_format)
                        time_taken = current_time - last_time
                        last_time = current_time
                        task_time[task] = timedelta_convertor(time_taken)
                        found = True
                        start_index = index
                        break
                if not found:
                    print _("Expected log message '%(log_msg)s' not found "\
                        "for request %(request_id)s") % locals()
                    task_time[task] = 0
            response_time = timedelta_convertor(end_time - start_time)
            task_time['api_response_time'] = response_time
            metrics = {'start_time': start_time,
                       'end_time': end_time,
                       'task_time': task_time}
        return metrics

    def fetch_metrics_summary(self, results_list, metrics):
        """Fetch the min, max and avg for specified metrics"""
        result = {}
        for metric in metrics:
            values = []
            for result in results_list:
                values.append(result['task_time'][metric])
            result.update({'min_%s' % metric: min(values),
                      'max_%s' % metric: max(values),
                      'avg_%s' % metric: sum(values) / len(values)})
        return result


class PerfResultsLogger(object):
    def __init__(self, format, filename):
        self.format = format
        self.filename = filename

    def _emit(self, results_list):
        fp = open(self.filename, "a")
        writer = csv.writer(fp)
        writer.writerows(results_list)
        fp.close()

    def log_results(self, fields, results_list):
        """
        Log the results.
        params: fields - list (order in which fields are written to csv)
        params: results_list - list containing dictionary of results per api
        """
        log_result_list = []
        #write the field names first.
        if not os.path.exists(self.filename):
            log_result_list.append(fields)

        for result in results_list:
            result_list = []
            #preserve the order in which fields are written to csv.
            for field in fields:
                result_list.append(result[field])
            log_result_list.append(result_list)
        if log_result_list:
            self._emit(log_result_list)


class PerfAnalyzerConfig(object):
    """Provides configuration information."""

    def __init__(self, path="nova_api_perf_analyzer.conf"):
        """Initialize a configuration from a path."""
        self.conf = self.load_config(path)

    def load_config(self, path=None):
        """Read configuration from given path and return a config object."""
        config = ConfigParser.SafeConfigParser()
        config.read(path)
        return config

    def get(self, item_name, default_value):
        try:
            return self.conf.get("default", item_name)
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            return default_value

    @property
    def result_file_prefix(self):
        """Results file name prefix to use"""
        return self.get("result_file_prefix", 'nova_api')

    @property
    def result_file_dir(self):
        """Results file to create in this directory """
        return self.get("result_file_dir", os.getcwd())
