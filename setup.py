#!/usr/bin/env python3
import sys
import os
import inspect

dir = os.path.dirname(inspect.getfile(inspect.currentframe()))
if dir == '':
    dir = '.'

print('dir = %s' % dir)

os.chdir(dir)

# Convert glade data
in_file = 'fah/FAHControl.glade'
out_file = 'fah/FAHControl_glade.py'

if os.path.exists(in_file):
    input = None
    output = None
    try:
        input = open(in_file, 'r', encoding="utf8")
        output = open(out_file, 'w', encoding="utf8")

        output.write('# -*- coding: utf8 -*-\n\n')
        output.write('glade_data = """')
        output.write(input.read())
        output.write('"""\n')
    finally:
        if input is not None:
            input.close()
        if output is not None:
            output.close()


# Bootstrap
try:
    import ez_setup
    ez_setup.use_setuptools()
except:
    pass

app = 'FAHControl'

if sys.platform == 'darwin':
    from setuptools import setup

    plist = dict(
        CFBundleDisplayName='FAHControl',
        CFBundleIdentifier='org.foldingathome.fahcontrol',
        CFBundleSignature='????',
        NSHumanReadableCopyright='Copyright 2010-2018 foldingathome.org',
    )

    options = dict(
        argv_emulation=False,
        includes='cairo, pango, pangocairo, atk, gobject, gio',
        iconfile='images/FAHControl.icns',
        resources=['/opt/local/share/themes', 'osx/entitlements.plist'],
        plist=plist,
    )

    extra_opts = dict(
        app=[app],
        options={'py2app': options},
        setup_requires=['py2app'],
    )

    # Hack around py2app problem with python scripts with out .py extension.
    from py2app.util import PY_SUFFIXES
    PY_SUFFIXES.append('')

elif sys.platform == 'win32':
    from cx_Freeze import setup, Executable

    # Need to search for include files
    # from https://github.com/achadwick/hello-cxfreeze-gtk/blob/master/setup.py
    # FIXME: the same issue may happen with py2app. Check that too.
    common_include_files = []
    required_dll_search_paths = os.getenv("PATH", os.defpath).split(os.pathsep)
    required_dlls = [
        "libgtk-3-0.dll",
        "libgdk-3-0.dll",
        "libepoxy-0.dll",
        "libgdk_pixbuf-2.0-0.dll",
        "libpango-1.0-0.dll",
        "libpangocairo-1.0-0.dll",
        "libpangoft2-1.0-0.dll",
        "libpangowin32-1.0-0.dll",
        "libatk-1.0-0.dll",
    ]
    for dll in required_dlls:
        dll_path = None
        for p in required_dll_search_paths:
            p = os.path.join(p, dll)
            if os.path.isfile(p):
                dll_path = p
                break
        assert dll_path is not None, "Unable to locate {} in {}".format(
            dll,
            required_dll_search_paths,
        )
        common_include_files.append((dll_path, dll))

    # We need the .typelib files at runtime.
    # The related .gir files are in $PREFIX/share/gir-1.0/$NS.gir,
    # but those can be omitted at runtime.

    required_gi_namespaces = [
        "Gtk-3.0",
        "Gdk-3.0",
        "cairo-1.0",
        "Pango-1.0",
        "GObject-2.0",
        "GLib-2.0",
        "Gio-2.0",
        "GdkPixbuf-2.0",
        "GModule-2.0",
    ]

    for ns in required_gi_namespaces:
        subpath = "lib/girepository-1.0/{}.typelib".format(ns)
        fullpath = os.path.join(sys.prefix, subpath)
        assert os.path.isfile(fullpath), "Required file {} is missing".format(
            fullpath,
        )
        common_include_files.append((fullpath, subpath))

    # Need pixbuf loaders.
    PIXPATH = 'lib/gdk-pixbuf-2.0/2.10.0'
    for root, _, files in os.walk(f"{sys.prefix}/{PIXPATH}", onerror=print):
        for f in files:
            if f.endswith('.a'):
                continue
            realpath = f"{root}/{f}"
            subpath = realpath[len(sys.prefix):]
            print((realpath, subpath))
            common_include_files.append((realpath, subpath))


    # Change base to 'Console' for debugging
    e = Executable(app, base='Win32GUI', icon='images/FAHControl.ico')
    options = {
        'build_exe': {
            'build_exe': 'gui',
            'packages': 'gi',
            'include_files': common_include_files,
        }
    }
    extra_opts = dict(executables=[e], options=options)

else:
    from setuptools import setup, find_packages

    extra_opts = dict(
        packages=find_packages(),
        scripts=[app],
        data_files=[
            ('/usr/share/pixmaps', ['images/FAHControl.png', 'images/FAHControl.ico'])],
        install_requires='pygobject >= 3.0',
        include_package_data=True,
    )

try:
    version = open('version.txt').read().strip()
    version.split('.')
except:
    version = '0.0.0'

if not os.path.exists('fah/Version.py') or version != '0.0.0':
    open('fah/Version.py', 'w').write('version = \'%s\'\n' % version)

description = \
    '''Folding@home is a distributed computing project using volunteered
computer resources.
'''
short_description = '''
This package contains FAHControl, a graphical monitor and control
utility for the Folding@home client. It gives an overview of running
projects on the local and optional (remote) machines. Starting,
stopping and pausing of the running projects is also possible, as is
viewing the logs. It provides an Advanced view with
additional information and settings for enthusiasts and gurus.'''

description += short_description

setup(
    name='FAHControl',
    version=version,
    description='Folding@home Client Control',
    long_description=description,
    author='Joseph Coffland',
    author_email='joseph@cauldrondevelopment.com',
    license='GNU General Public License version 3',
    keywords='protein, molecular dynamics, simulation',
    url='https://foldingathome.org/',
    package_data={'fah': ['*.glade']},
    python_requires='>=3.5',
    **extra_opts)

if sys.platform == 'darwin':
    with open('package-description.txt', 'w') as f:
        f.write(short_description.strip())
