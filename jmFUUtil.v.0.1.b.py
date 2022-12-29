#!/usr/bin/env python2

from itertools import izip
import os
import shutil
import sys
import datetime
import traceback
import argparse

defaultChunkSize = 16384 # 16KiB
logMsgDateTimeFormat = '%H:%M:%S, %d.%m.%Y'
fileTimeStampFormat = '%Y.%m.%d-%H.%M.%S-%f'

progName = 'jmFUUtil'
progVersion = '0.1.b'

progDescription = ''' 
"Jolly Mixer -- File Uroboros", aka "File Wheel ..."
... realizes a Vernam-like cipher ...
... ... ...
'''
progCopyright = '''
 Copyright (c) 2022, Denis I. Markov aka MariK
 < dm DOT marik DOT 230185 AT gmail DOT com >
 < t DOT me / dm UNDERSCORE MariK >
 All rights reserved.
 
 This code is multi-licensed under:  
 * CC BY-SA version 4.0 or later;
 * GNU GPL version 3 or later;
 * GNU Lesser GPL version 2.1 or later.
 Verbatim copy of any of these licenses can be found in the Internet on the corresponding resources.
 You are allowed to choose any of or any number of these licenses on your taste. ;-)
 
 The author preserves the right for his own to change the license to MIT License 
 or any other permissive license at any moment he wants.
  * The term "permissive license" is used here in the exactly same sense as the term 
 "lax permissive license" has been used in the article 'License Compatibility and Relicensing' 
 by Richard Stallman [ https://www.gnu.org/licenses/license-compatibility.en.html ].
 '''
# *** ----------------------------------------------------------------------------------------------
def ordbNOT(x):
  '''
  nx = ordbNOT(x) 
  Perform Bitwise NOT operation on an ASCII code.
  Expects "x" to be a CORRECT character's ASCII code.
  Returns also CORRECT character's ASCII code, ready 
  to be converted back to the ASCII character by chr().
  '''
  return (~x)%256

# *** ----------------------------------------------------------------------------------------------
def sxor(s1,s2):
  '''
  sOut = sxor(s1,s2)
    * convert strings s1 and s2 to a list of character pair tuples;
    * go through each tuple, converting them to ASCII code (ord);
    * perform XOR (Bitwise Exclusive Or) on the ASCII codes;
    * then convert the result back to ASCII (chr);
    * merge the resulting array of characters to the string sOut.
  '''
  #return ''.join(chr(ord(a) ^ ord(b)) for a,b in zip(s1,s2))
  return ''.join(chr(ord(a) ^ ord(b)) for a,b in izip(s1,s2))

# *** ----------------------------------------------------------------------------------------------
def snotxor(s1,s2):
  '''
  sOut = snotxor(s1,s2)
    * convert strings s1 and s2 to a list of character pair tuples;
    * go through each tuple, converting them to ASCII code (ord);
    * perform XOR (Bitwise Exclusive Or) on the ASCII codes, 
      returning also an ASCII code as a result;
    * perform Bitwise NOT on the result of the previous step;
    * then convert the result back to ASCII (chr);
    * merge the resulting array of characters to the string sOut.
  '''
  return ''.join(chr( ordbNOT(ord(a) ^ ord(b)) ) for a,b in izip(s1,s2))

# *** ----------------------------------------------------------------------------------------------
def snot(s1):
  ''' sOut = snot(s1)
    * convert the s1 string to a list of characters;
    * go through each character, converting them to ASCII code (ord);
    * perform Bitwise NOT on the ASCII code;
    * then convert the result back to ASCII (chr);
    * merge the resulting array of characters to the string sOut.
  '''
  return ''.join(chr(ordbNOT(ord(a))) for a in s1)

# *** ==============================================================================================
def fixOffset(filePath, offset):
  '''
  fxdOffset = fixOffset(filePath, offset)
  For a given file (denoted as filePath) converts the "extended" (in round-robin sense)
  offset value to the "normal" offset value -- such as that can be used, for example, 
  by FileObj.seek() method. Returns the "normal" offset value.
  Both fxdOffset and offset are in bytes.
  '''
  fSize = os.path.getsize(filePath)
  offset = int(offset)
  return offset % fSize

# *** ==============================================================================================
def roundRead(fObj, bNum):
  '''
  str = roundRead(fObj, bNum)
  Read ANY given number of bytes (bNum) from already openned fObj.
  The read operation is performed in round-robin manner, i.e. if the file size is less than bNum
  the read operation continues from the beginning of the file and so on. Return string of read bytes.
  * It is assumed that fObj is a correctly openned File-object in binary read-only mode 
  having pointer set up to correct offset position 
  by "fObj = open(fPath, 'rb')" and "fObj.seek(offset, 0)", respectively.
  !!! It is STRONGLY recomended to run this function inside "with"-Statement Context only !!!
  '''
  s = ''
  bLeft = bNum
  while True:
    s += fObj.read(bLeft)
    bLeft = bNum - len(s)
    if bLeft == 0:
      break
    else:
      fObj.seek(0, 0)
  return s
  
# *** ----------------------------------------------------------------------------------------------

def jm_write(ofObj, **kwopts):
  '''
  jm_write(outFileObj, **kwopts)
  "Jolly Mixer" per se: 
    * open Input File(s) in binary read-only mode;
    * set pointer(s) in the previously openned Input File object(s) to the position(s) specified by 
      the corresponding offset value(s) for the given Input File(s);
    * read bytes from the Input File object(s) by calling roundRead() function;
    * "mix" these bytes: apply required/requested operations to delivered bytes;
    * write the result to the Output File object (outFileObj);
    * close Input File object(s).
  Output File object (outFileObj) must be prepared* and, after all, closed outside this function.
  * It is assumed that outFileObj MUST BE a correctly openned File-object in binary write mode 
  having pointer set up to correct offset position.
  !!! It is STRONGLY recomended to run this function inside "with"-Statement Context only !!!
  *** *** ***
  kwopts is a dict containing keys: 
    * INPUT1, str -- path to Input File 1;
    * INPUT1_oset, int -- offset of Input File 1, i.e. position to start reading from;
    * INPUT1_bwNot, boolean -- whether to apply Bitwise NOT to bytes obtained from Input File 1;
    * NumOfBytes -- total number of bytes to process;
    * ChunkSize -- Chunk Size for file input/output;
  and optionally -- INPUT2, INPUT2_oset and INPUT2_bwNot -- having the same sense for Input File 2
  (in case of two input files).
  * --------------------------------
  XOR (^) properties:
    * a^b = NOT(a)^NOT(b)
    * NOT(a)^b = a^NOT(b) = NOT(a^b)
  * --------------------------------
  '''
  #  *** 2 input files case *** ----------------------------------------------- *
  if kwopts['INPUT2']:
    if (kwopts['INPUT1_bwNot'] ^ kwopts['INPUT2_bwNot']):
      # "NOT(a^b)" case
      fun = snotxor
    else:
      # "a^b = NOT(a)^NOT(b)" case
      fun = sxor
    oset_1 = fixOffset(kwopts['INPUT1'], kwopts['INPUT1_oset'])
    oset_2 = fixOffset(kwopts['INPUT2'], kwopts['INPUT2_oset'])
    #with A() as a, B() as b:
    with open(kwopts['INPUT1'], 'rb') as if1_obj, open(kwopts['INPUT2'], 'rb') as if2_obj:
      if1_obj.seek(oset_1, 0)
      if2_obj.seek(oset_2, 0)
      bLeft = kwopts['NumOfBytes']
      while bLeft > 0:
        chunkSz = min([bLeft, kwopts['ChunkSize']])
        s1 = roundRead(if1_obj, chunkSz)
        s2 = roundRead(if2_obj, chunkSz)
        sO = fun(s1, s2)
        ofObj.write(sO)
        bLeft -= chunkSz
  #  *** one input file case *** ---------------------------------------------- *
  else:
    if kwopts['INPUT1_bwNot']:
      fun = snot
    else:
      fun = lambda x: x
    oset_1 = fixOffset(kwopts['INPUT1'], kwopts['INPUT1_oset'])
    with open(kwopts['INPUT1'], 'rb') as if1_obj:
      if1_obj.seek(oset_1, 0)
      bLeft = kwopts['NumOfBytes']
      while bLeft > 0:
        chunkSz = min([bLeft, kwopts['ChunkSize']])
        s1 = roundRead(if1_obj, chunkSz)
        sO = fun(s1)
        ofObj.write(sO)
        bLeft -= chunkSz

# *** ==============================================================================================

class jmFU:
  def __init__(self, **kwopts):
    # INPUTn -- input file n, INPUTn_oset -- its offset in bytes, 
    # INPUTn_bwNot -- whether to apply Bitwise Not while deliver bytes from the file.
    self.INPUT1 = None
    self.INPUT1_oset = 0
    self.INPUT1_bwNot = False
    #------------------------
    self.INPUT2 = None
    self.INPUT2_oset = 0
    self.INPUT2_bwNot = False
    #------------------------
    # Output file:
    self.OUTPUT = None
    self.OUTPUT_oset = 0
    # Number of bytes to process. Chunk Size for file input/output. 
    self.NumOfBytes = 0
    self.ChunkSize = defaultChunkSize
    # One of the: 'overwriteFile', 'appendBytes', 'rewriteBytes', 'insertBytes'
    self.ModifyMethod = 'overwriteFile'
    # If the Output File exists, back up it to this path before process.
    self.BackupPath = None
    # Temporary Output file Path. (if the Output File exists)
    # Output all the data to this file first, and then MOVE the file to its 
    # "final destination": the Output File Path as specified in self.OUTPUT
    self.TmpOutPath = None
    # --------------------------------------
    self._modifyMethods = {
      'overwriteFile': self.overwriteFile,
      'appendBytes':   self.appendBytes,
      'rewriteBytes':  self.rewriteBytes,
      'insertBytes':   self.insertBytes
      }
    # --------------------------------------
    if kwopts:
      self.config(**kwopts)
  # *** --------------------------------------------------------------------------------------------
  
  def config(self, **kwopts):
    if 'INPUT1' in kwopts:
      self.INPUT1 = kwopts['INPUT1']
    if 'INPUT1_oset' in kwopts:
      self.INPUT1_oset = kwopts['INPUT1_oset']
    if 'INPUT1_bwNot' in kwopts:
      self.INPUT1_bwNot = kwopts['INPUT1_bwNot']
    #-------------------------------------------
    if 'INPUT2' in kwopts:
      self.INPUT2 = kwopts['INPUT2']
    if 'INPUT2_oset' in kwopts:
      self.INPUT2_oset = kwopts['INPUT2_oset']
    if 'INPUT2_bwNot' in kwopts:
      self.INPUT2_bwNot = kwopts['INPUT2_bwNot']
    #-------------------------------------------
    if 'OUTPUT' in kwopts:
      self.OUTPUT = kwopts['OUTPUT']
    if 'OUTPUT_oset' in kwopts:
      self.OUTPUT_oset = kwopts['OUTPUT_oset']
    if 'NumOfBytes' in kwopts:
      self.NumOfBytes = kwopts['NumOfBytes']
    if 'ChunkSize' in kwopts:
      self.ChunkSize = kwopts['ChunkSize']
    if 'ModifyMethod' in kwopts:
      self.ModifyMethod = kwopts['ModifyMethod']
    if 'BackupPath' in kwopts:
      self.BackupPath = kwopts['BackupPath']
    if 'TmpOutPath' in kwopts:
      self.TmpOutPath = kwopts['TmpOutPath']
  # *** --------------------------------------------------------------------------------------------
  
  def get_conf(self):
    kwopts = dict()
    kwopts['INPUT1'] = self.INPUT1 
    kwopts['INPUT1_oset'] = self.INPUT1_oset
    kwopts['INPUT1_bwNot'] = self.INPUT1_bwNot
    #-----------------------------------------
    kwopts['INPUT2'] = self.INPUT2
    kwopts['INPUT2_oset'] = self.INPUT2_oset
    kwopts['INPUT2_bwNot'] = self.INPUT2_bwNot
    #-----------------------------------------
    kwopts['OUTPUT'] = self.OUTPUT
    kwopts['OUTPUT_oset'] = self.OUTPUT_oset
    kwopts['NumOfBytes'] = self.NumOfBytes
    kwopts['ChunkSize'] = self.ChunkSize
    kwopts['ModifyMethod'] = self.ModifyMethod
    kwopts['BackupPath'] = self.BackupPath
    kwopts['TmpOutPath'] = self.TmpOutPath
    return kwopts
  # *** ============================================================================================
  
  # <--- Consider preservation of Output File attributes, at least MODIFICATION / Access timestamps !!! 
  def overwriteFile(self):
    if self.BackupPath:
      shutil.copy2(self.OUTPUT, self.BackupPath)
    optsD = self.get_conf()
    outFile = self.TmpOutPath or self.OUTPUT
    with open(outFile, 'wb') as ofObj:
      jm_write(ofObj, **optsD)
    if self.TmpOutPath:
      os.rename(self.TmpOutPath, self.OUTPUT)
  # *** --------------------------------------------------------------------------------------------
  
  def appendBytes(self):
    if self.BackupPath:
      shutil.copy2(self.OUTPUT, self.BackupPath)
    if self.TmpOutPath:
      shutil.copy2(self.OUTPUT, self.TmpOutPath)
      outFile = self.TmpOutPath
    else:
      outFile = self.OUTPUT
    optsD = self.get_conf()
    with open(outFile, 'ab') as ofObj:
      jm_write(ofObj, **optsD)
    if self.TmpOutPath:
      os.rename(self.TmpOutPath, self.OUTPUT)
  # *** --------------------------------------------------------------------------------------------
  
  def rewriteBytes(self):
    if self.BackupPath:
      shutil.copy2(self.OUTPUT, self.BackupPath)
    if self.TmpOutPath:
      shutil.copy2(self.OUTPUT, self.TmpOutPath)
      outFile = self.TmpOutPath
    else:
      outFile = self.OUTPUT
    optsD = self.get_conf()
    oset = fixOffset(outFile, self.OUTPUT_oset)
    with open(outFile, 'rb+') as ofObj:
      ofObj.seek(oset, 0)
      jm_write(ofObj, **optsD)
    if self.TmpOutPath:
      os.rename(self.TmpOutPath, self.OUTPUT)
  # *** --------------------------------------------------------------------------------------------
  
  def insertBytes(self):
    if not (self.BackupPath or self.TmpOutPath):
      msg = ''.join([
        '\'insertBytes\' Modify Method: Can not directly insert bytes to an existing file !\n',
        '''At least either separate Temporary Output File or Back Up the original version 
        of the Output File is required. At least one of the options: \'Use Temporary Output\'
        or \'Backup the Original [Output File]\' MUST be enabled / configured together with 
        \'insertBytes\' Modify Method.'''
        ])
      raise RuntimeError(msg)
    if self.BackupPath:
      shutil.copy2(self.OUTPUT, self.BackupPath)
    if self.TmpOutPath:
      shutil.copy2(self.OUTPUT, self.TmpOutPath)
      outFile = self.TmpOutPath
      srcFile = self.OUTPUT
    else:
      outFile = self.OUTPUT
      srcFile = self.BackupPath
    optsD = self.get_conf()
    oset = fixOffset(outFile, self.OUTPUT_oset)
    with open(outFile, 'rb+') as ofObj, open(srcFile, 'rb') as srcObj:
      ofObj.seek(oset, 0)
      srcObj.seek(oset, 0)
      jm_write(ofObj, **optsD)
      for chunk in iter(lambda: srcObj.read(self.ChunkSize), ''):
        ofObj.write(chunk)
    if self.TmpOutPath:
      os.rename(self.TmpOutPath, self.OUTPUT)
  # <--- Consider preservation of Output File attributes, at least MODIFICATION / Access timestamps !!! 
  # *** ============================================================================================
  
  def run(self):
    # <--------------------------- DIRTY !!! To be fixed !!! <------------------ !!! !!! !!! <-------- !!!
    t = datetime.datetime.now()
    logMsg = t.strftime(logMsgDateTimeFormat) + '\n' + str(self) + '\n'
    try:
      self._modifyMethods[self.ModifyMethod]()
    except:
      tbStr = traceback.format_exc()  # <------------------------------------------ Check THAT !!! <---- !!!
      logMsg += '!!! Operation FAILED !!!\n' + tbStr
      execFlag = False #'fail'
    else:
      logMsg += '* Operation Completed Successfully!\n'
      execFlag = True #'ok'
    finally:
      logMsg += '='*100 + '\n'
    # ------------------------------------------------------------------------ # <-------------------- !!!
    # self.GUIobj.setupFinish(logMsg, execFlag) # There to find target in old version of GUI <-------- !!!
    return logMsg, execFlag

    # <--------------------------- DIRTY !!! To be fixed !!! <------------------ !!! !!! !!! <-------- !!!
  # *** ============================================================================================
  
  def __str__(self):
    ''' String representation of an object of this class. '''
    s = '*** ' + '-'*50 + ' ***\n'
    s += ' * Input file #1 : ' + str(self.INPUT1) + '\n'
    s += 'Offset (raw/fixed): ' + str(self.INPUT1_oset) + ' bytes / ' + str(fixOffset(self.INPUT1, self.INPUT1_oset)) + ' bytes\n'
    if self.INPUT1_bwNot:
      s += 'Apply bitwise NOT\n'
    s += '-'*25 + '\n'
    # -------------------------
    if self.INPUT2:
      s += ' * Input file #2 : ' + str(self.INPUT2) + '\n'
      s += 'Offset (raw/fixed): ' + str(self.INPUT2_oset) + ' bytes / ' + str(fixOffset(self.INPUT2, self.INPUT2_oset)) + ' bytes\n'
      if self.INPUT2_bwNot:
        s += 'Apply bitwise NOT\n'
      s += '-'*25 + '\n'
    # -------------------------
    s += ' * Modify Method: ' + self.ModifyMethod + '\n'
    s += 'Number of bytes to process: ' + str(self.NumOfBytes) + '\n'
    s += 'Chunk Size for file input/output: ' + str(self.ChunkSize) + '\n'
    s += '-'*25 + '\n'
    # -------------------------
    s += ' * Output file : ' + str(self.OUTPUT) + '\n'
    if self.ModifyMethod in ['rewriteBytes', 'insertBytes']:
      s += 'Offset (raw/fixed): ' + str(self.OUTPUT_oset) + ' bytes / ' + str(fixOffset(self.OUTPUT, self.OUTPUT_oset)) + ' bytes\n'
    s += 'Path to Temporary Output: ' + str(self.TmpOutPath) + '\n'
    s += 'Path to Backup: ' + str(self.BackupPath) + '\n'
    s += '*** ' + '-'*50 + ' ***\n'
    return s
  
# *** ==============================================================================================
# *** ==============================================================================================

def genBcpPath(f_path):
  dirname, fname = os.path.split(f_path)
  t = datetime.datetime.now()
  timeStamp = t.strftime(fileTimeStampFormat)
  bcp_name = fname + '.' + timeStamp + '.BCP'
  return os.path.join(dirname, bcp_name)
# *** ----------------------------------------------------------------------------------------------

def genTmpPath(f_path):
  dirname, fname = os.path.split(f_path)
  t = datetime.datetime.now()
  timeStamp = t.strftime(fileTimeStampFormat)
  tmp_name = '_.TMP-' + timeStamp + '._' + fname
  return os.path.join(dirname, tmp_name)

# *** ==============================================================================================

def positiveInt(s):
  ok = True
  val = s
  try:
    val = int(s)
  except:
    ok = False
  if not ok or val <= 0:
    msg = "\n\tWrong value: %r \n\tMust be positive integer." % s
    raise argparse.ArgumentTypeError(msg)
  return val
# *** ----------------------------------------------------------------------------------------------

def checkOutFilePath(f_path):
  '''
  Try to open given file path for exclusive creation. In case of success close and remove
  the file immediately. Otherwise raise the exception.
  '''
  try:
    f = open(f_path, 'x')
    f.close()
    os.remove(f_path)
  except:
    if os.path.isfile(f_path):
      msg = "\n\tCan not use the file: %r \n\tFile exists." % f_path
    else:
      msg = "\n\tCan not use the file: %r \n\tPermission denied!" % f_path
    raise argparse.ArgumentTypeError(msg)
  return f_path
# *** ----------------------------------------------------------------------------------------------

def dispArgs(argDict):
  if sys.version[0] == '2':
    print '-'*50
    for key, value in argDict.items():
      print "The value of {} is {}".format(key, value)
    print '-'*50
  elif sys.version[0] == '3':
    print('-'*50)
    for key, value in argDict.items():
      print( "The value of {} is {}".format(key, value))
    print('-'*50)
  else:
    raise RuntimeError('Unrecognized python version:\n  {}'.format(sys.version))
# *** ----------------------------------------------------------------------------------------------

def main():
  parser = argparse.ArgumentParser(prog = progName, add_help = False, description = progDescription, 
                                   epilog = progCopyright)
  # Input File 1:
  if1_group = parser.add_argument_group(title='Input File 1 parameters')
  if1_group.add_argument('--input_1', '--if1', dest='INPUT1', required=True, nargs='?',
            help = 'Path to Input File 1', metavar = '/path/to/input/file_1')
  if1_group.add_argument('--input_1_offset', '--oset1', dest='INPUT1_oset', nargs='?', default='0',
            type=int, help = 'Offset for Input File 1 in bytes', metavar = 'NUMBER_OF_BYTES')
  if1_group.add_argument('--input_1_bw_not', '--bwNOT1', dest='INPUT1_bwNot', action='store_true',
            help = 'Whether to apply bitwise NOT to bytes from Input File 1 while read it context')
  
  # Input File 1 (optional):
  if2_group = parser.add_argument_group(title='Input File 2 parameters (optional)')
  if2_group.add_argument('--input_2', '--if2', dest='INPUT2', nargs='?',
            help = 'Path to Input File 2', metavar = '/path/to/input/file_2')
  if2_group.add_argument('--input_2_offset', '--oset2', dest='INPUT2_oset', nargs='?', default='0',
            type=int, help = 'Offset for Input File 2 in bytes', metavar = 'NUMBER_OF_BYTES')
  if2_group.add_argument('--input_2_bw_not', '--bwNOT2', dest='INPUT2_bwNot', action='store_true',
            help = 'Whether to apply bitwise NOT to bytes from Input File 2 while read it context')
  
  # Workflow parameters:
  wf_group = parser.add_argument_group(title='Workflow parameters')
  wf_group.add_argument( '--modify_method', '-m', '-M', dest='ModifyMethod', nargs='?', 
            choices=['overwriteFile', 'appendBytes', 'rewriteBytes', 'insertBytes'], 
            default='overwriteFile', metavar = 'modifyMethod', help = '... help for ModifyMethod ...')
  wf_group.add_argument('--bytes_num', '-n', '-N', dest='NumOfBytes', nargs='?', type=positiveInt, 
            metavar='NUMBER_OF_BYTES', 
            help = '''Number of bytes to process. Will process Input File 1 completely one time 
            if this parameter is not specified explicitly.''')
  wf_group.add_argument('--chunk_size', '--cs', '-s', '-S', dest='ChunkSize', nargs='?', 
            default=defaultChunkSize, type=positiveInt, metavar='NUMBER_OF_BYTES', 
            help = 'Chunk Size in bytes for file input / output operations')
  
  # Output File:
  of_group = parser.add_argument_group(title='Output parameters')
  of_group.add_argument('--output', '--of', dest='OUTPUT', required=True, nargs='?', 
            help = 'Path to Output File', metavar = '/path/to/output/file')
  of_group.add_argument('--output_offset', '--outoset', dest='OUTPUT_oset', nargs='?', default='0',
            type=int, help = 'Offset for Output File in bytes', metavar = 'NUMBER_OF_BYTES')
  of_group.add_argument('--tmp', dest='TmpOutPath', nargs='?', const='__AUTO__', default=None, 
            help = '''File to produce temporary output to. If it is specified all the output will 
            be sent to this file first, then the Output File will be replaced with this file. 
            If this option is NOT followed by the argument (passed as flag) the file name for 
            temporary output to will be generated automatically.''',
            metavar = '/path/to/temporary/output/file',
            type = checkOutFilePath)
  of_group.add_argument('--bcp', dest='BackupPath', nargs='?', const='__AUTO__', default=None, 
            help = '''File to back up the original version of the Output File to.
            If this option is NOT followed by the argument (passed as flag) the file name for 
            the backup_file will be generated automatically.''',
            metavar = '/path/to/backup_file',
            type = checkOutFilePath)
  
  # Others:
  other_group = parser.add_argument_group(title='Other parameters')
  other_group.add_argument('--version', action='version', help = 'Display version info and exit',
            version='%(prog)s {}'.format (progVersion))
  other_group.add_argument('--help', '-h', action='help', help='Show this help message and exit')
  # ---------------------------------------------------------------------------------------------
  
  argNS = parser.parse_args(sys.argv[1:])
  # convert The Namespace object to dict:
  argD = vars(argNS)
  dispArgs(argD) # <------------------------------------------------------------ For debug only !!!
  
  # Generate TmpOutPath if required
  if argD['TmpOutPath'] == '__AUTO__':
    argD['TmpOutPath'] = genTmpPath(argD['OUTPUT'])
  
  # Generate BackupPath if required
  if argD['BackupPath'] == '__AUTO__':
    argD['BackupPath'] = genBcpPath(argD['OUTPUT'])
  
  # Check files' names
  if argD['INPUT2'] and argD['INPUT2'] == argD['INPUT1']:
    raise ValueError('Input File 1 and Input File 2 must be DIFFERENT files!')
  if argD['BackupPath'] and argD['TmpOutPath'] and argD['BackupPath'] == argD['TmpOutPath']:
    raise ValueError('Backup File and Temporary Output File must be DIFFERENT files!')
  if argD['OUTPUT'] in [argD['INPUT1'], argD['INPUT2'], argD['BackupPath'], argD['TmpOutPath']]:
    raise ValueError('''Output File MUST NOT be the same as either of: 
                     Input File 1, Input File 2, Backup File or Temporary Output File.''')
  
  # If NumOfBytes is not passed set it equal to the size of Input File 1
  if not argD['NumOfBytes']:
    argD['NumOfBytes'] = os.path.getsize(argD['INPUT1'])
  dispArgs(argD) # <------------------------------------------------------------ For debug only !!!
  
  # Create jmFU-object, pocess the files ...
  fw_obj = jmFU(**argD)
  logMsg, execFlag = fw_obj.run() # <----------------------------------------------------------------------------- !!!
  if execFlag:
    sys.stdout.write(logMsg)
  else:
    sys.stderr.write(logMsg)
  
  return None
# ------------------------------------------------------------------------------------------------ #
if __name__ == '__main__':
  main()
