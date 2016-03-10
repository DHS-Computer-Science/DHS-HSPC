import time, os
import shutil, re
import mysql.connector
from io import StringIO
from watchdog.events import PatternMatchingEventHandler

class SubmissionWatcher(PatternMatchingEventHandler):
  patterns = ["*.zip"]

  def __init__(self, sql, args, q, staging_dir):
    PatternMatchingEventHandler.__init__(self)
    self.sql         = sql
    self.subs_table  = args['subs_table']
    self.team_table  = args['team_table']
    self.queue       = q
    self.staging_dir = staging_dir

  def on_created(self, event):
    self.cursor = self.sql.cursor()
    #self.process(event)
    file_name = os.path.basename(event.src_path)
    path_name = os.path.join(self.staging_dir, file_name)

    shutil.move(event.src_path, path_name)

    #get 8 char hash (generated by the Submission Program) from file name
    basename   = re.search('(.{8})\\.zip$', file_name).group(1)

    info = {'attempts':0}
    query = 'SELECT * FROM {} WHERE submission_name = \'{}\''
    while len(info) == 1:
      self.cursor.execute(query.format(self.subs_table, basename))
      time.sleep(2)
      for row in self.cursor:
        info.update(dict(zip(self.cursor.column_names, row)))

    query = 'SELECT team_name FROM {} WHERE team_id = \'{}\''
    self.cursor.execute(query.format(self.team_table, info['team_id']))
    for row in self.cursor:
      info['team_name'] = row[0]

    query = 'SELECT * FROM {} ' \
            'WHERE problem_id = \'{}\' AND team_id = \'{}\' AND time <= \'{}\''
    self.cursor.execute(query.format(self.subs_table, info['problem_id'],
                                     info['team_id'], info['time']))

    info['attempts'] = self.cursor._rowcount+1

    for i in info.keys():
      try:
        info[i] = info[i].decode('utf-8')
      except:
        pass

    self.cursor.close()
    self.queue.put((path_name, info))
