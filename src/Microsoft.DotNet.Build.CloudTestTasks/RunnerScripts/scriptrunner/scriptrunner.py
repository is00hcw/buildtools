#!/usr/bin/env py
import os.path
import re

import helix.depcheck
import helix.logs
import helix.proc
import helix.saferequests

from helix.cmdline import command_main
from helix.io import fix_path
from helix_test_execution import HelixTestExecution

log = helix.logs.get_logger()


def main(args=None):
    def _main(settings, optlist, args):
        """
        Usage::
            xunitrunner
                [--config config.json]
                [--setting name=value]
                --script
                [--args arg1 arg2...]
        """
        optdict = dict(optlist)
        log.info("BuildTools Helix Script Runner v0.1 starting")
        if '--args' in optdict:
            script_arguments = optdict['--args']
            log.info("Script Arguments:"+script_arguments)

        script_to_execute = optdict['--script']

        test_executor = HelixTestExecution(settings)

        unpack_dir = fix_path(settings.workitem_payload_dir)

        exec_dir = os.path.join(fix_path(settings.workitem_working_dir), 'execution')

        execution_args = [os.path.join(unpack_dir, script_to_execute)] + args

        return_code = helix.proc.run_and_log_output(
            execution_args,
            cwd=unpack_dir,
            env=None
        )
        event_client = helix.event.create_from_uri(settings.event_uri)
        results_location = os.path.join(exec_dir, 'testResults.xml')
        if os.path.exists(results_location):
            log.info("Uploading results from {}".format(results_location))

            with file(results_location) as result_file:
                test_count = 0
                for line in result_file:
                    if '<assembly ' in line:
                        total_expression = re.compile(r'total="(\d+)"')
                        match = total_expression.search(line)
                        if match is not None:
                            test_count = int(match.groups()[0])
                        break

            result_url = test_executor.upload_file_to_storage(results_location, settings)
            log.info("Sending completion event")
            event_client.send(
                {
                    'Type': 'XUnitTestResult',
                    'WorkItemId': settings.workitem_id,
                    'WorkItemFriendlyName': settings.workitem_friendly_name,
                    'CorrelationId': settings.correlation_id,
                    'ResultsXmlUri': result_url,
                    'TestCount': test_count,
                }
            )
        else:
            log.error("Error: No exception thrown, but XUnit results not created")
            test_executor.report_error(settings, failure_type="XUnitTestFailure")

        return return_code

    return command_main(_main, ['script='], args)

if __name__ == '__main__':
    import sys
    sys.exit(main())

helix.depcheck.check_dependencies(__name__)
