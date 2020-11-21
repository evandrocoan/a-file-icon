import os
import shutil
import sublime
import threading

from textwrap import dedent

from .icons import icons_json_content
from .utils import path
from .utils.logging import log, dump

__all__ = ["check", "enable", "disable"]

HAS_FIND_SYNTAX = hasattr(sublime, "list_syntaxes")

EMPTY_TEMPLATE = dedent(
    """
    %YAML 1.2
    ---
    name: {0}
    scope: {1}
    hidden: true
    file_extensions:
      - {2}
    contexts:
      main: []
    """
).lstrip()

if int(sublime.version()) > 4075:
    MAIN_TEMPLATE = dedent(
        """
        %YAML 1.2
        ---
        name: {0}
        scope: {1}
        hidden: true
        file_extensions:
          - {2}
        contexts:
          main:
            - include: scope:{3}
              apply_prototype: true
        """
    ).lstrip()

else:
    MAIN_TEMPLATE = dedent(
        """
        %YAML 1.2
        ---
        name: {0}
        scope: {1}
        hidden: true
        file_extensions:
          - {2}
        contexts:
          main:
            - include: scope:{3}#prototype
            - include: scope:{3}
        """
    ).lstrip()


def check(desired_state):
    if desired_state:
        enable()
    else:
        disable()


def disable():
    log("Disabling aliases")
    shutil.rmtree(path.overlay_cache_path(), ignore_errors=True)
    shutil.rmtree(path.overlay_aliases_path(), ignore_errors=True)


def enable():
    AsyncAliasCreator().start()


class AsyncAliasCreator(threading.Thread):
    def run(self):
        self.dest_path = path.overlay_aliases_path()

        try:
            os.makedirs(self.dest_path)
        except FileExistsError:
            log("Updating aliases")
        else:
            log("Enabling aliases")

        if HAS_FIND_SYNTAX:
            # Built a set of scopes from visible/real syntaxes.
            # Note: Existing aliases in the overlay are hidden and thus excluded
            #       by default. Also ignore possible aliases or special purpose
            #       syntaxes from 3rd-party packages.
            self.real_syntax = {
                s.scope for s in sublime.list_syntaxes() if not s.hidden
            }

            for file_type in icons_json_content().values():
                self._create_aliases(file_type.get("aliases", []))
                self._create_aliases(file_type.get("syntaxes", []))

        else:
            # Sublime Text does not support on demand alias creation.
            self.real_syntax = set()

            for file_type in icons_json_content().values():
                self._create_aliases(file_type.get("aliases", []))

    def _has_real_syntax(self, selector):
        selector = [s.strip() for s in selector.split(",")]
        for scope in selector:
            if scope.strip() in self.real_syntax:
                return True
        return False

    def _create_aliases(self, syntaxes):
        for syntax in syntaxes:
            if self._has_real_syntax(syntax["scope"]):
                self._delete_alias_file(syntax)
            elif "extensions" in syntax:
                self._create_alias_file(syntax)

    def _create_alias_file(self, alias):
        name = alias["name"]
        scope = alias["scope"].split(",", 1)[0]
        exts = "\n  - ".join(alias["extensions"])
        base = alias.get("base")

        path = os.path.join(self.dest_path, name + ".sublime-syntax")
        try:
            with open(path, "x", encoding="utf-8") as out:
                if base:
                    out.write(MAIN_TEMPLATE.format(name, scope, exts, base))
                else:
                    out.write(EMPTY_TEMPLATE.format(name, scope, exts, base))
        except FileExistsError:
            pass
        except Exception as error:
            dump(error)

    def _delete_alias_file(self, alias):
        alias_path = os.path.join(self.dest_path, alias["name"] + ".sublime-syntax")

        try:
            os.remove(alias_path)
        except FileNotFoundError:
            pass
        except Exception as error:
            dump(error)
