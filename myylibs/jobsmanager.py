import asyncio
from typing import Callable
import background
import random
import signal
import traceback
import threading
import time

class StatusReport:
    def __init__(self, status:str, result):
        self.status = status
        self.result = result

class A:

    def long_task(self, *args, **kwargs) -> str:
        time.sleep(3)
        return str(random.randrange(0, 100000))

class Job:

    @staticmethod
    def _dummy_method(*args, **kwargs):
        print("You didn't setup the method, you dummy !")

    def __init__(
        self,
        external_reference,
        log:list[StatusReport]=None,
        args:list=None,
        kwargs:dict=None,
        iterations:int=1):
        
        self.external_reference = external_reference
        self.read_until:int = 0
        # FIXME : Generate afterwards, from the worker thread
        # In order to ensure that the memory location is
        # more friendly to that worker thread
        self.log:list[StatusReport] = [] if log == None else log
        self.args:list = [] if args == None else args
        self.kwargs:dict = {} if kwargs == None else kwargs
        self.iterations:int = iterations

    def read_next(self) -> StatusReport:
        result = None
        
        if self.progressed():
            result = self.log[self.read_until]
            self.read_until += 1
        return result

    def progressed(self) -> bool:
        return self.read_until < len(self.log)

    def execute(self, method) -> list:
        self.log.append(StatusReport("Starting", None))
        if self.iterations < 0:
            self.iterations = 0

        try:
            for _ in range(0, self.iterations):
                result = method(*self.args, **self.kwargs)
                self.log.append(StatusReport("Progress", result))
        except Exception as e:
            self.log.append(StatusReport("Failed", str(e)))
            print(e)
        self.log.append(StatusReport("Finished", None))
        return self.log





class JobQueue:

    def report_job_started(self, job:Job, report:StatusReport):
        print("Job %s started !" % [str(job.external_reference)])

    def report_job_done(self, job:Job, report:StatusReport):
        print("Job %s is done !" % [str(job.external_reference)])

    def report_job_progress(self, job:Job, report:StatusReport):
        print("Job %s progress : %s" % (str(job.external_reference), str(report.result)))

    def report_job_failed(self, job:Job, report:StatusReport):
        print("Job %s failed :C" % (str(job.external_reference)))

    def is_done_report(self, report:StatusReport) -> bool:
        status = report.status
        return status == "Finished" or status == "Failed"

    def _current_job_done(self):
        self.current_job = None

    def handle_report(self, job:Job, report:StatusReport):
        if job == None or report == None:
            print("Called handle_report with None values !")
            return

        if not self.report_handlers:
            print("Report handlers are not configured")
            return

        status = report.status

        if not status in self.report_handlers:
            print("Can't handle status report of type %s" % (status))
            return

        try:
            self.report_handlers[status](job, report)
        except Exception as e:
            print("Something went wrong when trying to handle report type %s" % (status))
            print(traceback.print_exception(e))

        if self.is_done_report(report):
            self._current_job_done()

    @background.task
    def poll_jobs(jobs: list[Job], state:list[bool], worker_factory:Callable, worker_method:Callable):

        try:
            worker = worker_factory()
            work_method = worker_method(worker)
        except Exception as e:
            traceback.print_exception(e)
            return

        while state["queue_running"]:
            if len(jobs) > 0:
                print("Got a job !")
                current_job:Job = jobs.pop(0)
                current_job.execute(work_method)
                print("Job done")
            else:
                time.sleep(1)

    def __init__(self, worker_factory:Callable, worker_method:Callable):
        self.current_job:Job = None
        self.to_do:list[Job] = []
        self.in_progress:list[Job] = []
        self.running_state = {"queue_running": True}
        self.report_handlers = {
            "Starting": self.report_job_started,
            "Progress": self.report_job_progress,
            "Finished": self.report_job_done,
            "Failed": self.report_job_failed
        }
        JobQueue.poll_jobs(self.in_progress, self.running_state, worker_factory, worker_method)

    

    def add_jobs(self, jobs:list[Job]):
        self.to_do.extend(jobs)
    
    def add_job(self, job:Job):
        self.to_do.append(job)

    def _filter_out_jobs_list(self, filter_method:Callable, job_list:list[Job]):
        to_remove = []
        try:
            for job in job_list:
                to_remove.append(filter_method(job))
            for i in range(len(to_remove)-1, -1, -1):
                job_list.pop(i)
        except:
            return

    def filter_out_jobs(self, filter_method:Callable):
        self._filter_out_jobs_list(filter_method, self.to_do)
        self._filter_out_jobs_list(filter_method, self.in_progress)

    def _job_to_do(self):
        return self.to_do

    def _job_running(self):
        return self.current_job != None

    def _start_next_job_if_possible(self) -> bool:
        if not self._job_to_do():
            return False
        
        if self._job_running():
            return False
        
        self.current_job = self.to_do.pop(0)
        self.in_progress.append(self.current_job)
        return True
    
    def _bailing_out(self):
        self.running_state["queue_running"] = False

    async def main_task(self):
        while True:
            try:
                if self._job_running():
                    if self.current_job.progressed():
                        current_progress:StatusReport = self.current_job.read_next()
                        self.handle_report(self.current_job, current_progress)
                    else:
                        await asyncio.sleep(1)
                        continue
                else:
                    if not self._start_next_job_if_possible():
                        await asyncio.sleep(2)
            except KeyboardInterrupt:
                self._bailing_out()
                return
            except Exception as e:
                traceback.print_exception(e)
                self._bailing_out()
                return


