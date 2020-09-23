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


def find_tex_by_name(tex_name):
    tex_num = bpy.data.images.find(tex_name)
    if tex_num >= 0:
        return bpy.data.images[tex_num]
    return None


def remove_tex_by_name(name):
    tex = find_tex_by_name(name)
    if tex is not None:
        bpy.data.images.remove(tex)


def check_image_size(image):
    if not image or not image.size:
        return False
    w, h = image.size[:2]
    return w > 0 and h > 0


def safe_image_loading(blender_name, path):
    tex = find_tex_by_name(blender_name)
    if tex is not None:
        if check_image_size(tex):
            return tex
        else:
            remove_tex_by_name(blender_name)
    try:
        image = bpy.data.images.load(path)
        image.name = blender_name
    except Exception:
        logger = logging.getLogger(__name__)
        logger.error('Source texture for "{}" '
                     'is not found on path: {}'.format(blender_name, path))
        return None
    if not check_image_size(image):
        return None
    return image


def safe_image_in_scene_loading(blender_name, path):
    logger = logging.getLogger(__name__)
    tex = find_tex_by_name(blender_name)
    if tex is not None:
        if check_image_size(tex):
            return tex
        else:
            remove_tex_by_name(blender_name)
    try:
        image = bpy.data.images.load(path)
    except Exception:
        logger.error('Source texture for "{}" '
                     'is not found on path: {}'.format(blender_name, path))
        return None
    if not check_image_size(image):
        bpy.data.images.remove(image)
        logger.error('Source texture "{}" '
                     'has wrong format on path: {}'.format(blender_name, path))
        return None

    tex = bpy.data.images.new(blender_name,
                              width=image.size[0], height=image.size[1],
                              alpha=True, float_buffer=False)
    tex.pixels[:] = image.pixels[:]
    tex.pack()
    bpy.data.images.remove(image)
    return tex
