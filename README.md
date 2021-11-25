# Yum Extender (yumex-dnf)

This repository contains a complete rewrite of Yum Extender in python3, Gtk3 and using the dnf-daemon dbus API for
packaging actions

> **_May 2021:_**  yumex-dnf is now back in active development


Group/History support is read-only for now, as dnfdaemon support for history/groups is broken 


## How to build & install test rpms
```
git clone https://github.com/timlau/yumex-dnf.git
cd yumex-dnf
make get-builddeps
make test-inst
```

## Requirements

```
dnf install python3 python3-gobject 
```

[dnf-daemon](https://github.com/timlau/dnf-daemon) python3 bindings must also be installed.

```
dnf install python3-dnfdaemon
```

Or build the latest version from git

```
git clone https://github.com/timlau/dnf-daemon.git
cd dnf-daemon
make test-inst
```


## Fedora Copr Repository
yumex-dnf development packages is available in a [fedora Copr repository](https://copr.fedoraproject.org/coprs/timlau/yumex-dnf/) for  f34 & Rawhide


Use this to enable it.
```
sudo dnf copr enable timlau/yumex-dnf
sudo dnf install yumex-dnf
```

## Contributing
* Please [report bugs](https://github.com/timlau/yumex-dnf/issues) if you find some. 
* In case you want to [propose changes](https://github.com/timlau/yumex-dnf/pulls), please do so on Github after [testing](https://github.com/timlau/yumex-dnf/wiki/Testing-yumex-for-developing) them. 
* If you want to contribute translations, please do so on [Transifex](https://www.transifex.com/timlau/yumex/).

<br/>
<br/>
<br/>
<br/>

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg?style=for-the-badge&logo=appveyor)](https://github.com/psf/black) &nbsp;
 [![Code linter: flake8](https://img.shields.io/badge/linter-flake8-blue.svg?style=for-the-badge&logo=appveyor
)](https://github.com/PyCQA/flake8)

