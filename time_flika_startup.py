import os
import datetime
from logging import DEBUG

def get_log_file():
    LOG_DIR = os.path.join(os.path.expanduser("~"), '.FLIKA', 'log')
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    existing_files = os.listdir(LOG_DIR)
    existing_files = [f for f in existing_files if 'flikalog.' in f]
    if len(existing_files) == 0:
        log_idx = 0
    else:
        log_idx = existing_files[-1].split('.')[1]
        try:
            log_idx = int(log_idx)
        except ValueError:
            log_idx = 0
    LOG_FILE = os.path.join(LOG_DIR, 'flikalog.{}.log'.format(log_idx))
    return LOG_FILE

def get_log_steps():
    LOG_FILE = get_log_file()
    lines = []
    for line in reversed(list(open(LOG_FILE))):
        text = line.rstrip()
        if 'DEBUG' in text and ('Started' in text or 'Completed' in text):
            lines.append(text)
        if "Started 'reading __init__.py'" in text:
            break
    lines = lines[::-1]
    steps = get_steps(lines, 0)
    return steps

class Step(object):
    def __init__(self, name, time, children):
        self.name = name
        self.time = time
        self.children = children
    def __repr__(self):
        t = "{:.3f} s".format(self.time.seconds + self.time.microseconds/1000000)
        return "{} ({})".format(self.name, t)
    def repr_w_children(self, prefix=''):
        repr = prefix + self.__repr__() + '\n'
        for child in self.children:
            repr += child.repr_w_children(prefix=prefix + '- ')
        return repr

def get_steps(lines, idx, parent_step=None):
    steps = []
    while idx < len(lines):
        line = lines[idx]
        step_name = line.split("'")[1]
        if line.split(' - DEBUG - ')[1][:7] == 'Started':
            t_i = datetime.datetime.strptime(line.split(' - DEBUG')[0], "%Y-%m-%d %H:%M:%S,%f")
            substeps, t_f, idx = get_steps(lines, idx+1, parent_step=step_name)
            steps.append(Step(step_name, t_f - t_i, substeps))
        if line.split(' - DEBUG - ')[1][:9] == 'Completed':
            try:
                assert step_name == parent_step
            except AssertionError:
                print(AssertionError)
                print("Step name: '{}', parent_step: '{}'".format(step_name, parent_step))
            t_f = datetime.datetime.strptime(line.split(' - DEBUG')[0], "%Y-%m-%d %H:%M:%S,%f")
            return steps, t_f, idx+1
    return steps

if __name__ == '__main__':
    from flika import *
    start_flika()
    assert logger.level == DEBUG
    steps = get_log_steps()
    for step in steps:
        print(step.repr_w_children())




