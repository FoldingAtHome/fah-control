# TODO: Insert Copyright and Licensing statements

%global source_date_epoch_from_changelog 1
%global debug_package %{nil}

Name:           fahcontrol
# TODO: What is the version
Version:        0.0
Release:        1%{?dist}
Summary:        Folding@Home Control

License:        GPLv3+
URL:            https://foldingathome.org
Source0:        %{name}-%{version}-%{release}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-setuptools
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
* Fri Apr 24 2020 Guy Streeter <guy.streeter@gmail.com> - 0.0-1
- Initial attempt at spec file.
