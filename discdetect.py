#!/usr/bin/env python

import dbus
import gobject
from dbus.mainloop.glib import DBusGMainLoop

DEBUG = True

class DetectMedia():

    def __init__(self, device=None):
        mainloop = gobject.MainLoop()

        #must be done before connecting to DBus
        DBusGMainLoop(set_as_default=True)

        self.bus = dbus.SystemBus()
        self.proxy = self.bus.get_object("org.freedesktop.UDisks", 
                               "/org/freedesktop/UDisks")
        self.iface = dbus.Interface(self.proxy, "org.freedesktop.UDisks")

        #adds two signal listeners
        self.iface.connect_to_signal('DeviceAdded', self.device_added_callback)
        self.iface.connect_to_signal('DeviceChanged', self.device_changed_callback)

        # Check some daemon info
        try: print "Daemon Version:",proxy.Get('org.freedesktop.UDisks', 'DaemonVersion')
        except: print "Unknown"
        try: print "Daemon is Inhibited:",proxy.Get('org.freedesktop.UDisks', 'daemon-is-inhibited')
        except: print "Unknown"

        if not device:
            devices = self.iface.EnumerateDevices()
            for device in devices:
                return self.detect_media(device)
        else:
            return self.detect_media(device)

        try: mainloop.run()
        except KeyboardInterrupt:
            mainloop.quit()

    def device_added_callback(self, device):
        "Called when a device is added."
        print 'Device %s was added' % (device)
        self.detect_media(dev_obj)

    def device_changed_callback(self, device):
        "Called when a device changes."
        print 'Device %s has changed' % (device)
        self.detect_media(dev_obj)

    def detect_media(self, device):
        "Attempts to detect device with blank media and returns the device."
        dev_obj = self.bus.get_object("org.freedesktop.UDisks", device)
        dev = dbus.Interface(dev_obj, "org.freedesktop.DBus.Properties")
        if dev.Get('', 'DeviceIsDrive') and len(dev.Get('', 'DriveMediaCompatibility')) > 0:
            devname = dev.Get('', 'DeviceFile')
            print "Optical Device:",devname
            if DEBUG:
               for media in dev.Get('', 'DriveMediaCompatibility'):
                    print "Media compatibility:",media
            if bool(dev.Get('', 'DeviceIsOpticalDisc')):
                print "Media is loaded."
                if bool(dev.Get('', 'OpticalDiscIsBlank')):
                    print "Blank disc is avaiable."
                    print "Disc type:",dev.Get('', 'DriveMedia').lstrip('optical_')
                    print "Disc capacity:",dev.Get('', 'DeviceSize')
                    #mainloop.quit()
                    return devname
                else: print "Disc is not blank."
            else:
                print "Load a blank disc or Control-C to quit."
                return None
            print "No optical drive found."
            #mainloop.quit()
            return None

if __name__ == '__main__':
    print DetectMedia()

