from __future__ import print_function

from pip._internal.cli.cmdoptions import make_target_python
from pip._internal.commands.install import InstallCommand

install_cmd = InstallCommand("install", "test")
options, _ = install_cmd.parse_args([])
target_python = make_target_python(options)
print("=========== SUPPORTED TAGS =============")
print(*target_python.get_tags(), sep="\n")
print("=========== END TAGS ===============")
