import json,os
PATH=os.environ['AUDIT_EVENTS']
def emit(data):
    with open(PATH,'a',encoding='utf-8') as f: f.write(json.dumps(data,default=str)+'\n')
def pytest_collectreport(report):
    if report.failed: emit(dict(kind='collection',nodeid=report.nodeid,outcome=report.outcome,longrepr=str(report.longrepr)))
def pytest_runtest_logreport(report):
    if report.when=='call' or report.failed or report.skipped:
        emit(dict(kind='test',nodeid=report.nodeid,when=report.when,type=type(report).__name__,outcome=report.outcome,context=repr(getattr(report,'context','')),longrepr=str(report.longrepr) if report.longrepr else ''))
