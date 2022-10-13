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

from typing import List, Dict, Any

import bpy
import blf

from .base_shaders import KTShaderBase


class KTScreenText(KTShaderBase):
    def __init__(self, target_class: str=bpy.types.SpaceView3D):
        self.defaults = {'color': (1., 1., 1., 0.5),
                         'size': 24,
                         'shadow_color': (0., 0., 0., 0.75),
                         'shadow_blur': 5,
                         'x': None,
                         'y': 60}
        self.message: Dict = dict()
        self.set_message(self.get_default_text())
        super().__init__(target_class)

    def get_default_text(self) -> List[Dict]:
        return [
            {'text': 'Pin Mode ',
             'color': (1., 1., 1., 0.5),
             'size': 24,
             'y': 60},  # line 1
            {'text': 'ESC: Exit | LEFT CLICK: Create Pin | '
                     'RIGHT CLICK: Delete Pin | TAB: Hide/Show',
             'color': (1., 1., 1., 0.5),
             'size': 20,
             'y': 30}  # line 2
        ]

    def _fill_all_fields(self, text_arr: List[Dict]) -> List[Dict]:
        for row in text_arr:
            for name in self.defaults:
                if name not in row.keys():
                    row[name] = self.defaults[name]
        return text_arr

    def set_message(self, msg: List[Dict]) -> None:
        self.message = self._fill_all_fields(msg)

    def draw_callback(self, context: Any) -> None:
        # Force Stop
        if self.is_handler_list_empty():
            self.unregister_handler()
            return

        area = context.area
        if self.work_area != area:
            return

        if len(self.message) == 0:
            return

        region = area.regions[-1]
        assert region.type == 'WINDOW'

        xc = int(region.width * 0.5)  # horizontal center
        yc = int(region.height * 0.5)  # vertical center
        font_id = 0

        for row in self.message:
            blf.color(font_id, *row['color'])

            blf.enable(font_id, blf.SHADOW)
            blf.shadow(font_id, row['shadow_blur'], *row['shadow_color'])
            blf.shadow_offset(font_id, 1, -1)

            blf.size(font_id, row['size'], 72)

            xp = row['x'] if row['x'] is not None \
                else xc - blf.dimensions(font_id, row['text'])[0] * 0.5
            yp = row['y'] if row['y'] is not None else yc
            blf.position(font_id, xp, yp, 0)
            blf.draw(font_id, row['text'])

    def register_handler(self, context: Any,
                         post_type: str='POST_PIXEL') -> None:
        super().register_handler(context, post_type)
