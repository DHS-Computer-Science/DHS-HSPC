import time, os
import shutil, re
import mysql.connector
from io import StringIO #this may not be needed
from watchdog.events import PatternMatchingEventHandler

class SubmissionWatcher(PatternMatchingEventHandler):
  patterns = ["*"] #wait for all types of files

  def __init__(self, sql, args, q, staging_dir):
    PatternMatchingEventHandler.__init__(self)
    self.sql         = sql
    self.subs_table  = args['subs_table']
    self.team_table  = args['team_table']
    self.queue       = q
    self.staging_dir = staging_dir

  def on_created(self, event):
    if not event.is_directory:#if a dir is created...
      return
    self.cursor = self.sql.cursor()
    #self.process(event)
    file_name = os.path.basename(event.src_path)         #I don't even know why
    path_name = os.path.join(self.staging_dir, file_name)# these lines are here

    shutil.move(event.src_path, path_name)

    #get 8 char hash (generated by the Submission Program) from file name
    basename   = re.search('(.{8})/?$', file_name).group(1)

    info = {'attempts':0}#set number of attempts to zero?
    query = 'SELECT * FROM {} WHERE submission_name = \'{}\''
    while len(info) == 1:#wait for mysql to have ? appear(should'a used pymysql)
      self.cursor.execute(query.format(self.subs_table, basename))
      time.sleep(2)#wait for two seconds? Sure why not
      for row in self.cursor:
        info.update(dict(zip(self.cursor.column_names, row)))#some hack

    #I think this gets the team name
    query = 'SELECT team_name FROM {} WHERE team_id = \'{}\''
    self.cursor.execute(query.format(self.team_table, info['team_id']))
    for row in self.cursor:
      info['team_name'] = row[0]

    #num of attempts
    query = 'SELECT * FROM {} ' \
            'WHERE problem_id = \'{}\' AND team_id = \'{}\' AND time <= \'{}\''
    self.cursor.execute(query.format(self.subs_table, info['problem_id'],
                                     info['team_id'], info['time']))
    info['attempts'] = self.cursor._rowcount

    for i in info.keys():#attempt to turn everyone in the dict into a string
      try:               # on the note of everyone google:
        info[i] = info[i].decode('utf-8') # "oldman everyone", great movie(imho)
      except:
        pass #ignore error, they can't be serious... can they?

    self.cursor.close()
    self.queue.put((path_name, info))#add submission info to queue
