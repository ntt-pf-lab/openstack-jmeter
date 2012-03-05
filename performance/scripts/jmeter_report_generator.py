#!/usr/bin/env python

'''Script that uses JMeterPlugins CMD Command Line Tool to generate graphs out
.jtl files created by JMeter Test Plan listeners. Further it generates html
reports from the png and csv files.
Input - JTL file
Output - PNG and CSV file, HTML reports

REFER URL: http://code.google.com/p/jmeter-plugins/wiki/JMeterPluginsCMD
'''
import csv
import markup
import subprocess
import sys
from os import path, access, R_OK


plugin_class_file_map = {'AggregateReport':'aggregate_report.jtl',
			'HitsPerSecond': 'hits_per_second.jtl',
			'LatenciesOverTime':'response_times_over_time.jtl',
			'PerfMon':'perf_mon.jtl',
			'ResponseCodesPerSecond':'response_code_per_second.jtl',
			'ResponseTimesDistribution':'response_times_distribution.jtl',
			'ResponseTimesOverTime':'response_times_over_time.jtl',
			'ResponseTimesPercentiles':'response_times_percentiles.jtl',
			}
jar_path = '/home/rohit/jmeter/apache-jmeter-2.6/lib/ext/CMDRunner.jar'

png_cmd = 'java -jar %s --tool Reporter --generate-png %s.png '\
          '--input-jtl %s --plugin-type %s --width 800 --height 600'

csv_cmd = 'java -jar %s --tool Reporter --generate-csv '\
          '%s.csv --input-jtl %s --plugin-type %s'


class HTMLReportGenerator:
    def __init__(self, source_dir, reports_dir, cmd_runner=None):
	if not cmd_runner:
  	    self.cmd_runner = jar_path
	else:
            self.cmd_runner = cmd_runner 
        self.source_dir = source_dir
        self.reports_dir = reports_dir
        self.h1_style = "font-family:Verdana,sans-serif; font-size:18pt; "\
                        "color:rgb(96,0,0)"
        self.h2_style = "font-family:Verdana,sans-serif; font-size:16pt; "\
                        "color:rgb(96,0,0)"
        self.a_style = "text-decoration:none; font-family:Verdana,sans-serif;"\
                       " font-size:8pt; margin-right: 20px"
        self.table_style = "font-family:Verdana, sans-serif; text-align:left"

    def generate_png_and_csv_from_jtl(self):
        """
        Generate png and csv files for all plugin_classes whose .jtl are 
        created.
        """
        for key,value in plugin_class_file_map.items():
            fpath = path.join(self.source_dir, value)
            dpath = path.join(self.reports_dir, key)
            if path.exists(fpath) and path.isfile(fpath) and \
                access(fpath, R_OK):
                if key == 'AggregateReport':
                    # Only csv can be generated for Aggregate Report
                    csv_cmd1 = csv_cmd % (self.cmd_runner, dpath, fpath, key)
                    subprocess.check_call("%s" % csv_cmd1, shell=True)
                    continue
                png_cmd1 = png_cmd % (self.cmd_runner, dpath, fpath, key)
                subprocess.check_call ("%s" % png_cmd1, shell=True)
                csv_cmd1 = csv_cmd % (self.cmd_runner, dpath, fpath, key)
                subprocess.check_call("%s" % csv_cmd1, shell=True)

    def generate_html_report(self):
        """
        Generate the html report out of the png files created from jtl.
        """
        page = markup.page()
        page.init(title="Jenkins")
        page.h1("Performance report", style=self.h1_style)
        page.hr()
        index = 0
        for plugin,jtl in plugin_class_file_map.items():
            index += 1
            page.h2(plugin, style=self.h2_style)
            if plugin != 'AggregateReport':
                # Aggregate Report will only have tabular report link.                
                #png_path = path.join(self.reports_dir, plugin + ".png")
                png_path = plugin + ".png"
                page.img(src=png_path, alt=plugin)
            page.br()
            #generate tabular report.
            report_path = self.generate_tabular_html_report_for_plugin(plugin)
            if report_path:
                csv_fname = plugin + ".csv"
                page.a("Download csv report", href=csv_fname,
                       style=self.a_style)
                page.a("View csv report", href=report_path, style=self.a_style)
            page.a("Top", href="#top", style=self.a_style)
            page.br()
        #write the performance report html file.
        fpath = path.join(self.reports_dir, 'performance_report.html')
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

    def generate_tabular_html_report_for_plugin(self, plugin_name):
        """
        Generate the html report out of the csv files created from jtl.
        """
        fname = None
        csv_fname = path.join(self.reports_dir, plugin_name + ".csv")
        if path.exists(csv_fname) and path.isfile(csv_fname) and\
           access(csv_fname, R_OK):
            csv_iter = csv.reader(open(csv_fname, 'rb'))
            headers = csv_iter.next()
        
            page = markup.page()
            page.init(title="Jenkins")
            page.h1("Performance report - %s" % plugin_name, style=self.h1_style)
            page.hr()
            self._generate_table(page, headers, csv_iter)

            #write the performance report html file.
            fname = '%s_tabular.html' % plugin_name
            html = open(path.join(self.reports_dir, fname), 'w')
            html.write(str(page))
            html.close()
        return fname


def main():
    if len(sys.argv) < 3:
        print "Usage: ./report_generator.py source_dir dest_dir <CMDRunner.jar path>\n\
	       source_dir: Path to directory containing .jtl files\n\
               dest_dir: Path to create PNG and CSV files and HTML report file\n\
	       CMDRunner.jar path(Optional): Path to Jmeter plugin CMDRunner.jar\n"
        sys.exit(0)
    cmd_runner_path = sys.argv[3] if len(sys.argv) > 3 else None
    report_gen = HTMLReportGenerator(sys.argv[1], sys.argv[2], cmd_runner_path)
    report_gen.generate_png_and_csv_from_jtl()
    report_gen.generate_html_report()


if __name__ == '__main__':
    main()
