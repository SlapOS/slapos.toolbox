#!/bin/bash
##############################################################################
#
# Copyright (c) 2010 Vifib SARL and Contributors. All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly advised to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################
#
# This script is executed at the end of appliance creation.  Here you can do
# one-time actions to modify your appliance before it is ever used, like
# removing files and directories to make it smaller, creating symlinks,
# generating indexes, etc.
#
# The 'kiwi_type' variable will contain the format of the appliance (oem =
# disk image, vmx = VMware, iso = CD/DVD, xen = Xen).
#

# read in some variables
. /studio/profile


# Removing eth0 config file which became unecessary with the bridge creation
rm -f /etc/sysconfig/network/ifcfg-eth0
