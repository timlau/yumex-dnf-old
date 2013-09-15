%global appname yumex

Name:     %{appname}-nextgen
Version:  3.99.1
Release:  1%{?dist}
Summary:  Yum Extender graphical package management tool

Group:    Applications/System
License:  GPLv2+
URL:      http://yum-extender.blogspot.com
Source0:  http://www.yum-extender.org/dnl/yumex/source/%{name}-%{version}.tar.gz

BuildArch: noarch
BuildRequires: python3-devel
BuildRequires: desktop-file-utils
BuildRequires: gettext
BuildRequires: intltool


Requires: python3-yumdaemon >= 0.9.2
Requires: python3-gobject

%description
Graphical User Interface for Yum.


%prep
%setup -q 


%build
make


%install
make DESTDIR=$RPM_BUILD_ROOT install
desktop-file-validate %{buildroot}/%{_datadir}/applications/%{name}.desktop    

%post
/bin/touch --no-create %{_datadir}/icons/hicolor &>/dev/null || :

%postun
if [ $1 -eq 0 ] ; then
    /bin/touch --no-create %{_datadir}/icons/hicolor &>/dev/null
    /usr/bin/gtk-update-icon-cache -f %{_datadir}/icons/hicolor &>/dev/null || :
fi

%posttrans
/usr/bin/gtk-update-icon-cache -f %{_datadir}/icons/hicolor &>/dev/null || :

%files
%doc README.md
%{_datadir}/%{name}
%{_bindir}/%{name}
%{python3_sitelib}/yumex/
%{_datadir}/applications/%{name}.desktop
%{_datadir}/icons/hicolor/

%changelog
* Sun Sep 15 2013 Tim Lauridsen <timlau@fedoraproject.org> 3.99.1-1
- Initial rpm build

