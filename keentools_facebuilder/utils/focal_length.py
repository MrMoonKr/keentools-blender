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

__all__ = [
    'auto_focal_configuration_and_update',
    'configure_focal_mode_and_fixes',
    'update_camera_focal'
]

import contextlib

from . import coords
from ..config import Config, get_main_settings


def _unfix_all(fb, head):
    for cam in head.cameras:
        fb.set_focal_length_fixed_at(cam.get_keyframe(), False)


def _fix_all_except_this(fb, head, exclude_kid):
    for cam in head.cameras:
        fb.set_focal_length_fixed_at(cam.get_keyframe(),
                                     cam.get_keyframe() != exclude_kid)


def _unfix_not_in_groups(fb, head):
    for cam in head.cameras:
        fb.set_focal_length_fixed_at(
            cam.get_keyframe(),
            cam.is_in_group()
            or not cam.auto_focal_estimation)


def configure_focal_mode_and_fixes(fb, head, camera):
    if head.smart_mode():
        if camera.auto_focal_estimation:
            if camera.is_in_group():
                proj_mat = camera.get_projection_matrix()
                fb.set_static_focal_length_estimation(coords.focal_by_projection_matrix_px(proj_mat))
            else:  # image_group in (-1, 0)
                fb.set_varying_focal_length_estimation()
                for cam in head.cameras:
                    fb.set_focal_length_fixed_at(
                        cam.get_keyframe(),
                        cam.image_group > 0
                        or not cam.auto_focal_estimation)
        else:
            fb.set_varying_focal_length_estimation()
            _unfix_not_in_groups(fb, head)
    else:  # Override all
        if head.manual_estimation_mode == 'all_different':
            fb.set_varying_focal_length_estimation()
            _unfix_all(fb, head)
        elif head.manual_estimation_mode == 'current_estimation':
            fb.set_varying_focal_length_estimation()
            _fix_all_except_this(fb, head, kid)
        elif head.manual_estimation_mode == 'same_focus':
            proj_mat = camera.get_projection_matrix()
            fb.set_static_focal_length_estimation(coords.focal_by_projection_matrix_px(proj_mat))
        elif head.manual_estimation_mode == 'force_focal':
            fb.disable_focal_length_estimation()
        else:
            assert False, 'Unknown mode: {}'.format(
                head.manual_estimation_mode)


def _get_keyframe_focal(fb, keyframe_id):
    proj_mat = fb.projection_mat(keyframe_id)
    focal = coords.focal_by_projection_matrix_mm(
        proj_mat, Config.default_sensor_width)

    # Fix for Vertical camera (because Blender has Auto in sensor)
    rx, ry = coords.render_frame()
    if ry > rx:
        focal = focal * rx / ry
    return focal


def update_camera_focal(camera, fb):
    kid = camera.get_keyframe()
    focal = _get_keyframe_focal(fb, kid)
    camera.camobj.data.lens = focal
    camera.focal = focal


@contextlib.contextmanager
def auto_focal_configuration_and_update(fb, headnum, camnum):
    settings = get_main_settings()
    head = settings.get_head(headnum)
    camera = head.get_camera(camnum)
    configure_focal_mode_and_fixes(fb, head, camera)
    yield
    update_camera_focal(camera, fb)
