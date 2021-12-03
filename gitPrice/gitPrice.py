from argparse import RawTextHelpFormatter
from datetime import datetime
from typing import Any, Optional
import argparse
import subprocess
import sqlite3
import sys
import time

TIME_DIFF = 60 * 60 * 2
DEBUG_BYTE = 0

def byte_to_bits(byte):
  byte = bin(byte).lstrip('-0b')
  byte = ("0" * (8 - len(byte))) + byte
  return byte

def mIndex(data: str, needle: str) -> list[int, ...]:
  return [i for i, x in enumerate(data) if x == needle]

def debug(data: str, cByte: int) -> None:
  byte = mIndex(byte_to_bits(DEBUG_BYTE), '1')
  cByte = mIndex(byte_to_bits(cByte), '1')
  for x in cByte:
    if not x in byte:
      return None
  print(data)

def execute(cur: sqlite3.Cursor, sql: str, subs: Optional[tuple[Any, ...]] = None) -> sqlite3.Cursor:
  if subs is None:
    data = cur.execute(sql)
  else:
    data = cur.execute(sql, subs)
  cur.connection.commit()
  return data

def readCommand(cmd: str) -> str:
  data = subprocess.check_output(cmd)
  data = data.replace(b'\x00', b'')
  data = data.replace(b'\xff', b'')
  data = data.replace(b'\xfe', b'')
  data = data.replace(b'\r', b'')
  data = data.decode('utf8')
  debug(data, 8)
  data = data.split('\n')
  return data

def gitPrice(args) -> int:
  if args.convert:
    try:
      dt = datetime.strptime(args.convert, "%a %b %d %H:%M:%S %Y %z")
      print(f"Unix Timestamp: {round(time.mktime(dt.timetuple()))}")
    except ValueError:
      print(f"The timestamp '{args.convert}' does not match the expected format of '%a %b %d %H:%M:%S %Y %z'")
    return 0
  if args.after is None:
    args.after = 0
  if args.pH is None:
    TIME_COST = 10 # per hour
    LINE_COST = 0.05
  else:
    TIME_COST = args.pH
    LINE_COST = (args.pH * 0.005)
  if args.pL is None:
    LINE_COST = 0.05 # per line
  else:
    LINE_COST = args.pL

  # END ARGS PARSING 

  conn = sqlite3.connect(':memory:')
  cur = conn.cursor()
  execute(cur, 'CREATE TABLE "commits" ("commit" TEXT PRIMARY KEY, "author" TEXT, "timestamp" INT);')
  log = readCommand("git --no-pager log")

  cCommit = {}

  for line in log:
    if 'commit' in line[0:6]:
      if cCommit != {}:
        debug(cCommit, 8)
        execute(cur, "INSERT INTO commits VALUES (?, ?, ?)", (cCommit['name'], cCommit['author'], cCommit['timestamp']))
        cCommit = {}
      data = line.split()
      cCommit['name'] = data[1]
    elif 'Author:' in line[0:7]:
      data = line.split(' ')
      cCommit['author'] = ' '.join(data[1:])
    elif 'Date:' in line[0:5]:
      data = line.split(' ')
      date = (' '.join(data[1:])).strip()
      dt = datetime.strptime(date, "%a %b %d %H:%M:%S %Y %z")
      cCommit['timestamp'] = round(time.mktime(dt.timetuple()))

  if cCommit != {}:
    debug(cCommit, 8)
    debug("LAST", 8)
    execute(cur, "INSERT INTO commits VALUES (?, ?, ?)", (cCommit['name'], cCommit['author'], cCommit['timestamp']))
    cCommit = {}

  last_timestamp = 0
  last_commit = ""
  total_time = 0
  total_lines = 0
  pay = 0
  for commit in cur.execute('SELECT * FROM commits WHERE author=? ORDER BY timestamp ASC', ([args.author])):
    name = commit[0]
    author = commit[1]
    timestamp = commit[2]
    if timestamp < args.after:
      pass
    elif (timestamp - last_timestamp) > TIME_DIFF:
      if last_commit != "":
        debug("\n", 2)
        debug(f"{last_commit} {name}", 6)
        debug(f"{timestamp} - {last_timestamp} = {timestamp - last_timestamp} > {TIME_DIFF}", 2)
        diff = readCommand(f"git --no-pager diff {last_commit} {name}")
        lines = 0
        for line in diff:
          if line[0:3] == "+++":
            continue
          elif line[0:1] == "+" and len(line) > 1:
            lines += 1
        total_lines += lines
        pay += lines * LINE_COST
        debug(f"{lines=}", 2)
        debug(f"pay={lines * LINE_COST}", 2)
    else:
      debug("\n", 1)
      debug(f"{last_commit} {name}", 5)
      t = (timestamp - last_timestamp) / (60 * 60)
      total_time += t
      pay += t * TIME_COST
      debug(f"time={t}", 1)
      debug(f"pay={t * TIME_COST}", 1)

    last_timestamp = timestamp
    last_commit = name
  pay = round(pay, 2)
  total_time = round(total_time, 4)
  print("\nTotals:\n")
  print(f"{pay=}")
  print(f"{total_time=}")
  print(f"{total_lines=}")

  conn.close()

  return 0

def main() -> int:
  parser = argparse.ArgumentParser(description='Calculates Payable Time based off git repo.', formatter_class=RawTextHelpFormatter)
  parser.add_argument('--author', type=str, required=('--convert' not in sys.argv), help='Author being calculated.')
  parser.add_argument('--convert', type=str, help='Converts Git Date to timestamp.')
  parser.add_argument('--after', type=int, help='Will calculate the prices from after this timestamp.')
  parser.add_argument('--pH', type=int, help='The price per hour.\nDefault is 10 hours.')
  parser.add_argument('--pL', type=int, help='The price per line.\nDefault is 0.5%% of the price per hour.')
  parser.add_argument('-v', type=int, default=0, help='''Verbosity.  Uses binary to toggle different outputs.
00000001 (1) Display pay breakdown for hourly commits.
00000010 (2) Display pay breakdown for per line commits.
00000100 (4) Display commit hashes for breakdowns displayed.''')
  args = parser.parse_args()
  global DEBUG_BYTE
  DEBUG_BYTE = args.v
  return gitPrice(args)

if __name__ == "__main__":
  raise SystemExit(main())

