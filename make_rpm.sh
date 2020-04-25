#!/bin/sh

# NOTE the python3-rpm-macros package must be installed.

PACKAGE=fahcontrol
VERSION=$(rpmspec -q --qf '%{VERSION}' ${PACKAGE}.spec | cut -d' ' -f1)
RELEASE=$(rpmspec -q --qf '%{RELEASE}' ${PACKAGE}.spec | sed -e 's/\.[^.]*$//')
VER_REL=${VERSION}-${RELEASE}
RPM_TARBALL=rpmbuild/SOURCES/${PACKAGE}-${VER_REL}.tar.gz


rm -rf rpmbuild/{SOURCES,BUILD,BUILDROOT,SPECS,RPMS,SRPMS}/*
mkdir -p rpmbuild/SOURCES # {SOURCES,BUILD,RPMS,SRPMS}
git archive --format=tar --prefix=${PACKAGE}-${VER_REL}/ HEAD | gzip -9 > ${RPM_TARBALL}
rpmbuild -ba --define "_topdir ${PWD}/rpmbuild" ${PACKAGE}.spec
