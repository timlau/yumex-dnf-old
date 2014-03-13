Yum Extender (yumex-dnf)
=========================

This repository contains a complete rewrite of Yum Extender in python3, Gtk3 and using the dnf-daemon dbus API for
packaging actions


How to build & install test rpms
=================================
```
git clone https://github.com/timlau/yumex-dnf.git
cd yumex-dnf
make get-builddeps
make test-inst
```

Requirements
============

```
yum install python3 python3-gobject 
```

[dnf-deamon](https://github.com/timlau/dnf-daemon) must also be installed.

```
git clone https://github.com/timlau/dnf-daemon.git
cd dnf-daemon
make test-inst
```


Test Fedora Repository
=======================

There is a test repository the contains test builds for yumex-dnf & dnf-daemon 
http://copr.fedoraproject.org/coprs/timlau/yumex-dnf/

download the .repo file for your Fedora release and place it in /etc/yum.repos.d


Use this to install it.
```
sudo dnf install yumex-dnf

```
