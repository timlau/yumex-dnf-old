%global appname yumex

Name:     %{appname}-dnf
Version:  4.4.0
Release:  1%{?dist}
Summary:  Yum Extender graphical package management tool

Group:    Applications/System
License:  GPLv2+
URL:      http://yumex.dk
Source0:  https://github.com/timlau/yumex-dnf/releases/download/%{name}-%{version}/%{name}-%{version}.tar.gz

BuildArch: noarch
BuildRequires: desktop-file-utils
BuildRequires: gettext
BuildRequires: intltool
BuildRequires: python3-devel >= 3.8
BuildRequires: make
BuildRequires: python3-libsass
BuildRequires: libappstream-glib

Requires: python3-dnfdaemon >= 0.3.10
Requires: python3-gobject >= 3.10
Requires: python3-pyxdg
Requires: python3-dbus
Requires: python3-cairo
Requires: libnotify
Requires: google-noto-sans-fonts

%description
Graphical package tool for maintain packages on the system


%prep
%setup -q


%build
make %{?_smp_mflags}

%install
make install PYTHON=%{__python3} DESTDIR=%{buildroot} DATADIR=%{_datadir}
desktop-file-validate %{buildroot}/%{_datadir}/applications/%{name}.desktop
desktop-file-validate %{buildroot}/%{_datadir}/applications/%{name}-local.desktop
appstream-util validate-relax --nonet %{buildroot}%{_metainfodir}/%{name}.metainfo.xml

%find_lang %name

%post
/bin/touch --no-create %{_datadir}/icons/hicolor &>/dev/null || :
update-desktop-database %{_datadir}/applications &> /dev/null || :

%postun
if [ $1 -eq 0 ] ; then
    /bin/touch --no-create %{_datadir}/icons/hicolor &>/dev/null
    /usr/bin/gtk-update-icon-cache -f %{_datadir}/icons/hicolor &>/dev/null || :
fi
update-desktop-database %{_datadir}/applications &> /dev/null || :

%posttrans
/usr/bin/gtk-update-icon-cache -f %{_datadir}/icons/hicolor &>/dev/null || :

%files -f  %{name}.lang
%doc README.md COPYING
%{_datadir}/%{name}
%{_bindir}/%{name}*
%{python3_sitelib}/%{appname}/
%{python3_sitelib}/yumex_dnf-*.egg-info
%{_datadir}/applications/*.desktop
%{_datadir}/icons/hicolor/
%{_metainfodir}/%{name}.metainfo.xml

%changelog

* Fri Jun 4 2021 Tim Lauridsen <timlau@fedoraproject.org> 4.4.0-1
- bumped release to 4.4.0 (dev)

* Wed May 11 2016 Tim Lauridsen <timlau@fedoraproject.org> 4.3.3-1
- bumped release to 4.3.3 (dev)

* Tue Apr 26 2016 Tim Lauridsen <timlau@fedoraproject.org> 4.3.2-1
- bumped release to 4.3.2 (dev)

* Wed Dec 9 2015 Tim Lauridsen <timlau@fedoraproject.org> 4.3.1-1
- bumped release to 4.3.1 (dev)

* Tue Dec 1 2015 Tim Lauridsen <timlau@fedoraproject.org> 4.3.0-1
- bumped release to 4.3.0 (dev)

* Wed Sep 30 2015 Tim Lauridsen <timlau@fedoraproject.org> 4.1.4-1
- bumped release to 4.1.4
- need python3-dnfdaemon >= 0.3.10

* Wed May 27 2015 Tim Lauridsen <timlau@fedoraproject.org> 4.1.3-1
- bumped release to 4.1.3
- need python3-dnfdaemon >= 0.3.9

* Sun Apr 26 2015 Tim Lauridsen <timlau@fedoraproject.org> 4.1.2-1
- bumped release to 4.1.2
- need python3-dnfdaemon >= 0.3.8

* Sun Apr 26 2015 Tim Lauridsen <timlau@fedoraproject.org> 4.1.1-1
- bumped release to 4.1.1

* Thu Apr 16 2015 Tim Lauridsen <timlau@fedoraproject.org> 4.1.0-2
- require python3-dnfdaemon >= 0.3.6

* Sun Apr 12 2015 Tim Lauridsen <timlau@fedoraproject.org> 4.1.0-1
- bumped release to 4.1.0

* Sat Apr 11 2015 Tim Lauridsen <timlau@fedoraproject.org> 4.0.10-3
- fixed changelog versioning

* Thu Apr 9 2015 Tim Lauridsen <timlau@fedoraproject.org> 4.0.10-1
- bumped release to 4.0.10

* Tue Apr 7 2015 Tim Lauridsen <timlau@fedoraproject.org> 4.0.9-1
- bumped release to 4.0.9

* Tue Oct 21 2014 Tim Lauridsen <timlau@fedoraproject.org> 4.0.8-1
- bumped release to 4.0.8
- require python3-dnfdaemon >= 0.3.3

* Sun Sep 21 2014 Tim Lauridsen <timlau@fedoraproject.org> 4.0.7-1
- bumped release to 4.0.7

* Tue Sep 02 2014 Tim Lauridsen <timlau@fedoraproject.org> 4.0.6-1
- bumped release to 4.0.6

* Fri Jun 06 2014 Tim Lauridsen <timlau@fedoraproject.org> 4.0.5-1
- bumped release to 4.0.5
- Requires: python3-dnfdaemon-client >= 0.2.2

* Fri May 09 2014 Tim Lauridsen <timlau@fedoraproject.org> 4.0.4-1
- bumped release to 4.0.4
- Requires: python3-dnfdaemon-client >= 0.2.0

* Sat May 03 2014 Tim Lauridsen <timlau@fedoraproject.org> 4.0.3-1
- bumped release to 4.0.3
- Requires: python3-dnfdaemon >= 0.1.5

* Tue Apr 01 2014 Tim Lauridsen <timlau@fedoraproject.org> 4.0.2-1
- bumped release to 4.0.2
- Requires: python3-dnfdaemon >= 0.1.4

* Sat Mar 29 2014 Tim Lauridsen <timlau@fedoraproject.org> 4.0.1-1
- bumped release to 4.0.1

* Sun Sep 15 2013 Tim Lauridsen <timlau@fedoraproject.org> 3.99.1-1
- Initial rpm build

