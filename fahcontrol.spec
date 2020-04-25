# TODO: Insert Copyright and Licensing statements

%{!?py3_build: %global py3_build %{__python3} setup.py build}
%{!?py3_install: %global py3_install %{__python3} setup.py install --skip-build --root %{buildroot}}
%{!?python3_sitelib: %global python3_sitelib %(%{__python3} -Ic "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}

%global source_date_epoch_from_changelog 1
%global debug_package %{nil}

Name:           fahcontrol
# TODO: What is the version?
Version:        0.0.1
Release:        1%{?dist}
Summary:        Folding@Home Control

License:        GPLv3+
URL:            https://foldingathome.org
Source0:        %{name}-%{version}-%{release}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-setuptools desktop-file-utils
Requires:       python3 python3-libs python3-gobject

%description
Control and monitor local and remote Folding@home clients

%prep
%setup -q -n %{name}-%{version}-%{release}

%build
%py3_build

%install
%py3_install
desktop-file-install --dir=${RPM_BUILD_ROOT}%{_datadir}/applications FAHControl.desktop

%files
%{_bindir}/FAHControl
%{_datadir}/applications/*
%{_datadir}/pixmaps/*
%license LICENSE.txt
%{python3_sitelib}/*


%changelog
* Sat Apr 25 2020 Guy Streeter <guy.streeter@gmail.com> - 0.0.1-1
- COPR build targets do not have python(3)-rpm-macros installed?
- Work around Fedora BZ 1827811 at the same time

* Fri Apr 24 2020 Guy Streeter <guy.streeter@gmail.com> - 0.0-1
- Initial attempt at spec file.
