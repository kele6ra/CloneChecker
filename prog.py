import git
import os
import matplotlib.pyplot as plt
import numpy as np
import glob
import shutil
import csv
import re
import configparser

import networkx as nx

from bs4 import BeautifulSoup
from concurrent import futures

import sys

config = configparser.ConfigParser()
config.read('config.cfg')

sys.setrecursionlimit(config.getint('Settings','recursion_limit'))

DOWNLOAD_DATA = config.getboolean('Settings','download_data')
LIMIT = config.getfloat('Settings','limit')
BUNDLE_FILENAME = config.get('Settings','bundle_filename')

from pathlib import Path


def svgReplace(filename, links):
  with open(filename, 'r') as file:
    filedata = file.read()


  for user in links:
    filedata = filedata.replace(f'>{user}<', f'>{links[user]}<')

  # Write the file out again
  with open(filename, 'w') as file:
    file.write(filedata)


def concat_files(dir_path, file_pattern):
    res = ''

    for path in Path(dir_path).rglob(file_pattern):
      with open(path, "r", encoding='utf-8', errors='ignore') as infile:
          res += infile.read()
    return res

def concatenateAll(path, userList, taskName, pattern):
  newUserList = []
  for user in userList:
    currentPath = os.path.join(path, user, taskName)
    nodeModules = os.path.join(currentPath, 'node_modules')
    docDir = os.path.join(currentPath, 'doc')
    testDir = os.path.join(currentPath, 'test')
    
    if os.path.exists(nodeModules):
      shutil.rmtree(nodeModules)

    if os.path.exists(docDir):
      shutil.rmtree(docDir)

    if os.path.exists(testDir):
      shutil.rmtree(testDir)

    if os.path.exists(currentPath):
      print(f'current path = {currentPath}')
      text = concat_files(currentPath, pattern)
      if len(text) > 0:
        newUserList.append(user)
        with open(os.path.join(currentPath, BUNDLE_FILENAME), 'w', encoding='utf-8') as f:
          f.write(text)
  return newUserList


def detectComponents(graph, key, detected):
  for v in graph[key]:
    if not v in detected:
      detected.add(v)
      detectComponents(graph, v, detected)


def getPercent(value):
  return f'{value * 100}%'

def get_jaccard_sim(a, b):
    c = a.intersection(b)

    if len(a) + len(b) - len(c) == 0:
      return 0

    return float(len(c)) / (len(a) + len(b) - len(c))


def parseScores(path):
  pageText = open(path, 'r').read()
  page = BeautifulSoup(pageText, 'html.parser')
  
  users = set()

  for user in page.find_all('tr'):
    if user.has_attr('data-row-key'):
      users.add(user.get('data-row-key'))

  return list(users)

class UserTask:
  def __init__(self, userName, taskName, localPath, checkPath):
    self.userName = userName
    self.taskName = taskName
    self.localPath = localPath
    self.checkPath = checkPath
    self.cash = None

    self.success = self._cloneProject()

  def _cloneProject(self):
    self.downloadPath = os.path.join(self.localPath, self.userName)
    self.pathToFile = os.path.join(self.downloadPath, self.taskName, self.checkPath)

    self.gitUrl = f'https://github.com/{self.userName}/{self.taskName}'
    self.urlToFile = f'{self.gitUrl}/blob/master/{self.checkPath}'

    if not DOWNLOAD_DATA:
      return self.isSuccess()

    try:
      os.makedirs(self.downloadPath)
    except OSError:
      print ("Creation of the directory %s failed" % self.downloadPath)

    if not os.listdir(self.downloadPath):
      try:
        git.Git(self.downloadPath).clone(self.gitUrl)
      except git.exc.GitError:
        return False

    return self.isSuccess()

  def isSuccess(self):
    return os.path.exists(self.pathToFile)

  def getText(self):
    if self.cash:
      return self.cash
    

    with open (self.pathToFile, "r", encoding='utf-8', errors='ignore') as f:
      self.cash = f.read()
      return self.cash
  
  def check(self, value):
    text = self.getText()

    regexp = re.compile(value)
    return regexp.search(text)
    #return self.getText().find(value) != -1

class TaskHandler:
    def __init__(self, length):
        self.usersTasks = {}
        self.iterator = 0
        self.length = length

    def __call__(self, r):
        self.iterator+=1
        print(f'Downloaded: {self.iterator}/{self.length}')
        if r.result().success:
          self.usersTasks[r.result().userName] = r.result()
          print(f'Success for {r.result().userName}')

class UserList:
  def __init__(self, users, taskName, localPath, checkPath):
    self.taskName = taskName
    self.localPath = localPath
    self.checkPath = checkPath
    self.usersTasks = {}
    self.setCash = dict()
    
    self._createUserTasks(users)

  def updateUserList(self, userList):
    for user in list(self.usersTasks):
      if not user in userList:
        del self.usersTasks[user]

  def _createUserTasks(self, users):
    tasks_handler = TaskHandler(len(users))
    with futures.ProcessPoolExecutor() as pool:
      for user in users:
        future_result = pool.submit(UserTask, user, self.taskName, self.localPath, self.checkPath)
        future_result.add_done_callback(tasks_handler)
    self.usersTasks = tasks_handler.usersTasks
  
  def compare(self, userNameA, userNameB):
    userA = self.usersTasks[userNameA]
    userB = self.usersTasks[userNameB]

    if not userNameA + self.checkPath in self.setCash:
      textA = userA.getText()
      if not textA:
        return False
      self.setCash[userNameA + self.checkPath] = set(textA.split())
    
    if not userNameB + self.checkPath in self.setCash:
      textB = userB.getText()
      if not textB:
        return False
      self.setCash[userNameB + self.checkPath] = set(textB.split())


    return get_jaccard_sim(self.setCash[userNameA + self.checkPath], self.setCash[userNameB + self.checkPath])

  def cloneCheck(self, userA, userB, thresholdValue):
    res = self.compare(userA, userB)

    if not res:
      return False

    return res

  def createResultRow(self, userA, userB, cloneCheckResult):
    return f'Path: {self.checkPath}\tUser: {userA} <-> {userB}\tSimilarity: {cloneCheckResult * 100}%'

  def checkByValue(self, value):
    res = []

    with open('new-Function.txt', 'w') as f:
      for user in self.usersTasks:
        if self.usersTasks[user].check(value):
          res.append(user)
          f.writelines([f'User: {user}\n\n', self.usersTasks[user].getText()])
          f.write('\n\n\n------------------------------------------------------\n\n\n')
    


    return res

  def crossCheck(self):
    values = []
    file = open('crosscheck.txt', 'w')

    graph = nx.Graph()
    graphCsv = dict()

    i = 1

    for userA in self.usersTasks:
      print(f'{i/len(self.usersTasks)*100}%')
      self.checkUser(userA, values, graph, graphCsv, file)
      i += 1
      file.flush()

    file.close()

    plt.hist(values, bins=1000)
    plt.show()

    nx.write_graphml(graph, 'graph.graphml')

    with open('results.csv', 'w', newline='') as f:
      writer = csv.writer(f, delimiter=',')
      writer.writerow(['Number', 'User', 'Url', 'Data'])

      i = 1
      
      order = self.getComponents(graphCsv)

      for component in order:
        for node in component:
          line = [i, node, self.usersTasks[node].urlToFile]
          
          data = ''
          for user in graphCsv[node]:
            data += f'{user}: {graphCsv[node][user]}; '
          i += 1
          line.append(data)
          writer.writerow(line)
        writer.writerow('')
  
  def getLinks(self):
    res = dict()
    for task in self.usersTasks:
      res[task] = f'<a target="_blank" href="{self.usersTasks[task].urlToFile}">{task}</a>'
    return res

  def getComponents(self, graph):
    allComponents = set()
    res = []

    for i in list(graph):
      if not i in allComponents:
        localComponents = set()
        detectComponents(graph, i, localComponents)
        allComponents = allComponents.union(localComponents)
        res.append(localComponents)
    return res

  def checkUser(self, user, values, graph=None, graphCsv=None, file=None):
    nodes = set()

    hist = [0] * 101

    for userB in self.usersTasks:
      if user != userB:
        res = self.cloneCheck(user, userB, LIMIT)

        if res != False:
          values.append(res * 100)
        if res >= LIMIT:
          line = self.createResultRow(user, userB, res)

          if graph != None:
            if not user in graph.nodes:
              graph.add_node(user, label=user)
              graph.nodes[user]['xlink:href'] = self.usersTasks[user].urlToFile
              graphCsv[user] = dict()
            
            if not userB in graph.nodes:
              graph.add_node(userB, label=userB)
              graph.nodes[userB]['xlink:href'] = self.usersTasks[userB].urlToFile
              graphCsv[userB] = dict()

            graph.add_edge(user, userB)
            label = f'{round(res * 100)}%'
            graph.add_edge(userB, user, label=label)

            graphCsv[user][userB] = label
            graphCsv[userB][user] = label

          if file:
            file.write(line + '\n')

    return hist

if __name__ == "__main__":
  users = []

  for file in os.listdir("./scores"):
    if file.endswith(".html"):
      users += parseScores(os.path.join('.', 'scores', file))

  '''os.path.join('src', 'carbon-dating.js'),
    os.path.join('src', 'count-cats.js'),
    os.path.join('src', 'dream-team.js'),
    os.path.join('src', 'extended-repeater.js'),
    os.path.join('src', 'hanoi-tower.js'),
    os.path.join('src', 'recursive-depth.js'),
    os.path.join('src', 'transform-array.js'),
    os.path.join('src', 'vigenere-cipher.js'),
    os.path.join('src', 'what-season.js')'''

  #newUserList = concat_files('data/sovaz1997/basic-js/src', '*.js')
  
  userList = UserList(users, config.get('Settings','task_name'), os.path.join('data'), config.get('Settings','bundle_filename'))
  #userList.checkByValue(r'new Function')
  users = concatenateAll('data', users, config.get('Settings','task_name'), config.get('Settings','concat_pattern'))
  userList.updateUserList(users)
  #userList.updateUserList(userList.checkByValue(r'new Function'))
  userList.crossCheck()
  
  #links = userList.getLinks()
  #svgReplace('expression-calculator.svg', links)


