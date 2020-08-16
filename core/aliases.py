import os
import shutil
import sublime

from textwrap import dedent

from .icons import icons_json_content
from .utils import path
from .utils.logging import log, dump


def check(desired_state):
    if desired_state:
        enable()
    else:
        disable()


def enable():
    dest_path = path.overlay_aliases_path()
    try:
        os.makedirs(dest_path)
    except FileExistsError:
        log("Aliases already enabled")
        return

    log("Enabling aliases")

    # template to create alias syntax without pyyaml dependency
    if int(sublime.version()) > 4075:
        template = dedent(
            """
            %YAML 1.2
            ---
            name: {name}
            hidden: true
            file_extensions: {extensions}
            scope: {scope}
            contexts:
              main:
                - include: scope:{base}
                  apply_prototype: true
            """
        ).strip()

    else:
        template = dedent(
            """
            %YAML 1.2
            ---
            name: {name}
            hidden: true
            file_extensions: {extensions}
            scope: {scope}
            contexts:
              main:
                - include: scope:{base}#prototype
                - include: scope:{base}
            """
        ).strip()

    for file_type in icons_json_content().values():
        for alias in file_type.get("aliases", []):
            try:
                with open(
                    os.path.join(dest_path, alias["name"] + ".sublime-syntax"), "w"
                ) as out:
                    out.write(template.format(**alias))
            except Exception as error:
                dump(error)


def disable():
    log("Disabling aliases")
    shutil.rmtree(path.overlay_cache_path(), ignore_errors=True)
    shutil.rmtree(path.overlay_aliases_path(), ignore_errors=True)
