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

from ..addon_config import Config, get_operator, ErrorType
from ..facebuilder_config import FBConfig, get_fb_settings
from ..facebuilder.fbloader import FBLoader
from . import attrs
from ..facebuilder.utils import cameras
from ..facebuilder.utils.exif_reader import (read_exif_to_camera, auto_setup_camera_from_exif)
from ..blender_independent_packages.pykeentools_loader import module as pkt_module
from .localview import enter_context_localview, exit_context_localview


def _is_keentools_object(obj):
    return FBConfig.version_prop_name in obj.keys()


def _get_serial(obj):
    return attrs.get_safe_custom_attribute(obj, FBConfig.fb_serial_prop_name)


def _get_dir_name(obj):
    return attrs.get_safe_custom_attribute(obj, FBConfig.fb_dir_prop_name)


def _get_image_names(obj):
    return attrs.get_safe_custom_attribute(obj, FBConfig.fb_images_prop_name)


def _check_facs_available(count):
    try:
        return pkt_module().FacsExecutor.facs_available(count)
    except pkt_module().ModelLoadingException as err:
        logger = logging.getLogger(__name__)
        logger.error('_check_facs_available ModelLoadingException: {}'.format(str(err)))
    except Exception as err:
        logger = logging.getLogger(__name__)
        logger.error('_check_facs_available Unknown Exception: {}'.format(str(err)))
    return False


# Scene States and Head number. All States are:
# RECONSTRUCT, NO_HEADS, THIS_HEAD, ONE_HEAD, MANY_HEADS, PINMODE
# ------------
def what_is_state():
    def _how_many_heads():
        settings = get_fb_settings()
        unknown_headnum = -1
        heads_count = len(settings.heads)
        if heads_count == 0:
            return 'NO_HEADS', unknown_headnum
        elif heads_count == 1:
            return 'ONE_HEAD', 0
        else:
            return 'MANY_HEADS', unknown_headnum

    context = bpy.context
    settings = get_fb_settings()
    unknown_headnum = -1

    if settings.pinmode:
        return 'PINMODE', settings.current_headnum

    obj = context.object

    if not obj:
        return _how_many_heads()

    if not _is_keentools_object(obj):
        if obj.type == 'MESH':
            if _check_facs_available(len(obj.data.vertices)):
                return 'FACS_HEAD', unknown_headnum
        return _how_many_heads()

    if obj.type == 'MESH':
        ind = settings.find_head_index(obj)
        if ind >= 0:
            return 'THIS_HEAD', ind
        else:
            return 'RECONSTRUCT', unknown_headnum

    elif obj.type == 'CAMERA':
        ind, _ = settings.find_cam_index(obj)
        if ind >= 0:
            return 'THIS_HEAD', ind
        else:
            return _how_many_heads()

    return _how_many_heads()


def get_current_headnum():
    state, headnum = what_is_state()
    return headnum


def get_current_head():
    headnum = get_current_headnum()
    if headnum >= 0:
        settings = get_fb_settings()
        return settings.get_head(headnum)
    return None


def has_no_blendshape(obj):
    return not obj or obj.type != 'MESH' or not obj.data or \
           not obj.data.shape_keys


def has_blendshapes_action(obj):
    if obj and obj.type == 'MESH' \
           and obj.data.shape_keys \
           and obj.data.shape_keys.animation_data \
           and obj.data.shape_keys.animation_data.action:
        return True
    return False


def get_obj_from_context(context, force_fbloader=True):
    state, headnum = what_is_state()
    if state == 'FACS_HEAD':
        return context.object, 1.0
    else:
        if headnum < 0:
            return None, 1.0

        settings = get_fb_settings()
        head = settings.get_head(headnum)
        if not head:
            return None, 1.0

        if force_fbloader:
            FBLoader.load_model(headnum)
        return head.headobj, head.model_scale


def force_undo_push(msg='KeenTools operation'):
    inc_operation()
    bpy.ops.ed.undo_push(message=msg)


def push_head_in_undo_history(head, msg='KeenTools operation'):
    head.need_update = True
    force_undo_push(msg)
    head.need_update = False


def check_settings():
    settings = get_fb_settings()
    if not settings.check_heads_and_cams():
        heads_deleted, cams_deleted = settings.fix_heads()
        if heads_deleted == 0:
            warn = get_operator(Config.kt_warning_idname)
            warn('INVOKE_DEFAULT', msg=ErrorType.SceneDamaged)
        return False
    return True


# --------------------
def inc_operation():
    """ Debug purpose """
    settings = get_fb_settings()
    settings.opnum += 1


def get_operation():
    """ Debug purpose """
    settings = get_fb_settings()
    return settings.opnum
# --------------------


def select_object_only(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(state=True)
    bpy.context.view_layer.objects.active = obj


def reconstruct_by_head():
    """ Reconstruct Cameras and Scene structures by serial """
    logger = logging.getLogger(__name__)
    scene = bpy.context.scene
    rx = scene.render.resolution_x
    ry = scene.render.resolution_y
    settings = get_fb_settings()

    obj = bpy.context.object

    if obj.type != 'MESH':
        return

    if not _is_keentools_object(obj):
        return

    logger.debug('START RECONSTRUCT')

    params = cameras.get_camera_params(obj)
    if params is None:
        params = cameras.default_camera_params()
        logger.debug('DEFAULT CAMERA PARAMETERS GENERATED')
    logger.debug('PARAMS: {}'.format(params))

    serial_str = _get_serial(obj)
    if serial_str is None:
        serial_str = ""
    logger.debug("SERIAL")

    dir_name = _get_dir_name(obj)
    if dir_name is None:
        dir_name = ""
    logger.debug("DIR_NAME: {}".format(dir_name))

    images = _get_image_names(obj)
    if type(images) is not list:
        images = []
    logger.debug("IMAGES: {}".format(images))
    logger.debug("PARAMETERS LOADED. START HEAD CREATION")

    settings.fix_heads()
    headnum = len(settings.heads)
    head = settings.heads.add()
    head.headobj = obj

    try:
        head.store_serial_str_in_head_and_on_headobj(serial_str)
        fb = FBLoader.new_builder()
        head.sensor_width = params['sensor_width']
        head.sensor_height = params['sensor_height']
        head.focal = params['focal']
        head.use_emotions = False
        scene.render.resolution_x = params['frame_width']
        scene.render.resolution_y = params['frame_height']

        fb.deserialize(head.get_serial_str())
        logger.debug("RECONSTRUCT KEYFRAMES {}".format(str(fb.keyframes())))

        for i, kid in enumerate(fb.keyframes()):
            cam_ob = FBLoader.create_camera_object(headnum, i)
            camera = head.cameras.add()
            camera.camobj = cam_ob
            camera.set_keyframe(kid)

            filename = images[i]
            logger.debug("IMAGE {} {}".format(i, filename))
            img = bpy.data.images.new(filename, 0, 0)
            img.source = 'FILE'
            img.filepath = filename

            FBLoader.add_background_to_camera(headnum, i, img)

            read_exif_to_camera(headnum, i, filename)
            camera.orientation = camera.exif.orientation

            auto_setup_camera_from_exif(camera)

            logger.debug("CAMERA CREATED {}".format(kid))
            FBLoader.place_camera(headnum, i)
            FBLoader.update_camera_pins_count(headnum, i)

            attrs.mark_keentools_object(camera.camobj)

        FBLoader.update_cameras_from_old_version(headnum)

    except Exception:
        logger.error("WRONG PARAMETERS")
        for i, c in enumerate(reversed(head.cameras)):
            if c.camobj is not None:
                bpy.data.objects.remove(c.camobj, do_unlink=True)
            head.cameras.remove(i)
        settings.heads.remove(headnum)
        scene.render.resolution_x = rx
        scene.render.resolution_y = ry
        logger.info("SCENE PARAMETERS RESTORED")
        warn = get_operator(Config.kt_warning_idname)
        warn('INVOKE_DEFAULT', msg=ErrorType.CannotReconstruct)
        return


def get_vertex_groups(obj):
    vertices = obj.data.vertices
    vertex_groups = [x for x in obj.vertex_groups]
    vg_dict = {}
    for vg in vertex_groups:
        vg_dict[vg.name] = [[v.index, vg.weight(v.index)]
                            for v in vertices
                            if vg.index in [g.group for g in v.groups]]
    return vg_dict


def create_vertex_groups(obj, vg_dict):
    for vg_name in vg_dict.keys():
        if vg_name in obj.vertex_groups.keys():
            vg = obj.vertex_groups[vg_name]
        else:
            vg = obj.vertex_groups.new(name=vg_name)
        for i, w in vg_dict[vg_name]:
            vg.add([i], w, 'REPLACE')


def set_overlays(status=True):
    if not bpy.context.space_data:
        return
    bpy.context.space_data.overlay.show_floor = status
    bpy.context.space_data.overlay.show_axis_x = status
    bpy.context.space_data.overlay.show_axis_y = status
    bpy.context.space_data.overlay.show_cursor = status


def switch_to_camera(context, camobj, select_obj=None):
    exit_context_localview(context)
    camobj.hide_set(False)
    select_object_only(camobj)
    enter_context_localview(context)
    bpy.ops.view3d.object_as_camera()
    if select_obj is not None:
        select_object_only(select_obj)
