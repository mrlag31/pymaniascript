from enum import Enum, auto

class ReportType (Enum):
    FATAL_ERROR = auto()
    ERROR = auto()
    WARNING = auto()

FATAL_ERROR = ReportType.FATAL_ERROR
ERROR = ReportType.ERROR
WARNING = ReportType.WARNING

class Report:
    
    def __init__ (self, filename, level, offender, msg):
        self.filename, self.level, self.offender, self.msg = filename, level, offender, msg
    
    def __str__ (self):
        return f'{self.filename} ({self.level.name}) {self.offender.start} - {self.offender.end}: {self.msg}'

def reporter (filename):
    def report_gen (level, offender, msg):
        return Report(filename, level, offender, msg)
    return report_gen
