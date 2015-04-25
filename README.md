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
dnf install python3 python3-gobject 
```

[dnf-deamon](https://github.com/timlau/dnf-daemon) must also be installed.

```
dnf install dnfdaemon
```

Or build the latest version from git

```
git clone https://github.com/timlau/dnf-daemon.git
cd dnf-daemon
make test-inst
```


Fedora Repository
=======================
yumex-dnf is available in the Fedora repositories for f21, f22 & Rawhide

Use this to install it.
```
sudo dnf install yumex-dnf
```
