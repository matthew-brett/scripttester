# Test basic script finding

import os
import sys
from os.path import join as pjoin, dirname, abspath, isdir, realpath, pathsep
import shutil
import stat

try:
    NotFoundError = FileNotFoundError
except NameError:
    NotFoundError = OSError

from scriptrunner import ScriptRunner

import pytest

MYPKG_PATH = abspath(pjoin(dirname(__file__), 'mypkg66'))


def test_local(tmpdir, rollback_modules, cwd_on_path):
    shutil.copytree(MYPKG_PATH, 'pkg_dir')
    assert isdir(pjoin('pkg_dir', 'scripts'))
    os.chdir('pkg_dir')
    # Check we can instantiate with string, and module
    import mypkg66 as my_module
    assert realpath(dirname(my_module.__file__)) == realpath('mypkg66')
    for rooter in ('mypkg66', my_module):
        runner = ScriptRunner(rooter)
        assert runner.local_script_dir == realpath('scripts')
        assert runner.local_module_dir == realpath('.')
        assert runner.run_command('mypkg66_script') == (0, b'my script\n', b'')
        assert runner.run_command(['mypkg66_script']) == (0, b'my script\n', b'')
        assert (runner.run_command(['mypkg66_script', 'foo']) ==
                (0, b'my script+foo\n', b''))
    # Wrong script directory, fails
    runner = ScriptRunner('mypkg66', 'bin')
    with pytest.raises(NotFoundError):
        runner.run_command('mypkg66_script')
    # Until we rename the script directory
    os.rename('scripts', 'bin')
    runner = ScriptRunner('mypkg66', 'bin')
    assert runner.run_command('mypkg66_script') == (0, b'my script\n', b'')
    # Change file indicating containing directory
    runner = ScriptRunner('mypkg66', 'bin', 'foo.cfg')
    assert runner.local_script_dir is None
    assert runner.local_module_dir == realpath('.')
    with pytest.raises(NotFoundError):
        runner.run_command('mypkg66_script')
    # Put file at expected location
    os.rename('setup.py', 'foo.cfg')
    runner = ScriptRunner('mypkg66', 'bin', 'foo.cfg')
    assert runner.local_script_dir == realpath('bin')
    assert runner.local_module_dir == realpath('.')
    assert runner.run_command('mypkg66_script') == (0, b'my script\n', b'')


def prepare_unix_script(script_path):
    # Rewrite first line, make executable
    with open(script_path, 'rt') as fobj:
        lines = fobj.readlines()
    lines[0] = '#!{}\n'.format(sys.executable)
    with open(script_path, 'wt') as fobj:
        fobj.write(''.join(lines))
    os.chmod(script_path, stat.S_IRUSR | stat.S_IXUSR)


def prepare_windows_script(script_path):
    # Give up, rewrite as .bat file
    with open(script_path + '.bat', 'wt') as fobj:
        fobj.write('@echo my script')


def test_system(tmpdir,
                rollback_modules,
                restore_python_path,
                restore_system_path):
    # Simulate installed module
    shutil.copytree(MYPKG_PATH, 'pkg_dir')
    orig_script_dir = pjoin('pkg_dir', 'scripts')
    shutil.move(orig_script_dir, 'script_dir')
    assert not isdir(orig_script_dir)
    sys.path.insert(0, 'pkg_dir')
    # We should now be able to import
    import mypkg66 as my_module
    assert (realpath(dirname(my_module.__file__)) ==
            realpath(pjoin('pkg_dir', 'mypkg66')))
    # Put scripts on system PATH
    os.environ["PATH"] = os.environ["PATH"] + pathsep + 'script_dir'
    script_path = pjoin('script_dir', 'mypkg66_script')
    if os.name != 'nt':
        prepare_unix_script(script_path)
    else:
        prepare_windows_script(script_path)
    for rooter in ('mypkg66', my_module):
        runner = ScriptRunner(rooter)
        assert runner.local_script_dir == None
        assert runner.local_module_dir == None
        assert runner.run_command('mypkg66_script') == (0, b'my script\n', b'')
        assert runner.run_command(['mypkg66_script']) == (0, b'my script\n', b'')