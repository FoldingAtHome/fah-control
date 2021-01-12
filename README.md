Folding@home Client Advanced Control
====================================

FAHControl can monitor and control one or more FAHClients.

To run:

    python FAHControl

See: https://foldingathome.org/

# Prerequisites

## Debian / Ubuntu

    sudo apt-get install -y python3-stdeb python3-gi python3-all python3-six debhelper \
      dh-python gir1.2-gtk-3.0

## RedHat / CentOS

    sudo yum install -y python3-gobject python3-six
    
## Arch Linux / Manjaro

    sudo pacman -S python python-setuptools python-gobject python-six
    
Alternatively, use the unofficial [AUR package](https://aur.archlinux.org/packages/fahcontrol/) (or [this one for the GTK3/Python3 fork](https://aur.archlinux.org/packages/fahcontrol-gtk3-git)

## Windows (MinGW in MSYS2)

    pacman -S mingw-w64-x86_64-{gtk3,python-{cx_Freeze,gobject,six}}
