# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019  KeenTools

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# ##### END GPL LICENSE BLOCK #####

import logging

import bpy

from ..config import Config
from ..blender_independent_packages.pykeentools_loader import (
    module as pkt_module, is_installed as pkt_is_installed)
from ..blender_independent_packages.pykeentools_loader.install import (
    pre_download_async, PartInstallation, updates_downloaded,
    remove_download, install_download, download_file_version_path,
    downloaded_keentools_version)

from ..utils.html import parse_html, skip_new_lines_and_spaces, render_main


def mock_response():
    response = lambda: None
    response.description_url = 'https://keentools.io/downloads'
    response.download_url = 'https://keentools.io/downloads'
    response.message = "<h3>What's New in KeenTools 1.5.9</h3>\n" \
                       "<ul>\n  " \
                       "<li>fixed performance issues in Nuke 12;</li>\n  " \
                       "<li>pintooling performance improvements;</li>\n  " \
                       "<li>fixed large frame numbers bug;</li>\n  " \
                       "<li>fixed invisible model in macOS Catalina;</li>\n " \
                       "<li>minor fixes and improvements</li>\n" \
                       "</ul>\n<br />\n"
    response.plugin_name = 'FaceBuilder'
    response.version = pkt_module().Version(1, 5, 9)
    return response


class FBUpdater:
    _response = None
    _response = mock_response()  # Mock for testing (1/2)
    _parsed_response_content = None

    @classmethod
    def is_active(cls):
        return cls.has_response_message() and (not updates_downloaded() or
                                               downloaded_keentools_version() != str(cls.version()))

    @classmethod
    def has_response_message(cls):
        return cls._parsed_response_content is not None

    @classmethod
    def set_response(cls, val):
        cls._response = val

    @classmethod
    def get_response(cls):
        return cls._response

    @classmethod
    def get_parsed(cls):
        return cls._parsed_response_content

    @classmethod
    def set_parsed(cls, val):
        cls._parsed_response_content = val

    @classmethod
    def clear_message(cls):
        cls.set_response(None)
        cls.set_parsed(None)

    @classmethod
    def render_message(cls, layout):
        parsed = cls.get_parsed()
        if parsed is not None:
            render_main(layout, parsed)

    @classmethod
    def get_update_checker(cls):
        pykeentools = pkt_module()
        platform = 'Blender'
        ver = pykeentools.Version(*bpy.app.version)
        uc = pykeentools.UpdatesChecker.instance(platform, ver)
        return uc

    @classmethod
    def version(cls):
        return cls.get_response().version

    @classmethod
    def init_updater(cls):
        if cls.has_response_message() or not pkt_is_installed():
            return

        uc = cls.get_update_checker()
        res = uc.check_for_updates('FaceBuilder')
        res = cls.get_response()  # Mock (2/2)
        if res is not None:
            cls.set_response(res)
            parsed = parse_html(skip_new_lines_and_spaces(res.message))
            cls.set_parsed(parsed)


class FB_OT_DownloadTheUpdate(bpy.types.Operator):
    bl_idname = Config.fb_download_the_update_idname
    bl_label = 'Download the update'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Download the latest version of addon and core'

    def execute(self, context):
        pre_download_async(part_installation=PartInstallation.CORE)
        pre_download_async(part_installation=PartInstallation.ADDON)
        with open(str(download_file_version_path()), 'w') as f:
            print(FBUpdater.version(), file=f)
        return {'FINISHED'}


class FB_OT_RemindLater(bpy.types.Operator):
    bl_idname = Config.fb_remind_later_idname
    bl_label = 'Remind later'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Remind about this update tomorrow'

    def execute(self, context):
        logger = logging.getLogger(__name__)
        logger.debug('REMIND LATER')

        uc = FBUpdater.get_update_checker()
        res = FBUpdater.get_response()
        uc.pause_update(res.plugin_name, res.version)
        FBUpdater.clear_message()
        return {'FINISHED'}


class FB_OT_SkipVersion(bpy.types.Operator):
    bl_idname = Config.fb_skip_version_idname
    bl_label = 'Skip this version'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Skip this version'

    def execute(self, context):
        logger = logging.getLogger(__name__)
        logger.debug('SKIP THIS VERSION')

        uc = FBUpdater.get_update_checker()
        res = FBUpdater.get_response()
        uc.skip_update(res.plugin_name, res.version)
        FBUpdater.clear_message()
        return {'FINISHED'}


MIN_TIME_BETWEEN_REMINDERS = 86400  # 24 hours in seconds


class FBInstallationReminder:
    _message_text = 'The update {} is ready to be installed. ' \
                    'Blender will be relaunched after installing the update automatically. ' \
                    'Please save your project before continuing. Proceed?'.format(FBUpdater.version())
    _last_reminder_time = None

    @classmethod
    def is_active(cls):
        import time
        return not FBUpdater.is_active() and updates_downloaded() and \
               (cls._last_reminder_time is None or
                time.time() - cls._last_reminder_time > MIN_TIME_BETWEEN_REMINDERS) and \
               downloaded_keentools_version() != Config.addon_version

    @classmethod
    def render_message(cls, layout):
        if cls.is_active():
            render_main(layout, parse_html(cls._message_text))

    @classmethod
    def remind_later(cls):
        import time
        cls._last_reminder_time = time.time()


class FB_OT_InstallUpdates(bpy.types.Operator):
    bl_idname = Config.fb_install_updates_idname
    bl_label = 'Install updates and close blender'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Install updates and close blender'

    def execute(self, context):
        install_download(PartInstallation.ADDON)
        install_download(PartInstallation.CORE)
        remove_download(PartInstallation.CORE)
        remove_download(PartInstallation.ADDON)
        bpy.ops.wm.quit_blender()
        return {'FINISHED'}


class FB_OT_RemindInstallLater(bpy.types.Operator):
    bl_idname = Config.fb_remind_install_later_idname
    bl_label = 'Remind install tommorow'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Remind install tommorow'

    def execute(self, context):
        FBInstallationReminder.remind_later()
        return {'FINISHED'}


class FB_OT_SkipInstallation(bpy.types.Operator):
    bl_idname = Config.fb_skip_installation_idname
    bl_label = 'Skip installation'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = 'Skip installation'

    def execute(self, context):
        remove_download(PartInstallation.ADDON)
        remove_download(PartInstallation.CORE)
        return {'FINISHED'}
