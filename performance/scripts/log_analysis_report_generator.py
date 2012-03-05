#!/usr/bin/env python

'''Script that generates HTML reports out of .csv files.
Input - CSV files
Output - HTML reports
'''
import cairoplot
import copy
import csv
import gettext
import markup
import os
import shutil
import sys
import utils
from glob import glob
from os import path, access, R_OK, W_OK


gettext.install('log_analysis_report_generator', unicode=1)


report_csv_file_map = {'ServiceLevelReport': '_index.csv',
                        'NovaAPIService': '_nova-api.csv',
                        'NovaSchedulerService': '_scheduler.csv',
                        'NovaComputeService': '_compute.csv',
                        'NovaNetworkService': '_network.csv'}


class HTMLReportGenerator:
    IMG_WIDTH = 800
    IMG_HEIGHT = 600

    def __init__(self, test_start_ms, reports_dir):
        self.config = utils.PerfAnalyzerConfig()
        self.source_dir = os.path.join(self.config.result_file_dir,\
                                        test_start_ms)
        if not path.exists(self.source_dir) or\
            not access(self.source_dir, R_OK):
            print _("Specified source_dir '%s' does not exist or insufficient"\
                  "permissions accessing the directory.") % self.source_dir
            sys.exit(0)
        self.reports_dir = reports_dir
        self.h1_style = "font-family:Verdana,sans-serif; font-size:18pt; "\
                        "color:rgb(96,0,0)"
        self.h2_style = "font-family:Verdana,sans-serif; font-size:16pt; "\
                        "color:rgb(96,0,0)"
        self.a_style = "text-decoration:none; font-family:Verdana,sans-serif;"\
                       " font-size:8pt; margin-right: 20px"
        self.table_style = "font-family:Verdana, sans-serif; text-align:left"

    def _fetch_csv_files_from_source_dir(self):
        """
        Fetch the csv files from source_dir.
        """
        csv_files = glob(path.join(self.source_dir, "*.csv"))
        if len(csv_files) == 0:
            print _("No csv files available for generating reports")
            sys.exit(0)
        return csv_files

    def _fetch_report_name(self, csv_name):
        """
        Fetch the report name from the csv file name.
        """
        for report_name, csv_str in report_csv_file_map.iteritems():
            if csv_name.endswith(csv_str):
                return report_name
        return None

    def _calculate_summary_metrics(self, metric, results_list):
        skip_field_response = {'min': '-',
                               'max': '-',
                               'avg': '-',
                               'request_count': 0}
        values = []
        for result in results_list:
            try:
                values.append(int(result[metric]))
            except ValueError:
                return skip_field_response
            except TypeError:
                return skip_field_response

        result = {'min': min(values),
                  'max': max(values),
                  'avg': sum(values) / len(values),
                  'request_count': len(values)}
        return result

    def _fetch_metrics(self, csv_fname):
        """
        Calculate the avg, min, max from the metrics.
        """
        metrics_start_column = 6
        #fetch the fields in the order to display.
        fp = open(csv_fname, 'rb')
        csv_iter = csv.reader(fp)
        headers = csv_iter.next()
        headers.remove('compute_host')
        labels = headers[metrics_start_column:]
        row1 = csv_iter.next()
        fp.close()
        #only Create Server API has instance_type parameter.
        if row1[0] == 'create':
            summary_metrics = self._fetch_summary_metrics_by_instance_type(
                                    csv_fname,
                                    labels)
        else:
            summary_metrics = self._fetch_summary_metrics(csv_fname, labels)
        return labels, summary_metrics

    def _fetch_summary_metrics(self, csv_fname, labels):
        """
        Calculate the avg, min, max from the metrics.
        """
        fp = open(csv_fname, 'rb')
        csv_iter = csv.DictReader(fp)
        metrics = []
        for row in csv_iter:
            metrics.append(row)
        fp.close()

        metrics_summary = {'min': [], 'max': [], 'avg': [], 'request_count': 0}
        for label in labels:
            summary = self._calculate_summary_metrics(label, metrics)
            metrics_summary['min'].append(summary['min'])
            metrics_summary['max'].append(summary['max'])
            metrics_summary['avg'].append(summary['avg'])
            metrics_summary['request_count'] = summary['request_count']
        return metrics_summary

    def _fetch_summary_metrics_by_instance_type(self, csv_fname, labels):
        """
        Calculate the avg, min, max from the metrics for each instance_type.
        """
        fp = open(csv_fname, 'rb')
        csv_iter = csv.DictReader(fp)
        #group the results by instance_type
        instance_type_metric_map = {}
        for row in csv_iter:
            instance_type = row['instance_type']
            if instance_type not in instance_type_metric_map:
                instance_type_metric_map[instance_type] = []
            instance_type_metric_map[instance_type].append(row)
        fp.close()

        #generate summary metrics for each instance_type.
        instance_type_metric_summary_map = {}
        for instance_type, value_dict in instance_type_metric_map.iteritems():
            type_results = {'min': [], 'max': [], 'avg': [],
                            'request_count': 0}
            for label in labels:
                result = self._calculate_summary_metrics(label, value_dict)
                type_results['min'].append(result['min'])
                type_results['max'].append(result['max'])
                type_results['avg'].append(result['avg'])
                type_results['request_count'] = result['request_count']
            instance_type_metric_summary_map[instance_type] = type_results
        return instance_type_metric_summary_map

    def _generate_graphical_summary_report(self, metrics, page, avg_png_file,
        labels):
        """
        Generate the graph of average time taken for each instance type.
        """
        avg_png_fpath = path.join(self.reports_dir, avg_png_file)
        avg_graph_data = {}
        for instance_type, graph_data in metrics.iteritems():
            key = "type-%s" % instance_type
            avg_graph_data[key] = graph_data['avg']

        cairoplot.dot_line_plot(
                    avg_png_fpath,
                    avg_graph_data,
                    self.IMG_WIDTH,
                    self.IMG_HEIGHT,
                    axis=True,
                    series_legend=True,
                    y_title="Time in ms",
                    x_title="Instance Type Summary report",
                    x_labels=labels)
        page.img(src=avg_png_file, alt="Instance Type Summary report")
        page.br()

    def _generate_tabular_summary_report(self, metrics, page, labels):
        """
        Generate a summary report csv and HTML tabular report.
        """
        csv_file = path.join(self.reports_dir, "summary_report.csv")
        csv_header = ['instance_type', 'label', 'total_requests']
        csv_header.extend(labels)
        data_rows = [csv_header, ]
        for instance_type, graph_data in metrics.iteritems():
            data = copy.copy(graph_data)
            request_count = data.pop('request_count')
            for op_type, value_list in data.iteritems():
                data_row = [instance_type, op_type, request_count]
                data_row.extend(value_list)
                data_rows.append(data_row)

        fp = open(csv_file, "w")
        csv_writer = csv.writer(fp)
        csv_writer.writerows(data_rows)
        fp.close()

        report_name = "Instance Type Summary Report"
        report_path = self.generate_tabular_html_report(report_name, csv_file)
        csv_fname = path.basename(csv_file)
        page.a("Download csv report", href=csv_fname,
               style=self.a_style)
        page.a("View csv report", href=report_path,
                style=self.a_style)
        page.a("Top", href="#top", style=self.a_style)
        page.br()

    def _generate_graph_from_metrics(self, csv_fname, page):
        """
        Generate a line graph (png file) from the available metrics.
        """
        fname_name_ext = list(path.splitext(path.basename(csv_fname)))
        avg_png_file = fname_name_ext[0] + '_average.png'

        labels, metrics = self._fetch_metrics(csv_fname)
        if 'request_count' in metrics:
            #generate ungrouped report.
            png_file = fname_name_ext[0] + '.png'
            instance_count = metrics.pop('request_count')
            alt_text = "Service Level Summary Report"
            cairoplot.dot_line_plot(
                        png_fpath,
                        metrics,
                        self.IMG_WIDTH,
                        self.IMG_HEIGHT,
                        axis=True,
                        series_legend=True,
                        y_title="Time in ms",
                        x_title="Service Level Summary Report",
                        x_labels=labels)
            page.img(src=png_file, alt=alt_text)
            page.br()
        else:
            png_file = fname_name_ext[0] + '_%s.png'
            png_fpath = path.join(self.reports_dir, png_file)
            #generate reports grouped by instance_type.
            #generate graph for average time taken for each instance type.
            self._generate_graphical_summary_report(metrics, page,
                    avg_png_file, labels)

            #generate summary csvs.
            self._generate_tabular_summary_report(metrics, page, labels)

            #generate the min-avg-max graph for each instance type.
            for instance_type, graph_data in metrics.iteritems():
                print instance_type, graph_data
                instance_count = graph_data.pop('request_count')
                alt_text = "Instance type %s summary report" % instance_type
                cairoplot.dot_line_plot(
                            png_fpath % instance_type,
                            graph_data,
                            self.IMG_WIDTH,
                            self.IMG_HEIGHT,
                            axis=True,
                            series_legend=True,
                            y_title="Time in ms",
                            x_title="Instance Type - %(instance_type)s, "\
                                    "Instance Count - %(instance_count)s" %
                                    locals(),
                            x_labels=labels)
                page.img(src=png_file % instance_type, alt=alt_text)
                page.br()

    def generate_html_report(self):
        """
        Generate the html report out of the png files created from csv.
        """
        csv_files = self._fetch_csv_files_from_source_dir()

        page = markup.page()
        page.init(title="Jenkins")
        page.h1("API Performance report", style=self.h1_style)
        page.hr()
        index = 0
        for csv_file in csv_files:
            report_name = self._fetch_report_name(csv_file)
            if report_name:
                #add the graphical report.
                page.h2(report_name, style=self.h2_style)
                if report_name == 'ServiceLevelReport':
                    self._generate_graph_from_metrics(csv_file, page)
                report_path = self.generate_tabular_html_report(report_name,
                                                                csv_file)
                if report_path:
                    #copy the csv file to reports directory.
                    shutil.copy(csv_file, self.reports_dir)
                    csv_fname = path.basename(csv_file)
                    page.a("Download csv report", href=csv_fname,
                           style=self.a_style)
                    page.a("View csv report", href=report_path,
                            style=self.a_style)
                page.a("Top", href="#top", style=self.a_style)
            page.br()

        #write the performance report html file.
        fpath = path.join(self.reports_dir, 'log_analysis_report.html')
        html = open(fpath, 'w')
        html.write(str(page))
        html.close()
        print "Generated performance report : %s" % fpath

    def _generate_table(self, page, header_list, data_iter):
        """
        Generate an HTML table from the provided iterator.
        """
        page.table(border="2", cellspacing="0", cellpadding="4", width="50%",
                   style=self.table_style)
        #write table headers
        for header in header_list:
            page.th(header)
        #write table data rows
        for item in data_iter:
            page.tr()
            for value in item:
                page.td(value)
            page.tr.close()
        page.table.close()

    def generate_tabular_html_report(self, report_name, csv_fname):
        """
        Generate the html report out of the csv files.
        """
        fname = None
        if path.exists(csv_fname) and path.isfile(csv_fname) and\
           access(csv_fname, R_OK):
            csv_iter = csv.reader(open(csv_fname, 'rb'))
            headers = csv_iter.next()

            page = markup.page()
            page.init(title="Jenkins")
            page.h1("Performance report - %s" % report_name,
                    style=self.h1_style)
            page.hr()
            self._generate_table(page, headers, csv_iter)

            #write the performance report html file.
            fname = '%s_tabular.html' % report_name
            html = open(path.join(self.reports_dir, fname), 'w')
            html.write(str(page))
            html.close()
        return fname


def main():
    if len(sys.argv) < 3:
        print _("Usage: ./log_analysis_report_generator test_start_ms "\
              "dest_dir"\
              "\ntest_start_ms: Time when test was started"\
              "\ndest_dir: Path to create the HTML report files\n")
        sys.exit(0)

    test_start_ms = sys.argv[1]
    dest_dir = sys.argv[2]
    if not path.exists(dest_dir) or not access(dest_dir, W_OK):
        print "Specified source_dir '%s' does not exist or insufficient"\
              "permissions accessing the directory." % dest_dir
        sys.exit(0)
    report_gen = HTMLReportGenerator(test_start_ms, dest_dir)
    report_gen.generate_html_report()


if __name__ == '__main__':
    main()
