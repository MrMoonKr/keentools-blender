# ##### BEGIN GPL LICENSE BLOCK #####
# KeenTools for blender is a blender addon for using KeenTools in Blender.
# Copyright (C) 2019-2022  KeenTools

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

from typing import Any, List, Callable, Tuple, Optional

from bpy.types import Object, Area, Region, SpaceView3D

from .bpy_common import bpy_background_mode


class KTShaderBase:
    handler_list: List[Callable] = []

    @classmethod
    def add_handler_list(cls, handler: Callable) -> None:
        cls.handler_list.append(handler)

    @classmethod
    def remove_handler_list(cls, handler: Callable) -> None:
        if handler in cls.handler_list:
            cls.handler_list.remove(handler)

    @classmethod
    def is_handler_list_empty(cls) -> bool:
        return len(cls.handler_list) == 0

    def __init__(self, target_class: Any=SpaceView3D):
        self.draw_handler: Optional[Any] = None
        self.target_class: Any = target_class
        self.work_area: Optional[Area] = None
        self.is_shader_visible: bool = True

        if not bpy_background_mode():
            self.init_shaders()

    def is_visible(self) -> bool:
        return self.is_shader_visible

    def set_visible(self, flag: bool=True) -> None:
        self.is_shader_visible = flag

    def get_target_class(self) -> Any:
        return self.target_class

    def set_target_class(self, target_class: Any) -> None:
        self.target_class = target_class

    def is_working(self) -> bool:
        return not (self.draw_handler is None)

    def init_shaders(self) -> None:
        pass

    def create_batch(self) -> None:
        pass

    def draw_callback(self, context) -> None:
        pass

    def register_handler(self, context: Any,
                         post_type: str='POST_VIEW') -> None:
        self.work_area = context.area
        if self.draw_handler is not None:
            self.unregister_handler()
        self.draw_handler = self.get_target_class().draw_handler_add(
            self.draw_callback, (context,), 'WINDOW', post_type)
        self.add_handler_list(self.draw_handler)

    def unregister_handler(self) -> None:
        if self.draw_handler is not None:
            self.get_target_class().draw_handler_remove(
                self.draw_handler, 'WINDOW')
            self.remove_handler_list(self.draw_handler)
        self.draw_handler = None
        self.work_area = None

    def hide_shader(self) -> None:
        self.set_visible(False)

    def unhide_shader(self) -> None:
        self.set_visible(True)
