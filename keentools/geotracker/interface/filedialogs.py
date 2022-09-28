# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2022 KeenTools

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
import os
from typing import Any, Optional, List

import bpy
from bpy.types import MovieClip
from bpy_extras.io_utils import ImportHelper, ExportHelper

from ...addon_config import Config, get_operator
from ...geotracker_config import GTConfig, get_current_geotracker_item
from ...utils.images import set_background_image_by_movieclip
from ...utils.video import (convert_movieclip_to_frames,
                            load_movieclip,
                            get_movieclip_duration)
from ..gtloader import GTLoader
from ..utils.textures import bake_texture, preview_material_with_texture


_logger: Any = logging.getLogger(__name__)


def _log_output(message: str) -> None:
    global _logger
    _logger.debug(message)


def _log_error(message: str) -> None:
    global _logger
    _logger.error(message)


def _load_movieclip(dir_path: str, file_names: List[str]) -> Optional[MovieClip]:
    geotracker = get_current_geotracker_item()
    if not geotracker:
        return None

    new_movieclip = load_movieclip(dir_path, file_names)

    geotracker.movie_clip = new_movieclip
    set_background_image_by_movieclip(geotracker.camobj,
                                      geotracker.movie_clip)
    return new_movieclip


class GT_OT_SequenceFilebrowser(bpy.types.Operator, ImportHelper):
    bl_idname = GTConfig.gt_sequence_filebrowser_idname
    bl_label = 'Open frame sequence'
    bl_description = 'Load image sequence. ' \
                     'Just select first image in sequence'

    filter_glob: bpy.props.StringProperty(
        default='*.jpg;*.jpeg;*.png;*.tif;*.tiff;*.bmp;*.mp4;*.avi;*.mov;*.mpeg',
        options={'HIDDEN'}
    )

    files: bpy.props.CollectionProperty(
        name='File Path',
        type=bpy.types.OperatorFileListElement,
    )

    directory: bpy.props.StringProperty(
            subtype='DIR_PATH',
    )

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.scale_y = Config.text_scale_y
        col.label(text='Load image sequence. ')
        col.label(text='Just select first image in sequence')

    def execute(self, context):
        geotracker = get_current_geotracker_item()
        if not geotracker:
            return {'CANCELLED'}

        new_movieclip = _load_movieclip(self.directory,
                                        [f.name for f in self.files])
        if not new_movieclip:
            return {'CANCELLED'}

        _log_output(f'LOADED MOVIECLIP: {geotracker.movie_clip.name}')
        return {'FINISHED'}


class GT_OT_ChoosePrecalcFile(bpy.types.Operator, ExportHelper):
    bl_idname = GTConfig.gt_choose_precalc_file_idname
    bl_label = 'Set precalc file'
    bl_description = 'Choose an existing .precalc file ' \
                     'or just enter a name for a new one'
    bl_options = {'REGISTER', 'INTERNAL'}

    filter_glob: bpy.props.StringProperty(
        default='*.precalc',
        options={'HIDDEN'}
    )

    check_existing: bpy.props.BoolProperty(
        name='Check Existing',
        description='Check and warn on overwriting existing files',
        default=True,
        options={'HIDDEN'},
    )

    filename_ext: bpy.props.StringProperty(default='.precalc')

    filepath: bpy.props.StringProperty(
        default=GTConfig.default_precalc_filename,
        subtype='FILE_PATH'
    )

    def check(self, context):
        change_ext = False

        filepath = self.filepath
        sp = os.path.splitext(filepath)

        if sp[1] in {'.precalc', '.'}:
            filepath = sp[0]

        filepath = bpy.path.ensure_ext(filepath, self.filename_ext)

        if filepath != self.filepath:
            self.filepath = filepath
            change_ext = True

        return change_ext

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.scale_y = Config.text_scale_y
        col.label(text='Choose an existing .precalc file')
        col.label(text='or just enter a name for a new one')

    def execute(self, context):
        _log_output('PRECALC PATH: {}'.format(self.filepath))
        geotracker = get_current_geotracker_item()
        if not geotracker:
            _log_error('Current GeoTracker is wrong')
            return {'CANCELLED'}

        if os.path.exists(self.filepath) and os.path.isdir(self.filepath):
            _log_error(f'Wrong precalc destination: {self.filepath}')
            self.report({'ERROR'}, 'Wrong precalc destination!')
            return {'CANCELLED'}

        geotracker.precalc_path = self.filepath
        status, msg, _ = geotracker.reload_precalc()
        if not status:
            _log_error(msg)
            self.report({'ERROR'}, msg)

        _log_output('PRECALC PATH HAS BEEN CHANGED: {}'.format(self.filepath))
        return {'FINISHED'}


class GT_OT_SplitVideo(bpy.types.Operator, ExportHelper):
    bl_idname = GTConfig.gt_split_video_to_frames_idname
    bl_label = 'Split video to frames'
    bl_description = 'Choose dir where to place video-file frames'
    bl_options = {'REGISTER', 'INTERNAL'}

    use_filter: bpy.props.BoolProperty(default=True)
    use_filter_folder: bpy.props.BoolProperty(default=True)

    filter_glob: bpy.props.StringProperty(
          options={'HIDDEN'}
    )
    filepath: bpy.props.StringProperty(
        default='',
        subtype='DIR_PATH'
    )
    file_format: bpy.props.EnumProperty(name='Image file format', items=[
        ('PNG', 'PNG', 'Default image file format', 0),
        ('JPEG', 'JPEG', 'Data loss image format', 1),
    ], description='Choose image file format')
    from_frame: bpy.props.IntProperty(name='from', default=1)
    to_frame: bpy.props.IntProperty(name='to', default=1)
    filename_ext: bpy.props.StringProperty()

    def draw(self, context):
        layout = self.layout
        layout.label(text='Output frames file format:')
        layout.prop(self, 'file_format', expand=True)
        layout.label(text='Frame range:')
        row = layout.row()
        row.prop(self, 'from_frame', expand=True)
        row.prop(self, 'to_frame', expand=True)

    def execute(self, context):
        self.filename_ext = '.png' if self.file_format == 'PNG' else '.jpg'
        filepath = os.path.abspath(self.filepath)
        _log_output(f'OUTPUT filepath: {filepath}')

        geotracker = get_current_geotracker_item()
        if not geotracker or not geotracker.movie_clip:
            return {'CANCELLED'}

        output_path = convert_movieclip_to_frames(geotracker.movie_clip,
                                                  filepath,
                                                  file_format=self.file_format,
                                                  start_frame=self.from_frame,
                                                  end_frame=self.to_frame)
        _log_output(f'OUTPUT PATH2: {output_path}')
        if output_path is not None:
            new_movieclip = _load_movieclip(os.path.dirname(output_path),
                                            [os.path.basename(output_path)])
            _log_output(f'new_movieclip: {new_movieclip}')
        return {'FINISHED'}


class GT_OT_SplitVideoExec(bpy.types.Operator):
    bl_idname = GTConfig.gt_split_video_to_frames_exec_idname
    bl_label = 'Split video-file.'
    bl_description = 'Choose dir where to place video-file frames.'
    bl_options = {'REGISTER', 'INTERNAL'}

    def draw(self, context):
        pass

    def execute(self, context):
        _log_output('GT_OT_SplitVideoExec')
        geotracker = get_current_geotracker_item()
        if not geotracker or not geotracker.movie_clip:
            return {'CANCELLED'}

        op = get_operator(GTConfig.gt_split_video_to_frames_idname)
        op('INVOKE_DEFAULT', from_frame=1,
           to_frame=get_movieclip_duration(geotracker.movie_clip),
           filepath=os.path.join(os.path.dirname(geotracker.movie_clip.filepath),''))
        return {'FINISHED'}


class GT_OT_FrameSelector(bpy.types.Operator):
    bl_idname = GTConfig.gt_select_frames_for_bake_idname
    bl_label = 'Select frames:'
    bl_description = 'Create texture using selected frames'
    bl_options = {'REGISTER', 'INTERNAL'}

    def draw(self, context):
        geotracker = get_current_geotracker_item()
        if not geotracker or not geotracker.movie_clip:
            return {'CANCELLED'}

        layout = self.layout
        checked_views = False

        box = layout.box()
        col = box.column(align=True)
        col.scale_y = Config.text_scale_y
        for item in geotracker.selected_frames:
            row = col.row(align=True)
            row.prop(item, 'selected', text='')
            row.label(text=f'{item.num}', icon='FILE_IMAGE')
            if item.selected:
                checked_views = True

        row = box.row(align=True)
        op = row.operator(GTConfig.gt_actor_idname, text='All')
        op.action = 'select_all_frames'

        op = row.operator(GTConfig.gt_actor_idname, text='None')
        op.action = 'deselect_all_frames'

        col = layout.column()
        col.scale_y = Config.text_scale_y

        if checked_views:
            col.label(text='Please note: texture creation is very '
                           'time consuming.')
        else:
            col.alert = True
            col.label(text='You need to select at least one image '
                           'to create texture.')

    def invoke(self, context, event):
        geotracker = get_current_geotracker_item()
        if not geotracker or not geotracker.movie_clip:
            return {'CANCELLED'}
        gt = GTLoader.kt_geotracker()

        selected_frames = geotracker.selected_frames
        old_selected_frame_numbers = set([x.num for x in selected_frames if x.selected])
        selected_frames.clear()
        for frame in gt.keyframes():
            item = selected_frames.add()
            item.num = frame
            item.selected = frame in old_selected_frame_numbers

        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        _log_output('GT START TEXTURE CREATION')

        geotracker = get_current_geotracker_item()
        if not geotracker or not geotracker.movie_clip:
            return {'CANCELLED'}

        built_texture = bake_texture(
            geotracker,
            [x.num for x in geotracker.selected_frames if x.selected])

        if built_texture is None:
            _log_error('GT TEXTURE HAS NOT BEEN CREATED')
        else:
            preview_material_with_texture(built_texture, geotracker.geomobj)
            _log_output('GT TEXTURE HAS BEEN CREATED')
        return {'FINISHED'}
