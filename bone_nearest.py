import bpy
import bmesh
from bpy_extras import view3d_utils

addon_keymaps = []

class BoneNearestProps(bpy.types.PropertyGroup):
    use_bone_nearest: bpy.props.BoolProperty(name="Enable Shortcuts", default=False)

def get_bone_from_weights(obj, face_index, hit_location_world):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(depsgraph)
    mesh = eval_obj.to_mesh()
    mesh.calc_loop_triangles()

    try:
        face = mesh.polygons[face_index]
    except IndexError:
        eval_obj.to_mesh_clear()
        return []

    closest_vert_idx = min(
        face.vertices,
        key=lambda i: (obj.matrix_world @ mesh.vertices[i].co - hit_location_world).length
    )

    vertex = mesh.vertices[closest_vert_idx]
    sorted_groups = sorted(vertex.groups, key=lambda g: g.weight, reverse=True)
    bone_names = [obj.vertex_groups[g.group].name for g in sorted_groups]

    eval_obj.to_mesh_clear()
    return bone_names

class VIEW3D_OT_pick_weighted_bone(bpy.types.Operator):
    bl_idname = "view3d.pick_weighted_bone"
    bl_label = "Click on mesh (check by weight)"

    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        # Sprawdź, czy checkbox "Enable Shortcuts" jest włączony
        if not context.scene.bone_nearest_props.use_bone_nearest:
            return {'PASS_THROUGH'}

        region = context.region
        rv3d = context.space_data.region_3d
        coord = (event.mouse_region_x, event.mouse_region_y)

        view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
        ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
        depsgraph = context.evaluated_depsgraph_get()

        result, location, normal, face_index, obj, _ = context.scene.ray_cast(
                depsgraph, ray_origin, view_vector
            )

        # Jeśli nie trafiono w obiekt, nie rób nic
        if not result or obj is None or obj.type != 'MESH':
            return {'PASS_THROUGH'}

        bone_names = get_bone_from_weights(obj, face_index, obj.matrix_world.inverted() @ location)

        # Sprawdź, czy mesh ma modyfikator typu Armature
        arm_mod = next((m for m in obj.modifiers if m.type == 'ARMATURE' and m.object), None)

        if bone_names:
            # Użyj aktywnej armatury
            arm = context.active_object
            if arm and arm.type == 'ARMATURE' and arm.mode == 'POSE':
                # Znajdź pierwszą pasującą kość w tej armaturze
                for name in bone_names:
                    if name in arm.pose.bones:
                        bpy.ops.pose.select_all(action='DESELECT')
                        pb = arm.pose.bones[name]
                        pb.bone.select = True
                        arm.data.bones.active = pb.bone
                        return {'FINISHED'}

        return {'FINISHED'}

class VIEW3D_PT_bone_picker_weights(bpy.types.Panel):
    bl_label = "Bone Picker"
    bl_idname = "VIEW3D_PT_bone_picker_weights"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_parent_id = 'VIEW3D_PT_bone_edit'
    bl_category = "GUI PatryCCio"

    @classmethod
    def poll(cls, context):
        return context.mode == 'POSE'

    def draw(self, context):
        layout = self.layout
        # Dodaj checkboxa do panelu
        layout.prop(context.scene.bone_nearest_props, "use_bone_nearest", text="Enable Shortcuts")
        layout.operator("view3d.pick_weighted_bone", text="Kliknij mesh – wybierz wg wag")

classes = [
    VIEW3D_OT_pick_weighted_bone,
    VIEW3D_PT_bone_picker_weights,
]

def register():
    bpy.utils.register_class(BoneNearestProps)
    bpy.types.Scene.bone_nearest_props = bpy.props.PointerProperty(type=BoneNearestProps)

    for c in classes:
        bpy.utils.register_class(c)

    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps.new(name='Pose', space_type='EMPTY')
    # Zaktualizowany skrót: Ctrl + Shift + LPM (lewy przycisk myszy)
    kmi = km.keymap_items.new(VIEW3D_OT_pick_weighted_bone.bl_idname, 'LEFTMOUSE', 'PRESS', ctrl=True, shift=True)
    addon_keymaps.append((km, kmi))

def unregister():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    del bpy.types.Scene.bone_nearest_props

    for c in classes:
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
