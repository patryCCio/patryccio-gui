import bpy
import bmesh
import mathutils
from bpy.props import StringProperty, FloatProperty, EnumProperty

prefixAdd = "Brak"  

class BoneFromVertexOperator(bpy.types.Operator):
    bl_idname = "object.bones_from_vertices"
    bl_label = "Dodaj kości do zaznaczonych wierzchołków"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        size = context.scene.bone_size
        armature_name = context.scene.armature_name
        obj = context.active_object

        if obj.type != 'MESH':
            self.report({'ERROR'}, "Zaznacz obiekt typu MESH")
            return {'CANCELLED'}

        if armature_name not in bpy.data.objects:
            self.report({'ERROR'}, f"Armatura o nazwie '{armature_name}' nie istnieje!")
            return {'CANCELLED'}

        arm_obj = bpy.data.objects[armature_name]

        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(obj.data)
        world_positions = [obj.matrix_world @ v.co.copy() for v in bm.verts if v.select]
        bpy.ops.object.mode_set(mode='OBJECT')

        if not world_positions:
            self.report({'ERROR'}, "Nie zaznaczono żadnych wierzchołkóww!")
            return {'CANCELLED'}

        bpy.context.view_layer.objects.active = arm_obj
        bpy.ops.object.mode_set(mode='EDIT')

        for i, world_pos in enumerate(world_positions):
            bone_name = f"Bone_{i}"

            if prefixAdd == ".L":
                bone_name += ".L"
            elif prefixAdd == ".R":
                bone_name += ".R"

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
        layout.prop(context.scene, "bone_size")
        layout.prop(context.scene, "armature_name")

        layout.prop(context.scene, "bone_prefix")
        layout.operator("object.bones_from_vertices")

class BoneEditPanel(bpy.types.Panel):
    bl_label = "Bone Edit"
    bl_idname = "VIEW3D_PT_bone_edit"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'GUI PatryCCio'  

    def draw(self, context):
        layout = self.layout


def register():
    bpy.utils.register_class(BoneFromVertexOperator)
    bpy.utils.register_class(BoneEditPanel)
    bpy.utils.register_class(BoneEditAddPanel)
    bpy.types.Scene.bone_size = FloatProperty(
        name="Rozmiar kości",
        default=0.1,
        min=0.001,
        max=10.0,
        description="Długość każdej kości"
    )
    bpy.types.Scene.armature_name = StringProperty(
        name="Nazwa Armatury",
        default="Armature",
        description="Podaj nazwę armatury, do której mają być dodane kości"
    )
    bpy.types.Scene.bone_prefix = EnumProperty(
        name="Prefiks",
        items=[
            (".L", ".L", "Dodaj prefiks '.L' do nazwy kości"),
            ("Brak", "None", "Brak prefiksu"),
            (".R", ".R", "Dodaj prefiks '.R' do nazwy kości"),
        ],
        default="Brak",
        description="Wybierz prefiks do nazwy kości",
        update=lambda self, context: update_prefix(self, context)
    )


def unregister():
    bpy.utils.unregister_class(BoneFromVertexOperator)
    bpy.utils.unregister_class(BoneEditAddPanel)
    bpy.utils.unregister_class(BoneEditPanel)
    del bpy.types.Scene.bone_size
    del bpy.types.Scene.armature_name
    del bpy.types.Scene.bone_prefix


def update_prefix(self, context):
    global prefixAdd
    print(prefixAdd)
    prefixAdd = self.bone_prefix  

if __name__ == "__main__":
    register()
