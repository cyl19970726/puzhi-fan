"""
渲染指定 STL 的单件预览图（验证修复几何没变形）
用法: blender --background --python cad/preview_stl.py -- Base Body FrontPanel M2_Bracket
输出: cad/stl/_preview_<name>.png
"""
import bpy
import os
import sys
import math
import mathutils
from mathutils import Vector

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STL_DIR = os.path.join(BASE_DIR, "stl")


def render_one(name):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    path = os.path.join(STL_DIR, name + ".stl")
    bpy.ops.wm.stl_import(filepath=path)
    obj = bpy.context.selected_objects[0]
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "OBJECT"
    scene.display.shading.show_cavity = True

    bb = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    ctr = sum(bb, Vector()) / 8
    r = max((v - ctr).length for v in bb)
    cam_loc = ctr + Vector((1, -1, 0.8)).normalized() * r * 2.6
    bpy.ops.object.camera_add(location=cam_loc)
    cam = bpy.context.active_object
    cam.data.lens = 50
    fwd = (ctr - cam_loc).normalized()
    cam.rotation_euler = fwd.to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    scene.render.filepath = os.path.join(STL_DIR, "_preview_%s.png" % name)
    bpy.ops.render.render(write_still=True)
    print("PREVIEW:", scene.render.filepath)


for n in sys.argv[sys.argv.index("--") + 1:]:
    render_one(n)
