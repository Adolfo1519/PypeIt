import sys
from inspect import currentframe, getouterframes


class Messages:
    """
    Create coloured text for messages printed to screen.

    For further details on colours see the following example:
    http://ascii-table.com/ansi-escape-sequences.php
    """

    def __init__(self, log, debug, last_updated, version, colors=True):
        """
        Initialize the Message logging class

        Parameters
        ----------
        log : str
          Name of saved log file (no log will be saved if log=="")
        debug : bool
          Used for debugging. Should be set to False in all other cases
        last_updated : str
          The data of last update
        version : str
          Current version of the code
        colors : bool
          If true, the screen output will have colors, otherwise
          normal screen output will be displayed
        """

        # Initialize the log
        if log:
            self._log = open(log, 'w')
        else:
            self._log = log
        # Initialize other variables
        self._debug = debug
        self._last_updated = last_updated
        self._version = version
        # Save the version of the code including last update information to the log file
        if self._log:
            self._log.write("------------------------------------------------------\n\n")
            self._log.write("PYPIT was last updated {0:s}\n".format(last_updated))
            self._log.write("This log was generated with version {0:s} of PYPIT\n\n".format(version))
            self._log.write("------------------------------------------------------\n\n")
        # Use colors?
        self._start, self._end = "", ""
        self._black_CL, self._yellow_CL, self._blue_CL, self._green_CL, self._red_CL = "", "", "", "", ""
        self._white_RD, self._white_GR, self._white_BK = "", "", ""
        self._white_BL, self._black_YL, self._yellow_BK = "", "", ""
        if colors:
            self.enablecolors()
        else:
            self.disablecolors()

    # Headers and usage
    def armedheader(self, prognm):
        """
        Get the info header for ARMED
        """
        header = "##  "
        header += self._start + self._white_GR + "ARMED : "
        header += "Automated Reduction and Modelling of Echelle Data v1.0" + self._end + "\n"
        header += "##  "
        header += "Usage : "
        header += "python %s [options] filelist".format(prognm)
        return header

    def pypitheader(self, prognm):
        """
        Get the info header for PYPIT
        """
        header = "##  "
        header += self._start + self._white_GR + "PYPIT : "
        header += "The Python Spectroscopic Data Reduction Pipeline v1.0" + self._end + "\n"
        header += "##  "
        header += "Usage : "
        if prognm is None:
            header += "pypit [options] filename.red"
        else:
            header += "python %s [options] filename.red".format(prognm)
        return header

    def usage(self, prognm):
        print "\n#####################################################################"
        print self.pypitheader(prognm)
        print "##  -----------------------------------------------------------------"
        print "##  Options: (default values in brackets)"
        print "##   -c or --cpus      : (all) Number of cpu cores to use"
        print "##   -h or --help      : Print this message"
        print "##   -v or --verbose   : (2) Level of verbosity (0-2)"
        print "##  -----------------------------------------------------------------"
        print "##  %s".format(self._last_updated)
        print "#####################################################################\n"
        sys.exit()

    def debugmessage(self):
        if self._debug:
            info = getouterframes(currentframe())[2]
            dbgmsg = self._start + self._blue_CL + info[1].split("/")[-1]+" "+str(info[2])+" "+info[3]+"()"+self._end+" - "
        else:
            dbgmsg = ""
        return dbgmsg

    def close(self):
        """
        Close the log file before the code exits
        """
        if self._log:
            self._log.close()

    def signal_handler(self, signalnum, handler):
        """
        Handle signals sent by the keyboard during code execution
        """
        if signalnum == 2:
            self.info("Ctrl+C was pressed. Ending processes...")
            self.close()
            sys.exit()
        return

    def error(self, msg, usage=False):
        """
        Print an error message
        """
        dbgmsg = self.debugmessage()
        premsg = "\n"+self._start + self._white_RD + "[ERROR]   ::" + self._end + " "
        print >>sys.stderr, premsg+dbgmsg+msg
        if self._log:
            self._log.write(self.cleancolors(premsg+dbgmsg+msg)+"\n")
        self.close()
        if usage:
            self.usage(None)
        sys.exit()

    def info(self, msg):
        """
        Print an information message
        """
        dbgmsg = self.debugmessage()
        premsg = self._start + self._green_CL + "[INFO]    ::" + self._end + " "
        print >>sys.stderr, premsg+dbgmsg+msg
        if self._log:
            self._log.write(self.cleancolors(premsg+dbgmsg+msg)+"\n")
        return

    def info_update(self, msg, last=False):
        """
        Print an information message that needs to be updated
        """
        dbgmsg = self.debugmessage()
        premsg = "\r" + self._start + self._green_CL + "[INFO]    ::" + self._end + " "
        if last:
            print >>sys.stderr, premsg+dbgmsg+msg
            if self._log:
                self._log.write(self.cleancolors(premsg+dbgmsg+msg)+"\n")
        else:
            print >>sys.stderr, premsg+dbgmsg+msg,
            if self._log:
                self._log.write(self.cleancolors(premsg+dbgmsg+msg))
        return

    def test(self, msg):
        """
        Print a test message
        """
        dbgmsg = self.debugmessage()
        premsg = self._start + self._white_BL + "[TEST]    ::" + self._end + " "
        print >>sys.stderr, premsg+dbgmsg+msg
        if self._log:
            self._log.write(self.cleancolors(premsg+dbgmsg+msg)+"\n")
        return

    def warn(self, msg):
        """
        Print a warning message
        """
        dbgmsg = self.debugmessage()
        premsg = self._start + self._red_CL + "[WARNING] ::" + self._end + " "
        print >>sys.stderr, premsg+dbgmsg+msg
        if self._log:
            self._log.write(self.cleancolors(premsg+dbgmsg+msg)+"\n")
        return

    def bug(self, msg):
        """
        Print a bug message
        """
        dbgmsg = self.debugmessage()
        premsg = self._start + self._white_BK + "[BUG]     ::" + self._end + " "
        print >>sys.stderr, premsg+dbgmsg+msg
        if self._log:
            self._log.write(self.cleancolors(premsg+dbgmsg+msg))
        return

    def work(self, msg):
        """
        Print a work in progress message
        """
        dbgmsg = self.debugmessage()
        premsgp = self._start + self._black_CL + "[WORK IN ]::" + self._end + "\n"
        premsgs = self._start + self._yellow_CL + "[PROGRESS]::" + self._end + " "
        print >>sys.stderr, premsgp+premsgs+dbgmsg+msg
        if self._log:
            self._log.write(self.cleancolors(premsgp+premsgs+dbgmsg+msg)+"\n")
        return

    def prindent(self, msg):
        """
        Print an indent
        """
        premsg = "             "
        print >>sys.stderr, premsg+msg
        if self._log:
            self._log.write(self.cleancolors(premsg+msg)+"\n")
        return

    def input(self):
        """
        Return a text string to be used to display input required from the user
        """
        premsg = self._start + self._blue_CL + "[INPUT]   ::" + self._end + " "
        return premsg

    @staticmethod
    def newline():
        """
        Return a text string containing a newline to be used with messages
        """
        return "\n             "

    @staticmethod
    def indent():
        """
        Return a text string containing an indent to be used with messages
        """
        return "             "

    # Set the colors
    def enablecolors(self):
        """
        Enable colored output text
        """

        # Start and end coloured text
        self._start = "\x1B["
        self._end = "\x1B[" + "0m"

        # Clear Backgrounds
        self._black_CL = "1;30m"
        self._yellow_CL = "1;33m"
        self._blue_CL = "1;34m"
        self._green_CL = "1;32m"
        self._red_CL = "1;31m"

        # Coloured Backgrounds
        self._white_RD = "1;37;41m"
        self._white_GR = "1;37;42m"
        self._white_BK = "1;37;40m"
        self._white_BL = "1;37;44m"
        self._black_YL = "1;37;43m"
        self._yellow_BK = "1;33;40m"

    def cleancolors(self, msg):
        cols = [self._end, self._start,
                self._black_CL, self._yellow_CL, self._blue_CL, self._green_CL, self._red_CL,
                self._white_RD, self._white_GR, self._white_BK, self._white_BL, self._black_YL, self._yellow_BK]
        for i in cols:
            msg = msg.replace(i, "")
        return msg

    def disablecolors(self):
        """
        Disable colored output text
        """

        # Start and end coloured text
        self._start = ""
        self._end = ""

        # Clear Backgrounds
        self._black_CL = ""
        self._yellow_CL = ""
        self._blue_CL = ""
        self._green_CL = ""
        self._red_CL = ""

        # Coloured Backgrounds
        self._white_RD = ""
        self._white_GR = ""
        self._white_BK = ""
        self._white_BL = ""
        self._black_YL = ""
        self._yellow_BK = ""
