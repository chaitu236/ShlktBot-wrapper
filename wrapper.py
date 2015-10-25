import subprocess
import socket
import re

server_addr = ('playtak.com', 10000)
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
gameno=''

debug = True

def read_line():
  data=''
  while True:
    c = sock.recv(1)
    if c=='\n' or c=='':
      break
    else:
      data += c
  if debug:
    print 'read_line:'+data
  return data

def send(msg):
  if debug:
    print 'send:'+msg
  sock.sendall(msg+'\n')

def post_seek(size):
  send('Seek '+str(size))

def bot_to_server(move):
  move = move.strip()
  print 'bot_to_server', move
  #[T0, X]: ai move => c3
  move = move.split('move => ')[1]
  match = re.match(r'[a-h][1-8]$', move)
  if match:
    return 'P '+move.upper()
  match = re.match(r'C([a-h][1-8])$', move)
  if match:
    return 'P '+match.group(1).upper()+' C'
  match = re.match(r'S([a-h][1-8])$', move)
  if match:
    return 'P '+match.group(1).upper()+' W'

  match = re.match(r'([1-8])?([a-h])([1-8])([><\-+]$)', move)
  if match:
    fl = ord(match.group(2))
    rw = int(match.group(3))
    sym = match.group(4)
    print 'sym='+sym

    fadd=0
    radd=0
    if sym=='<':
      fadd=-1
    elif sym =='>':
      fadd=1
    elif sym =='+':
      radd = 1
    elif sym=='-':
      radd = -1

    return 'M '+chr(fl).upper()+str(rw)+' '+chr(fl+fadd).upper()+''+str(rw+radd)+' 1'

  match = re.match(r'([1-8])([a-h])([1-8])([><\-+])([1-8]+)', move)
  if match:
    stsz = int(match.group(1))
    fl = ord(match.group(2))
    rw = int(match.group(3))
    sym = match.group(4)
    stk = match.group(5)

    fadd=0
    radd=0
    if sym=='<':
      fadd=-1*len(stk)
    elif sym =='>':
      fadd=1*len(stk)
    elif sym =='+':
      radd = 1*len(stk)
    elif sym=='-':
      radd = -1*len(stk)

    msg = 'M '+chr(fl).upper()+str(rw)+' '+chr(fl+fadd).upper()+''+str(rw+radd)
    for i in stk:
      msg = msg+' '+i

    return msg
  return 'Not match'
  #ai move => Cb4
  print 'not implemented!!'

def server_to_bot(move):
  print 'server_to_bot', move
  spl = move.split(' ')
  #Game#1 P A4 (C|W)
  if spl[1] == 'P':
    stone=''
    if len(spl) == 4:
      if spl[3]=='W':
        stone='S'
      else:
        stone='C'
    print 'returning:'+stone+spl[2].lower()+':'
    return stone+spl[2].lower()

  #Game#1 M A2 A5 2 1
  elif spl[1] == 'M':
    fl1 = ord(spl[2][0])
    rw1 = int(spl[2][1])
    fl2 = ord(spl[3][0])
    rw2 = int(spl[3][1])

    dir=''
    if fl2==fl1:
      if rw2>rw1:
        dir='+'
      else:
        dir='-'
    else:
      if fl2>fl1:
        dir='>'
      else:
        dir='<'

    lst=''
    liftsize=0
    for i in range(4, len(spl)):
      lst = lst+spl[i]
      liftsize = liftsize+int(spl[i])

    #there's an ambiguity here.. is the start sq. empty??.. lets find out
    send('Game#'+gameno+' Show '+spl[2])
    msg = read_line()
    if 'Over' in msg:
      return 'Over'
    #Game#1 Show Sq [f]
    origsq = len(msg.split(' ')[3])-2
    prefix=liftsize
    if origsq==0 and liftsize==1:
      prefix=''
    if lst=='1':#this is a bug in bot
      lst=''

    print 'returning:'+str(prefix)+spl[2].lower()+dir+lst+":"
    return str(prefix)+spl[2].lower()+dir+lst

def is_white_turn(move_no):
  return (move_no%2)==0

def read_game_move(game_no):
  while(True):
    msg = read_line()
    if(msg.startswith('Game#'+game_no)):
      return msg

def read_bot_move(p):
  while(True):
    move = p.stdout.readline()
    print 'read_bot_move:', move
    if 'ai move' in move:
      return move
    elif 'Game over' in move:
      return ''

  print 'something wrong!'

def bot(no, is_bot_white):
  p = subprocess.Popen('mono TakConsole.exe',
              shell=True, bufsize=0, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
  p.stdin.write('interactive\n')
  p.stdin.flush()
  print 'color', no, 'iswhite?', is_bot_white

  move_no = 0
  while(True):
    #read from bot, write to server
    if is_white_turn(move_no) == is_bot_white:
      if move_no == 0 or move_no ==1:
        p.stdin.write('ai on\n')
        p.stdin.flush()

      print 'reading bot move'
      move=read_bot_move(p)
      if move=='':
        break;
      send('Game#'+no+' '+bot_to_server(move))
    #read from server, write to bot
    else:
      print 'reading game move'
      msg = read_game_move(no)
      print 'readgm', msg
      print 'Over in '+str('Over' in msg)
      if 'Abandoned' in msg or 'Over' in msg:
        break;
      #if 'R-0' in msg or '0-R' in msg or 'F-0' in msg or '0-F' in msg or '1/2-1/2' in msg:
      #  break; 
      msg = server_to_bot(msg)
      if msg == 'Over':
        break;
      p.stdin.write(msg+'\n')
      p.stdin.flush()

    move_no = move_no+1
  print 'here'
  p.stdin.write('\n\n')
  p.stdin.flush()

def run():
  #for i in range(10)
  send('Name ShlktBot')
  i=1
  while(read_line().startswith("Name?")==True):
    send('Name ShlkBot'+str(i))
    i=i+1

  post_seek(5)
  msg=read_line()
  while(msg.startswith("Game Start")!=True):
    msg=read_line()

  #Game Start no. size player_white vs player_black yourcolor
  print 'game started!'+msg
  spl = msg.split(' ')
  global gameno
  gameno = spl[2]
  print 'gameno='+gameno
  bot(gameno, spl[7]=="white")

if __name__ == "__main__":
  sock.connect(server_addr)
  read_line()
  read_line()
  while(True):
    try:
      run()
    finally:
      pass