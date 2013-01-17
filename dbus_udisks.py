#!/usr/bin/env python

import dbus
import gobject
from dbus.mainloop.glib import DBusGMainLoop

DEBUG = True

mainloop = gobject.MainLoop()

def device_added_callback(device):
    "Called when a device is added."
    print 'Device %s was added' % (device)
    detect_media(device)

def device_changed_callback(device):
    "Called when a device changes."
    print 'Device %s was changed' % (device)
    detect_media(device)

def detect_media(devices):
    "Attempts to detect device with blank media and returns the device."
    for device in devices:
        bus_obj = bus.get_object("org.freedesktop.UDisks", device)
        dev = dbus.Interface(bus_obj, "org.freedesktop.DBus.Properties")
        if dev.Get('', 'DeviceIsDrive') and dev.Get('', 'DeviceMajor') == 11:
            devname = dev.Get('', 'DeviceFile')
            print "Optical Device:",devname
            if DEBUG:
                data = dev.GetAll('')
                for i in data: print i+': '+str(data[i])
                for media in dev.Get('', 'DriveMediaCompatibility'):
                    print "Media compatibility:",media
            if bool(dev.Get('', 'DeviceIsOpticalDisc')):
                print "Media is loaded."
                if bool(dev.Get('', 'OpticalDiscIsBlank')):
                    print "Blank disc is avaiable."
                    print "Disc type:",dev.Get('', 'DriveMedia')
                    print "Disc capacity:",dev.Get('', 'DeviceSize')
                    mainloop.quit()
                    return devname
                else: print "Disc is not blank."
            else:
                print "Load a blank disc or Control-C to quit."
                return None
    print "No optical drive found."
    mainloop.quit()
    return None

#must be done before connecting to DBus
DBusGMainLoop(set_as_default=True)

bus = dbus.SystemBus()

proxy = bus.get_object("org.freedesktop.UDisks", 
                       "/org/freedesktop/UDisks")
iface = dbus.Interface(proxy, "org.freedesktop.UDisks")

# Check some daemon info
try: print "Daemon Version:",proxy.Get('org.freedesktop.UDisks', 'DaemonVersion')
except: print "Unknown"
try: print "Daemon is Inhibited:",proxy.Get('org.freedesktop.UDisks', 'daemon-is-inhibited')
except: print "Unknown"


devices = iface.get_dbus_method('EnumerateDevices')()


#addes two signal listeners
iface.connect_to_signal('DeviceAdded', device_added_callback)
iface.connect_to_signal('DeviceChanged', device_changed_callback)

detect_media(devices)

if __name__ == '__main__':
    #start the main loop
    try: mainloop.run()
    except KeyboardInterrupt:
        mainloop.quit()
