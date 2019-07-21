import json
import os
import shutil
import zipfile

import sublime

from ..common.utils import path
from ..common.utils.logging import log, dump


def init():
    log("Initializing icons")

    try:
        general_path = path.overlay_patches_general_path()
        if os.path.isdir(general_path):
            dump("All the necessary icons are provided")
        else:
            _init_overlay(general_path)
    except Exception as error:
        log("Error during copy")
        dump(error)


def _init_overlay(dest):
    """Create the icon overlay package.

    In order to make sure to override existing icons provided by the themes
    icons need to be copied to a package, which is loaded as late as possible.

    This function therefore creates a package named `zzz A File Icon zzz` and
    copies all icons over there.
    """
    # initializes path variables
    dest_multi = os.path.join(dest, "multi")
    dest_single = os.path.join(dest, "single")

    # copy icons from the loosen package folder
    src = path.package_icons_path()
    try:
        shutil.copytree(os.path.join(src, "single"), dest_single)
    except FileNotFoundError:
        os.makedirs(dest_single, exist_ok=True)

    try:
        shutil.copytree(os.path.join(src, "multi"), dest_multi)
    except FileNotFoundError:
        os.makedirs(dest_multi, exist_ok=True)

    # extract remaining icons from the package archive
    try:
        with zipfile.ZipFile(path.installed_package_path(), "r") as z:
            for m in z.namelist():
                if m.startswith("icons/single") or m.startswith("icons/multi"):
                    _, color, name = m.split("/")
                    try:
                        with open(os.path.join(dest, color, name), "xb") as f:
                            f.write(z.read(m))
                    except FileExistsError:
                        pass
    except FileNotFoundError:
        pass


def copy_missing(source, overlay, package):
    log("Checking icons for {}...".format(package))

    try:
        missing_icons = _get_missing(package)
        if missing_icons:
            _copy_missing(source, overlay, package, "multi", missing_icons)
            _copy_missing(source, overlay, package, "single", missing_icons)
        return bool(missing_icons)
    except Exception as error:
        log("Error during copy")
        dump(error)
    return False


def _copy_missing(source, overlay, package, color, icons):
    src = os.path.join(source, color)
    dest = path.makedirs(overlay, package, color)
    for icon in icons:
        _copy(src, dest, icon + ".png")
        for i in range(2, 4):
            _copy(src, dest, "{}@{}x.png".format(icon, i))


def _copy(src, dest, icon):
    try:
        with open(os.path.join(dest, icon), "xb") as df:
            with open(os.path.join(src, icon), "rb") as sf:
                df.write(sf.read())
    except FileExistsError:
        pass


def _get_missing(package):
    package_icons = json.loads(sublime.load_resource(path.icons_json_path()))
    theme_icons_path = _icons_path(package)
    if not theme_icons_path:
        return package_icons

    theme_icons = {
        os.path.basename(os.path.splitext(i)[0])
        for i in sublime.find_resources("*.png")
        if i.startswith(theme_icons_path)
    }

    return [icon for icon in package_icons if icon not in theme_icons]


def _icons_path(package):
    package_path = "Packages/" + package
    for res in sublime.find_resources("file_type_default.png"):
        if res.startswith(package_path):
            return os.path.dirname(res)
    return False
