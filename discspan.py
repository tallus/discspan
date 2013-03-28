#! /usr/bin/env python

__author__ = "James S. Martin"
__maintainer__ = "Richard M. Shaw"
__credits__ = "Doc, Dez, Erin, Jason, Adam"
__license__ = "GPL"
__version__ = "0.2.3"

import os
import sys
import os.path
import math
import subprocess
import tempfile
import dbus
import readline
import ConfigParser
import string
from decimal import *
from optparse import OptionParser
from time import sleep

debug = False

class Config:

    def __init__(self, cfgfile):

        self.config = ConfigParser.SafeConfigParser()
        self.config.read(cfgfile)
        self.media = self.config.options('media')
        self.speed = self.config.get('drive', 'speed')

    def convert_to_bytes(self,value):

        if value[-1:] == 'M':
            s_value = value.replace('M','')
            b_value = Decimal(s_value) * 2**20

        elif value[-1:] == 'G':
            s_value = value.replace('G','')
            b_value = Decimal(s_value) * 2**30

        else:
            print "Size does matter. Make sure you've specified a M or G after your media config file."
            sys.exit(1)

        return str(b_value)

    def get_capacity(self, medium):
        "Returns capacity of disc type in both human readable and in bytes."

        h_capacity, b_capacity = string.split(self.config.get('media', medium))

        return h_capacity, b_capacity


class Drive:

    def __init__(self, device_name, capacity, drive_name):

        self.device = device_name
        self.capacity = capacity
        self.model = drive_name

class System:

    def __init__(self, config):

        self.config = config

    def find_drives(self):

        drive = None
        bus = dbus.SystemBus()
        hal_obj = bus.get_object('org.freedesktop.Hal', '/org/freedesktop/Hal/Manager')
        hal = dbus.Interface(hal_obj, 'org.freedesktop.Hal.Manager')
        drives = []
        udis = []

        for udi in hal.FindDeviceByCapability('volume'):
            if debug: print udi

            dev_obj = bus.get_object('org.freedesktop.Hal', udi)
            dev = dbus.Interface(dev_obj, 'org.freedesktop.Hal.Device')

            try: volume_disc_type = dev.GetProperty('volume.disc.type')
            except: continue

            if volume_disc_type in self.config.media:
                device_name = dev.GetProperty('block.device')
                print "Media found in %s" % device_name

            else:
                print "No recordable media found in %s." % device_name
                continue

            if not dev.GetProperty('volume.disc.is_blank'):
                print "HAL says media in %s is not blank." % dev.GetProperty('block.device')
                continue

            else:
                parent_obj = bus.get_object('org.freedesktop.Hal', dev.GetProperty("info.parent"))
                parent = dbus.Interface(parent_obj, 'org.freedesktop.Hal.Device')
                h_capacity , b_capacity = self.config.get_capacity(dev.GetProperty('volume.disc.type'))
                drive_name = parent.GetProperty('info.product')
                drive = Drive(device_name, b_capacity, drive_name)
                print "The disc capacity of the disc in %s (%s) is %s." % (drive.device, drive.model, h_capacity)
                drives.append(drive)

        if len(drives) == 1:
            drive = drives[0]
            statement = '\nUsing %s (%s) as your dvd burner' % (drive.device, drive.model)

        elif len(drives) > 1:
            print "Don't make this difficult.  Please only put one piece of writable" \
            "medium in your system at a time."
            sys.exit(1)

        return drive

    def wait_for_media(self):

        n = 0
        drive = self.find_drives()
        if drive == None:
            print "Insert disc and wait for drive to become ready..."
            
        while drive == None:
            drive = self.find_drives()
            sleep(3)
            n = n + 1
            if n >= 30:
                print "Unable to detect media, exiting."
                sys.exit(1)

        return drive

class DiscType:

    def __init__(self, config, disc_type):

        self.config = config
        self.disc_type = disc_type

    def wait_for_media(self):
        '''note func name is taken from system class'''
        h_capacity , b_capacity = self.config.get_capacity(self.disc_type)
        drive = Drive('null_device', b_capacity, 'null_drive')
        return drive
    


class Interface:

    def __init__(self, backup_dir, speed):

        if self.validate_speed(speed):
            self.speed = speed
        else:
            print 'Your drive speed (%s) is invalid.' % self.speed
            sys.exit(1)

        if backup_dir == None:
            self.backup_dir = self.ask_questions()
        elif self.validate_backup_dir(backup_dir):
            self.backup_dir = backup_dir
        else:
            print 'Directory option is not valid.'
            self.backup_dir = self.ask_questions()

    def ask_questions(self):

        valid = False
        while not valid:
            backup_dir = raw_input('Which directory would you like to backup? (Or Q to quit)\n')
            if backup_dir in ('Q','q'):
                sys.exit(1)
            valid = self.validate_backup_dir(backup_dir)

        self.backup_dir = backup_dir

        return self.backup_dir

    def validate_speed(self, speed):

        try:
            int(speed)
            return True
        except:
            print speed, 'is not a valid number.'
            return False

    def validate_backup_dir(self, backup_dir):

        if os.path.isdir(backup_dir):
            return True
        else:
            print "You must enter a valid directory."
            return False

class Iso:

    def __init__(self, inputs, system):
        self.inputs = inputs
        self.system = system
        self.drive = self.system.wait_for_media()

    def build_list(self, files):

        disc_capacity = int(float(self.drive.capacity) * float(options.size_factor))
        print "Disc capacity reported by drive is: " + str(int(self.drive.capacity))
        if options.size_factor != 1:
            print " Adjusted disc capacity set to: " + str(disc_capacity)

        print "Building file lists..."
        file_count = 1
        # First 32768 bytes are unused by ISO 9660
        disc_size = 32768
        disc_list = []
        disc_files = []
        outfiles = []

        for file in files:

            if not os.path.islink(file):
            # Add ISO 9660 file system overhead in addition to file size
                file_size = 33 + len(os.path.split(file)[1]) + os.path.getsize(file)
                # Round up file sizes to 2KB sector size for ISO 9660.
                iso_size = math.ceil(file_size/(2.0**11))*(2.0**11)
                disc_size += iso_size
            else: pass

            if disc_size >= disc_capacity:
                disc_list.append(disc_files)
                print 'Disc %s will contain %s files using %dMB.' % (str(len(disc_list)), str(len(disc_files)),disc_size/(2**20))
                disc_size = 0
                disc_size += iso_size
                disc_files = []
                disc_files.append(file)
            else:
                disc_files.append(file)

        disc_list.append(disc_files)
        print 'Disc %s will contain %s files using %dMB.' % (str(len(disc_list)), str(len(disc_files)),disc_size/(2**20))
        return (disc_list)

    def calculate_discs(self):

        print "Calculating discs..."
        dir = self.inputs.backup_dir
        # First 32768 bytes are unused by ISO 9660
        total_size = 32768
        # Attempt to predict metadata size (file & directory descriptors)
        descriptor_size = 0
        disc_capacity = int(float(self.drive.capacity) * float(options.size_factor))

        if dir[len(dir)-1:] != "/":
            dir = dir + "/"

        file_list = []

        for path, dirs, files in os.walk(dir):
            for filename in files:
                file_list.append(os.path.join(path, filename))

        file_list.sort()
        for file in file_list:
            if not os.path.islink(file):
                size = os.path.getsize(file)
                if options.verbose: print file, size
                # Individual files must be smaller than 4GiB -1.
                if size >= 4*2**30 and not options.skip_big:
                    print "%s is to big. ISO 9660 requires individual files to be smaller than 4GiB." % file
                    sys.exit(1)
                elif size >= disc_capacity - 32768 and not options.skip_big:
                    print "%s will not fit on the current media. Try the --skip-big option to workaround." % file
                    sys.exit(1)
                elif size >= 4*2**30 and options.skip_big:
                    print "%s will be skipped because it is too big for ISO 9660." % file
                    file_list.remove(file)
                    continue
                elif size >= disc_capacity - 32768 and options.skip_big:
                    print "%s will be skipped because it is too big for the current media." % file
                    file_list.remove(file)
                    continue
                else:
                    total_size += size

        num_discs = int(math.ceil(total_size/disc_capacity))
        discs = self.build_list(file_list)
        print "\nNumber of %s's required to burn: %s" % ("dvd", len(discs))
        file_count = 0

        for disc in discs:
            file_count = file_count + len(disc)

        print "\nSanity Check:\n"
        print "Total files in directory: ", len(file_list)
        print "Total files in all discs: ", file_count

        print 'Total discs still: ' + str(len(discs))
        return discs


    def burn(self, disc, disc_num, total_disc, volume_name, test, iso_dir):


        msg = "\nReady to burn disc %s/%s."  % (disc_num, total_disc )
        print msg
        if int(disc_num) > 1:
            input=raw_input("Press enter to continue...")
        speed = self.inputs.speed
        drive = self.system.wait_for_media()
        dir = self.inputs.backup_dir

        list = ""
        for file in disc:

            file_on_disc = file.replace(dir, "")
            list = list + "%s=%s\n" % (file_on_disc, file)

        fd, temp_list = tempfile.mkstemp(suffix=".discspanlist")
        output = open(temp_list, 'w')
        output.write(list)
        output.close()
q
        if test :
            print 'Test write option enabled.'
            drive = '/dev/null'
        else:
            drive = self.drive.device

        if iso_dir :
            print 'ISO will be written to a file.'
            if iso_dir[len(iso_dir)-1:] != "/":
                iso_dir += "/"
            iso_file = iso_dir + volume_name + ".iso"
            if which('mkisofs'):
                burn_prog = mkisofs
            else:
                burn_prog = genisoimage
            burn_cmd = "%s -o %s -V %s -A DiscSpan -p Unknown" \
                       " -iso-level 4 -l -r -hide-rr-moved -J -joliet-long" \
                       " -graft-points" % (burn_prog, fork
                               iso_file, volume_name)
        else :
            burn_cmd = "growisofs -Z %s -speed=%s -use-the-force-luke=notray" \
                       " -use-the-force-luke=tty  " \
                       " -V %s -A DiscSpan -p Unknown -iso-level 4" \
                       " -l -r -hide-rr-moved -J -joliet-long" \
                       " -graft-points" % (drive, speed, volume_name)

        burn_cmd = burn_cmd + ' -path-list %s' % temp_list
        p = subprocess.Popen("%s" % (burn_cmd), shell=True)
        print burn_cmd
        sts = os.waitpid(p.pid, 0)
        os.unlink(temp_list)
        if not test and not iso_dir:
            p = subprocess.Popen("%s" % ("eject"), shell=True)
            sts = os.waitpid(p.pid, 0)
            sleep(5)


def which(name, flags=os.X_OK):
    # Taken from procutils.py, part of twisted
    # Copyright (c) 2001-2004 Twisted Matrix Laboratories.
    # Orignally MIT licensed
    """Search PATH for executable files with the given name.
    
    On newer versions of MS-Windows, the PATHEXT environment variable will be
    set to the list of file extensions for files considered executable. This
    will normally include things like ".EXE". This fuction will also find files
    with the given name ending with any of these extensions.

    On MS-Windows the only flag that has any meaning is os.F_OK. Any other
    flags will be ignored.
    
    @type name: C{str}
    @param name: The name for which to search.
    
    @type flags: C{int}
    @param flags: Arguments to L{os.access}.
    
    @rtype: C{list}
    @param: A list of the full paths to files found, in the
    order in which they were found.
    """
    result = []
    exts = filter(None, os.environ.get('PATHEXT', '').split(os.pathsep))
    path = os.environ.get('PATH', None)
    if path is None:
        return []
    for p in os.environ.get('PATH', '').split(os.pathsep):
        p = os.path.join(p, name)
        if os.access(p, flags):
            result.append(p)
        for e in exts:
            pext = p + e
            if os.access(pext, flags):
                result.append(pext)
    return result

if __name__ == "__main__":

    parser = OptionParser(version=__version__)
    parser.add_option("--config",  dest="config_file", metavar ="CONFIG_FILE",
                      help="Location of config file.")
    parser.add_option("--start-disc", dest="start_disc",
                      default=1, help="Specify disc to start with (in case of failed previous burn)", metavar="START_DISC")
    parser.add_option("--skip-big", action="store_true", dest="skip_big",
                      default=False, help="Skip files that are too big.", metavar="SKIP_BIG")
    parser.add_option("--test", action="store_true", dest="test",
                      default=False, help="Performs a test run of the burn.", metavar="TEST")
    parser.add_option("--dir",  dest="backup_dir", metavar ="BACKUP_DIR",
                      help="Directory to backup.")
    parser.add_option("--volume-name",  dest="volume_name", metavar ="VOLUME_NAME",
                      default='DiscSpan', help="Name for the volume.")
    parser.add_option("--size-factor", dest="size_factor",
                      default=1, help="Specify size factor for disc capacity, i.e. 1 = 100%", metavar="SIZE_FACTOR")
    parser.add_option("--iso-dir",  dest="iso_dir", metavar ="ISO_DIR",
                      default=False, help="Redirect iso generation to a directory. Filename will be generated from volume name.")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose",
                      default=False, help="Extended verbosity", metavar="VERBOSE")
    parser.add_option("--disc-type", dest="disc_type", 
                    help="specify a target disc type, as specified in discspan.ini,rather than detect from drive. Only works with the --iso-dir option." , metavar="DISC_TYPE")


    (options, args) = parser.parse_args()

    n = 0

    config_file = options.config_file

    if config_file == None:

        for file in [ os.path.join(sys.path[0], 'discspan.ini'), '/usr/local/etc/discspan.ini', '/etc/discspan.ini'] :
            if os.path.isfile(file):
                config_file = file

    print "Using", config_file, "as config file."
    c = Config(config_file)
    
    if options.disc_type and options.iso_dir:
        s = DiscType(c, options.disc_type)
    else:
        s = System(c)

    interface = Interface(options.backup_dir,c.speed)
    iso = Iso(interface, s)
    discs = iso.calculate_discs()
    disc_num = int(options.start_disc)

    for disc in discs[(int(disc_num)-1):]:
            # Basic logic to prevent volume names that are too long.
        if len(options.volume_name) <= 30 - len(discs):
            volume_name = options.volume_name + '_' + str(disc_num)
        else: volume_name = options.volume_name

        iso.burn(disc, disc_num, len(discs), volume_name, options.test, options.iso_dir)
        disc_num = disc_num + 1
