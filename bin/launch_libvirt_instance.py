#!/usr/bin/env python

import sys
import os
import uuid

XML_TEMPLATE = """<domain type='kvm'>
  <name>%s</name>
  <uuid>%s</uuid>
  <memory unit='KiB'>262144</memory>
  <vcpu placement='static'>1</vcpu>
  <os>
    <type arch='x86_64' machine='pc-i440fx-trusty'>hvm</type>
    <boot dev='hd'/>
  </os>
  <features>
    <acpi/>
  </features>
  <clock offset='utc'/>
  <on_poweroff>destroy</on_poweroff>
  <on_reboot>restart</on_reboot>
  <on_crash>destroy</on_crash>
  <devices>
    <emulator>/usr/bin/kvm</emulator>
    <disk type='file' device='disk'>
      <driver name='qemu' type='qcow2'/>
      <source file='/var/lib/libvirt/images/%s/image.qcow2'/>
      <target dev='vda' bus='virtio'/>
<address type='pci' domain='0x0000' bus='0x00' slot='0x05' function='0x0'/>
    </disk>
    <controller type='usb' index='0'>
<address type='pci' domain='0x0000' bus='0x00' slot='0x01' function='0x2'/>
    </controller>
    <controller type='pci' index='0' model='pci-root'/>
    <interface type='bridge'>
      <mac address='52:54:00:2d:%s:%s'/>
      <source bridge='obr2'/>
      <virtualport type='openvswitch'/>
      <model type='virtio'/>
<address type='pci' domain='0x0000' bus='0x00' slot='0x03' function='0x0'/>
    </interface>
    <input type='mouse' bus='ps2'/>
    <input type='keyboard' bus='ps2'/>
    <graphics type='vnc' port='-1' autoport='yes' listen='0.0.0.0'>
      <listen type='address' address='0.0.0.0'/>
    </graphics>
    <video>
      <model type='cirrus' vram='9216' heads='1'/>
<address type='pci' domain='0x0000' bus='0x00' slot='0x02' function='0x0'/>
    </video>
    <memballoon model='virtio'>
<address type='pci' domain='0x0000' bus='0x00' slot='0x04' function='0x0'/>
    </memballoon>
  </devices>
</domain>
"""


def int_to_hex(n):
    if not 1 <= n <= 254:
        raise KeyError('Wrong value: number not within [1, 254]')
    s = hex(n)[2:]
    if len(s) == 2:
        return s
    else:
        return '0' + s


def gen_libvirt_xml(subnet, begin, end):
    for i in range(begin, end):
        name = "%s.%s" % (subnet, i)
        xml = XML_TEMPLATE % (name, str(uuid.uuid4()), name,
                              int_to_hex(subnet), int_to_hex(i))
        print xml
        fout = open('/tmp/%s.%s.xml' % (subnet, i), 'w')
        fout.write(xml)
        fout.close()
        cmd = "mkdir -p /var/lib/libvirt/images/%s.%s/" % (subnet, i)
        print cmd
        os.system(cmd)
        cmd = ("qemu-img create -b /var/lib/libvirt/images/base.qcow2 "
               "-f qcow2 /var/lib/libvirt/images/%s.%s/image.qcow2" %
               (subnet, i))
        print cmd
        os.system(cmd)
        cmd = "virsh define /tmp/%s.%s.xml" % (subnet, i)
        print cmd
        os.system(cmd)

if __name__ == "__main__":
    subnet = int(sys.argv[1])
    begin = int(sys.argv[2])
    end = int(sys.argv[3])
    gen_libvirt_xml(subnet, begin, end)
