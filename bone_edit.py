import bpy
import bmesh
import mathutils
from bpy.props import StringProperty, FloatProperty, EnumProperty

prefixAdd = "Brak"  

class BoneEditProps(bpy.types.PropertyGroup):
    density: bpy.props.IntProperty(name="Density", min=1, default=1)

class BoneFromSelected(bpy.types.Operator):
    bl_idname = "object.bones_from_selected"
    bl_label = "Add one bone to selected meshes"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        size = context.scene.bone_size
        armature_name = context.scene.armature_name
        selected_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']

        if not selected_objects:
            self.report({'ERROR'}, "Zaznacz obiekty typu MESH")
            return {'CANCELLED'}

        if armature_name not in bpy.data.objects:
            self.report({'ERROR'}, f"Armature '{armature_name}' doesn't exist!")
            return {'CANCELLED'}

        arm_obj = bpy.data.objects[armature_name]

        for obj in selected_objects:
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        bpy.context.view_layer.objects.active = arm_obj
        bpy.ops.object.mode_set(mode='EDIT')

        for i, obj in enumerate(selected_objects):
            # Wylicz środek bounding boxa
            bbox_center_local = 0.125 * sum((mathutils.Vector(corner) for corner in obj.bound_box), mathutils.Vector())
            bbox_center_world = obj.matrix_world @ bbox_center_local

            base_name = context.scene.bone_base_name.strip()
            bone_name = f"{base_name}_{i}" if base_name else f"Bone_{i}"
            prefix = context.scene.bone_prefix
            if prefix in [".L", ".R"]:
                bone_name += prefix

            bone = arm_obj.data.edit_bones.new(bone_name)
            bone.head = bbox_center_world
            bone.tail = bbox_center_world + mathutils.Vector((0, size, 0))

        bpy.ops.object.mode_set(mode='OBJECT')
        return {'FINISHED'}

class BoneFromVertexOperator(bpy.types.Operator):
    bl_idname = "object.bones_from_vertices"
    bl_label = "Add bones to selected vertices"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        size = context.scene.bone_size
        armature_name = context.scene.armature_name
        obj = context.active_object

        if obj.type != 'MESH':
            self.report({'ERROR'}, "Select mesh object")
            return {'CANCELLED'}

        # Apply transforms
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        if armature_name not in bpy.data.objects:
            self.report({'ERROR'}, f"Armature '{armature_name}' doesn't exist!")
            return {'CANCELLED'}

        arm_obj = bpy.data.objects[armature_name]

        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(obj.data)
        world_positions = [obj.matrix_world @ v.co.copy() for v in bm.verts if v.select]
        bpy.ops.object.mode_set(mode='OBJECT')

        if not world_positions:
            self.report({'ERROR'}, "No vertices were marked!")
            return {'CANCELLED'}

        bpy.context.view_layer.objects.active = arm_obj
        bpy.ops.object.mode_set(mode='EDIT')

        for i, world_pos in enumerate(world_positions):
            base_name = context.scene.bone_base_name.strip()
            bone_name = f"{base_name}_{i}" if base_name else f"Bone_{i}"
            prefix = context.scene.bone_prefix
            if prefix in [".L", ".R"]:
                bone_name += prefix

            bone = arm_obj.data.edit_bones.new(bone_name)
            bone.head = world_pos
            bone.tail = world_pos + mathutils.Vector((0, size, 0))

        bpy.ops.object.mode_set(mode='OBJECT')

        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')

        return {'FINISHED'}

class BoneFromVertexOperatorDensity(bpy.types.Operator):
    bl_idname = "object.bones_from_vertices_density"
    bl_label = "Add bones to selected vertices with density"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        size = context.scene.bone_size
        armature_name = context.scene.armature_name
        density = max(1, context.scene.prop_bone_edit.density)  # Pobieramy density z prop_bone_edit
        obj = context.active_object

        if obj.type != 'MESH':
            self.report({'ERROR'}, "Select mesh object")
            return {'CANCELLED'}

        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        if armature_name not in bpy.data.objects:
            self.report({'ERROR'}, f"Armature '{armature_name}' doesn't exist!")
            return {'CANCELLED'}

        arm_obj = bpy.data.objects[armature_name]

        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(obj.data)
        world_positions = [obj.matrix_world @ v.co.copy() for v in bm.verts if v.select]
        bpy.ops.object.mode_set(mode='OBJECT')

        if not world_positions:
            self.report({'ERROR'}, "No vertices were marked!")
            return {'CANCELLED'}

        bpy.context.view_layer.objects.active = arm_obj
        bpy.ops.object.mode_set(mode='EDIT')

        base_name = context.scene.bone_base_name.strip()
        prefix = context.scene.bone_prefix

        for i, world_pos in enumerate(world_positions[::density]):
            bone_index = i * density  # Dla spójności nazw
            bone_name = f"{base_name}_{bone_index}" if base_name else f"Bone_{bone_index}"
            if prefix in [".L", ".R"]:
                bone_name += prefix

            bone = arm_obj.data.edit_bones.new(bone_name)
            bone.head = world_pos
            bone.tail = world_pos + mathutils.Vector((0, size, 0))

        bpy.ops.object.mode_set(mode='OBJECT')

        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')

        return {'FINISHED'}
        
class BoneEditAddPanel(bpy.types.Panel):
    bl_label = "Bone Add"
    bl_idname = "PT_bone_add"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_parent_id = "VIEW3D_PT_bone_edit"
    bl_category = "GUI PatryCCio"
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.prop_bone_edit

        box = layout.box()
        box.label(text="Settings")
        box.prop(context.scene, "bone_size")

        box.label(text="Armatures list")
        box.prop(context.scene, "armature_name")

        box.label(text="Base name for bone")
        box.prop(context.scene, "bone_base_name")

        layout.separator()

        box2 = layout.box()
        box2.prop(context.scene, "bone_prefix")
        box2.operator("object.bones_from_vertices")
        box2.operator("object.bones_from_selected")

        layout.separator()

        box3 = layout.box()
        box3.prop(props, "density")
        box3.operator("object.bones_from_vertices_density")

class BoneEditPanel(bpy.types.Panel):
    bl_label = "Bone Edit"
    bl_idname = "VIEW3D_PT_bone_edit"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'GUI PatryCCio'  

    def draw(self, context):
        layout = self.layout

classes = [
    BoneEditProps,
    BoneFromVertexOperator,
    BoneFromVertexOperatorDensity,
    BoneEditPanel,
    BoneEditAddPanel,
    BoneFromSelected
]

def register():
    for c in classes:
        bpy.utils.register_class(c)

    bpy.types.Scene.prop_bone_edit = bpy.props.PointerProperty(type=BoneEditProps)

    bpy.types.Scene.bone_size = FloatProperty(
        name="Bone size",
        default=0.1,
        min=0.001,
        max=10.0,
        description="Length for all bones"
    )
    def get_armature_items(self, context):
        return [(obj.name, obj.name, "") for obj in bpy.data.objects if obj.type == 'ARMATURE']

    bpy.types.Scene.armature_name = EnumProperty(
        name="",
        description="Check armature from list",
        items=get_armature_items
    )
    bpy.types.Scene.bone_prefix = EnumProperty(
        name="Prefix",
        items=[
            (".L", ".L", "Add prefix '.L' to bone name"),
            ("Without prefix", "None", "Without prefix"),
            (".R", ".R", "Add prefix '.R' to bone name"),
        ],
        default="Without prefix",
        description="Check prefix to bone name",
        update=lambda self, context: update_prefix(self, context)
    )
    bpy.types.Scene.bone_base_name = StringProperty(
        name="",
        default="",
        description="Optional base name for all bones"
    )


def unregister():
    del bpy.types.Scene.prop_bone_edit

    for c in classes:
        bpy.utils.unregister_class(c)

    del bpy.types.Scene.bone_size
    del bpy.types.Scene.armature_name
    del bpy.types.Scene.bone_prefix
    del bpy.types.Scene.bone_base_name

def update_prefix(self, context):
    global prefixAdd
    print(prefixAdd)
    prefixAdd = self.bone_prefix  

if __name__ == "__main__":
    register()
