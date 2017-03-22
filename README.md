23-03-2017: yumex-dnf is no longer under active development
============================================================


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

[dnf-deamon](https://github.com/timlau/dnf-daemon) python3 bindings must also be installed.

```
dnf install python3-dnfdaemon
```

Or build the latest version from git

```
git clone https://github.com/timlau/dnf-daemon.git
cd dnf-daemon
make test-inst
```


Fedora Repository
=======================
yumex-dnf is available in the Fedora repositories for f22, f23 & Rawhide

Use this to install it.
```
sudo dnf install yumex-dnf
```

Fedora Copr Repository
=======================
yumex-dnf & dnddaemon development packages is available in a [fedora Copr repository](https://copr.fedoraproject.org/coprs/timlau/yumex-dnf/) for f22, f23 & Rawhide


Use this to enable it.
```
sudo dnf copr enable timlau/yumex-dnf
```

Contributing
============
Please [report bugs](https://github.com/timlau/yumex-dnf/issues) if you find some. In case you want to [propose changes](https://github.com/timlau/yumex-dnf/pulls), please do so on Github after [testing](https://github.com/timlau/yumex-dnf/wiki/Testing-yumex-for-developing) them. If you want to contribute translations, please do so on [Transifex](https://www.transifex.com/timlau/yumex/).
