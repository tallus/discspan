#!/usr/bin/env python
# Port of
# http://git.kernel.org/?p=linux/hotplug/udev.git;a=blob;f=extras/gudev/gjs-example.js

import sys
sys.path.insert(0, ".libs")

import gudev
import glib

print "GUDEV VERSION: %s" % gudev.__version__

def print_device(device):
    print "subsystem", device.get_subsystem()
    print "devtype", device.get_devtype()
    print "name", device.get_name()
    print "number", device.get_number()
    print "sysfs_path:", device.get_sysfs_path()
    print "driver:", device.get_driver()
    print "action:", device.get_action()
    print "seqnum:", device.get_seqnum()
    print "device type:", device.get_device_type()
    print "device number:", device.get_device_number()
    print "device file:", device.get_device_file()
    print "device file symlinks:", ", ".join(device.get_device_file_symlinks())
    print "device keys:", ", ".join(device.get_property_keys())
    for device_key in device.get_property_keys():
        print "   device property %s: %s"  % (device_key, device.get_property(device_key))

def on_uevent(client, action, device):
    print "UEVENT"
    print_device(device)
    print "------", device.get_property("ID_MEDIA_PLAYER")

client = gudev.Client(["block"])
client.connect("uevent", on_uevent)

devices = client.query_by_subsystem("block")
for device in devices:
    if device.get_property('ID_TYPE') and 'cd' in device.get_property('ID_TYPE'):
        print_device(device)

print "\n --- WAITING FOR EVENTS ---"

try: glib.MainLoop().run()
except KeyboardInterrupt:
    glib.MainLoop().quit()

