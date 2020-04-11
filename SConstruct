# Setup
import os
env = Environment(ENV = os.environ)
try:
    env.Tool('config', toolpath = [os.environ.get('CBANG_HOME')])
except Exception, e:
    raise Exception, 'CBANG_HOME not set?\n' + str(e)

env.CBLoadTools('packager run_distutils osx fah-client-version')
env.CBAddVariables(
    BoolVariable('cross_mingw', 'Build with mingw cross compiler', 0))
conf = env.CBConfigure()

# Version
try:
    version = env.FAHClientVersion()
except Exception, e:
    print(e)
    version = '0.0.0'
    env.Replace(PACKAGE_VERSION = version)

f = open('version.txt', 'w')
f.write(version)
f.close()

if env['PLATFORM'] != 'darwin': env['package_arch'] = 'noarch'

# Build
target_dir = None
if env['PLATFORM'] == 'darwin':
    env['RUN_DISTUTILSOPTS'] = 'py2app'
    target_dir = 'dist/FAHControl.app'

elif env['PLATFORM'] == 'win32' or int(env.get('cross_mingw', 0)):
    env['RUN_DISTUTILSOPTS'] = 'build'
    target_dir = 'gui'
    target_pat = '' # Not packaged here

elif env.GetPackageType() == 'deb':
    env['RUN_DISTUTILSOPTS'] = ['--command-packages=stdeb.command', 'bdist_deb']
    target_dir = 'deb_dist'
    target_pat = 'deb_dist/fahcontrol_%s-*.deb' % version

# Run distutils
gui = None
if env.GetPackageType() != 'rpm':
    # Cleanup old GUI build
    # Note: py2app does not work correctly if the old .app is still around
    import shutil
    shutil.rmtree(target_dir, True)

    if int(env.get('cross_mingw', 0)):
        # Use the cross compiled Python
        gui = env.Command(target_dir, 'setup.py', 'python2.exe setup.py build')
    else:
        gui = env.RunDistUtils(Dir(target_dir), 'setup.py')

    Default(gui)
    AlwaysBuild(gui)


# Package
if env['PLATFORM'] == 'darwin' or env.GetPackageType() == 'rpm':
    pkg = env.Packager(
        'FAHControl',

        version = version,
        maintainer = 'Joseph Coffland <joseph@cauldrondevelopment.com>',
        vendor = 'Folding@home',
        url = 'https://foldingathome.org/',
        license = 'LICENSE.txt',
        bug_url = 'https://apps.foldingathome.org/bugs/',
        summary = 'Folding@home Control',
        description = \
            'Control and monitor local and remote Folding@home clients',
        prefix = '/usr',

        documents = ['README.md', 'CHANGELOG.md', 'LICENSE.txt'],
        desktop_menu = ['FAHControl.desktop'],
        icons = ['images/FAHControl.png'],

        rpm_license = 'GPL v3+',
        rpm_group = 'Applications/Internet',
        rpm_requires = 'python, pygtk2',
        rpm_build = 'rpm/build',
        rpm_filelist = 'filelist.txt',

        pkg_id = 'org.foldingathome.fahcontrol.pkg',
        pkg_resources = 'osx/Resources',
        pkg_apps = [['dist/FAHControl.app', 'Folding@home/FAHControl.app']],
        pkg_scripts = 'osx/scripts',
        pkg_target = '10.6',
        pkg_distribution = 'osx/distribution.xml',
        )

    AlwaysBuild(pkg)
    env.Alias('package', pkg)
    if gui is not None: Depends(pkg, gui)

else:
    # Write package.txt
    def write_filename(target, source, env):
        import glob
        filename = str(Glob(target_pat)[0])
        open(str(target[0]), 'w').write(filename)

    bld = Builder(action = write_filename)
    env.Append(BUILDERS = {'WriteFilename' : bld})
    cmd = env.WriteFilename('package.txt', [])
    AlwaysBuild(cmd)
    if gui is not None: Depends(cmd, gui)

    env.Alias('package', [cmd])
