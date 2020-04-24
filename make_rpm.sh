#!/bin/sh

# NOTE the python-rpm-macros and python3-rpm-macros packages must be installed.

PACKAGE=fahcontrol
VERSION=$(rpmspec -q --qf '%{VERSION}' ${PACKAGE}.spec | cut -d' ' -f1)
RELEASE=$(rpmspec -q --qf '%{RELEASE}' ${PACKAGE}.spec | sed -e 's/\.[^.]*$$//')
VER_REL=${VERSION}-${RELEASE}
RPM_TARBALL=rpm/SOURCES/${PACKAGE}-${VER_REL}.tar.gz


rm -rf rpm/{SOURCES,BUILD,BUILDROOT,SPECS,RPMS,SRPMS}/*
mkdir -p rpm/SOURCES # {SOURCES,BUILD,RPMS,SRPMS}
git archive --format=tar --prefix=${PACKAGE}-${VER_REL}/ HEAD | gzip -9 > ${RPM_TARBALL}
rpmbuild -ba --define "_topdir ${PWD}/rpm" ${PACKAGE}.spec
# fedpkg --release f31 local
