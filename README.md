Yum Extender
============

This branch contains a complete rewrite of Yum Extender in python3, Gtk3 and using the yum-daemon dbus API for
packaging actions

How to build & install test rpms
=================================
```
git clone https://github.com/timlau/yumex.git
cd yumex
git checkout future
make get-builddeps
make test-inst
```

Requirements
============

```
yum install python3 python3-gobject
```

[yum-deamon](https://github.com/timlau/yum-daemon) must also be installed.

```
git clone https://github.com/timlau/yum-daemon.git
cd yum-daemon
make test-inst
```