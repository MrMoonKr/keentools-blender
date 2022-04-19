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
import bpy

from ..geotracker_config import GTConfig
from .utils.geotracker_acts import create_geotracker_act, enter_pinmode_act


class GT_OT_Actor(bpy.types.Operator):
    bl_idname = GTConfig.gt_actor_idname
    bl_label = 'Actor Operator'
    bl_options = {'REGISTER', 'UNDO'}

    action: bpy.props.StringProperty(name='Action string', default='none')
    num: bpy.props.IntProperty(name='Numeric parameter', default=0)

    def draw(self, context):
        pass

    def execute(self, context):
        logger = logging.getLogger(__name__)
        logger.debug('ACTION call: {}'.format(self.action))

        if self.action == 'create_geotracker':
            create_geotracker_act()
            self.report({'INFO'}, self.action)
            return {'FINISHED'}

        elif self.action == 'enter_pinmode':
            act_status = enter_pinmode_act()
            if not act_status.success:
                self.report({'ERROR'}, act_status.error_message)
                return {'CANCELLED'}

            self.report({'INFO'}, self.action)
            return {'FINISHED'}

        self.report({'INFO'}, self.action)
        return {'FINISHED'}
