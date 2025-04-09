import bpy
import bmesh

class MirrorVertexGroupWeightsOperator(bpy.types.Operator):
    bl_idname = "object.mirror_vertex_group_weights"
    bl_label = "Mirror Vertex Group Weights"

    source_vg: bpy.props.StringProperty()
    axis: bpy.props.StringProperty(default='X')

    def execute(self, context):
        obj = context.object

        if ".L" in self.source_vg:
            target_vg_name = self.source_vg.replace(".L", ".R")
        elif ".R" in self.source_vg:
            target_vg_name = self.source_vg.replace(".R", ".L")
        else:
            self.report({"ERROR"}, "Vertex group must contain .L or .R")
            return {'CANCELLED'}

        if not obj.vertex_groups.get(target_vg_name):
            obj.vertex_groups.new(name=target_vg_name)

        mirror_vertex_group_weights(obj, self.source_vg, target_vg_name, self.axis)
        
        self.report({"INFO"}, f"Mirrored {self.source_vg} to {target_vg_name} along {self.axis} axis")
        return {'FINISHED'}

def mirror_vertex_group_weights(obj, source_vg_name, target_vg_name, axis):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')

    bm = bmesh.from_edit_mesh(obj.data)

    source_vg = obj.vertex_groups.get(source_vg_name)
    target_vg = obj.vertex_groups.get(target_vg_name)

    if not source_vg or not target_vg:
        print(f"Vertex group {source_vg_name} or {target_vg_name} does not exist.")
        return

    vg_weights = {v.index: get_vertex_weight(obj, source_vg, v.index) for v in bm.verts if has_vertex_weight(obj, source_vg, v.index) and get_vertex_weight(obj, source_vg, v.index) > 0}

    bpy.ops.object.mode_set(mode='OBJECT')

    for vert in obj.data.vertices:
        mirrored_vert = vert.co.copy()
        if axis == 'X':
            mirrored_vert.x = -mirrored_vert.x
        elif axis == 'Y':
            mirrored_vert.y = -mirrored_vert.y
        elif axis == 'Z':
            mirrored_vert.z = -mirrored_vert.z

        nearest_vert = find_nearest_vertex(obj, mirrored_vert)

        if nearest_vert and nearest_vert.index in vg_weights:
            weight = vg_weights[nearest_vert.index]
            target_vg.add([vert.index], weight, 'REPLACE')

    bpy.ops.object.mode_set(mode='EDIT')


def get_vertex_weight(obj, vg, vert_index):
    try:
        return vg.weight(vert_index)
    except RuntimeError:
        return 0.0

def has_vertex_weight(obj, vg, vert_index):
    try:
        vg.weight(vert_index)
        return True
    except RuntimeError:
        return False

def find_nearest_vertex(obj, co):
    nearest_vert = None
    nearest_distance = float('inf')

    for vert in obj.data.vertices:
        distance = (vert.co - co).length
        if distance < nearest_distance:
            nearest_vert = vert
            nearest_distance = distance

    return nearest_vert

class PT_VERTEX_GROUPS(bpy.types.Panel):
    bl_label = "Vertex Groups"
    bl_idname = "PT_VERTEX_GROUPS"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'GUI PatryCCio'
    
    def draw(self, context):
        layout = self.layout
        obj = context.object

        if not obj or obj.type != 'MESH':
            layout.label(text="Active object is not a mesh")
            return

class VertexGroupMirrorPanel(bpy.types.Panel):
    bl_label = "Mirror"
    bl_idname = "OBJECT_PT_vertex_group_mirror"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'GUI PatryCCio'
    bl_parent_id = "PT_VERTEX_GROUPS"
    @classmethod
    def poll(cls, context):
        obj_t = getattr(context, "object", None)
        return obj_t and obj_t.type == 'MESH' and obj_t.select_get()

    def draw(self, context):
        layout = self.layout
        obj = context.object

        if not obj or obj.type != 'MESH':
            layout.label(text="Active object is not a mesh")
            return

        row = layout.row()
        row.prop(context.scene, "mirror_axis", expand=True)

        vgs = obj.vertex_groups
        for vg in vgs:
            if ".L" in vg.name or ".R" in vg.name:
                row = layout.row()
                row.label(text=vg.name)
                op = row.operator("object.mirror_vertex_group_weights", text="Mirror")
                op.source_vg = vg.name
                op.axis = context.scene.mirror_axis

classes = [
    PT_VERTEX_GROUPS,
    MirrorVertexGroupWeightsOperator,
    VertexGroupMirrorPanel
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.mirror_axis = bpy.props.EnumProperty(
        name="Mirror Axis",
        description="Select the axis for mirroring",
        items=[
            ('X', "X", "Mirror along X axis"),
            ('Y', "Y", "Mirror along Y axis"),
            ('Z', "Z", "Mirror along Z axis")
        ],
        default='X'
    )
    

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.mirror_axis

if __name__ == "__main__":
    register()
