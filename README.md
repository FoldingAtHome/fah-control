Folding@home Client Advanced Control
====================================

FAHControl can monitor and control one or more FAHClients.

To run:

    python FAHControl

See: https://foldingathome.org/

# Prerequisites

## Debian / Ubuntu

    sudo apt-get install -y python3-stdeb python3-gi python3-all debhelper \
      dh-python gir1.2-gtk-3.0

## RedHat / CentOS

    sudo yum install -y python3-gobject

## Windows (MinGW in MSYS2)

    pacman -S mingw-w64-x86_64-{gtk3,python3-{cx_Freeze,gobject}}
