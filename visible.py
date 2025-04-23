import bpy

def get_first_layer_items_objects(self, context):
    objects = context.scene.objects
    layers = set()
    for obj in objects:
        if obj.type in {'MESH', 'CURVE', 'LIGHT'} and '-' in obj.name:
            layers.add(obj.name.split('-')[0])
    return [(layer, layer, "") for layer in sorted(layers)]

bpy.types.Scene.first_layer_filter_objects = bpy.props.EnumProperty(
    name="Layer",
    description="Filter by top-level prefix (Objects)",
    items=get_first_layer_items_objects
)

def get_second_layer_items_objects(self, context):
    objects = context.scene.objects
    selected_first = context.scene.first_layer_filter_objects
    if not selected_first:
        return []

    layers = set()
    for obj in objects:
        parts = obj.name.split('-')
        if obj.type in {'MESH', 'CURVE', 'LIGHT'} and len(parts) >= 2 and parts[0] == selected_first:
            if len(parts) >= 2:
                layers.add(parts[1])
    return [(layer, layer, "") for layer in sorted(layers)]

bpy.types.Scene.second_layer_filter_objects = bpy.props.EnumProperty(
    name="Sub Layer",
    description="Filter by second-level prefix (Objects)",
    items=get_second_layer_items_objects
)

def get_first_layer_items_armatures(self, context):
    objects = context.scene.objects
    layers = set()
    for obj in objects:
        if obj.type == 'ARMATURE' and '-' in obj.name:
            layers.add(obj.name.split('-')[0])
    return [(layer, layer, "") for layer in sorted(layers)]

bpy.types.Scene.first_layer_filter_armatures = bpy.props.EnumProperty(
    name="Layer",
    description="Filter by top-level prefix (Armatures)",
    items=get_first_layer_items_armatures
)

def get_second_layer_items_armatures(self, context):
    objects = context.scene.objects
    selected_first = context.scene.first_layer_filter_armatures
    if not selected_first:
        return []

    layers = set()
    for obj in objects:
        parts = obj.name.split('-')
        if obj.type == 'ARMATURE' and len(parts) >= 2 and parts[0] == selected_first:
            if len(parts) >= 2:
                layers.add(parts[1])
    return [(layer, layer, "") for layer in sorted(layers)]

bpy.types.Scene.second_layer_filter_armatures = bpy.props.EnumProperty(
    name="Sub Layer",
    description="Filter by second-level prefix (Armatures)",
    items=get_second_layer_items_armatures
)

def update_second_layer_filter_objects(self, context):
    context.scene.second_layer_filter_objects = ""

bpy.types.Scene.first_layer_filter_objects = bpy.props.EnumProperty(
    name="Layer",
    description="Filter by top-level prefix (Objects)",
    items=get_first_layer_items_objects,
    update=update_second_layer_filter_objects
)

def update_second_layer_filter_armatures(self, context):
    context.scene.second_layer_filter_armatures = ""

bpy.types.Scene.first_layer_filter_armatures = bpy.props.EnumProperty(
    name="Layer",
    description="Filter by top-level prefix (Armatures)",
    items=get_first_layer_items_armatures,
    update=update_second_layer_filter_armatures
)

def group_by_prefix(objects):
    """ Grupa obiekty rekurencyjnie po częściach przed myślnikiem. """
    grouped = {}
    for obj in objects:
        parts = obj.name.split('-')
        if len(parts) < 2:
            continue  # Pomijaj obiekty bez prefiksu
        current_group = grouped
        for part in parts:
            if part not in current_group:
                current_group[part] = {}
            current_group = current_group[part]
        current_group['obj'] = current_group.get('obj', []) + [obj]
    return grouped

class CollectionPanel(bpy.types.Panel):
    bl_label = "Collections"
    bl_idname = "VIEW3D_PT_collection_visibility"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "GUI PatryCCio"
    bl_parent_id = "VIEW3D_PT_visible"

    def draw(self, context):
        layout = self.layout
        view_layer = context.view_layer

        def draw_collections(layer_collection, layout, level=0):
            # Pomijamy główną "Scene Collection"
            if layer_collection.name == "Scene Collection":
                for child in layer_collection.children:
                    draw_collections(child, layout, level)
                return

            row = layout.row()
            row.alignment = 'LEFT'
            row.prop(layer_collection, "exclude", text="")
            row.label(text=" " * (level * 4) + layer_collection.name)

            for child in layer_collection.children:
                draw_collections(child, layout, level + 1)

        draw_collections(view_layer.layer_collection, layout)

class ArmaturePanel(bpy.types.Panel):
    bl_label = "Armatures"
    bl_idname = "VIEW3D_PT_armature_visibility"
    bl_space_type = "VIEW_3D"
    bl_region_type = 'UI'
    bl_category = 'GUI PatryCCio'
    bl_parent_id = "VIEW3D_PT_visible"  

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.prop(context.scene, "first_layer_filter_armatures")
        layout.prop(context.scene, "second_layer_filter_armatures")

        armatures = [obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE' and '-' in obj.name]
        
        
        prefix = context.scene.first_layer_filter_armatures
        sub = context.scene.second_layer_filter_armatures
        filtered = [
            obj for obj in armatures
            if obj.name.startswith(f"{prefix}-") and
            (not sub or f"{prefix}-{sub}-" in obj.name or obj.name.startswith(f"{prefix}-{sub}"))
        ]
        
        
        grouped_armatures = group_by_prefix(filtered)

        def draw_group(group, layout, prefix=""):
            for key, sub_group in sorted(group.items()):
                if key == 'obj':  
                    box = layout.row()
                    for obj in sub_group:
                        row = box.row()
                        row.prop(obj, "hide_viewport", text=f"")
                        row.prop(obj, "hide_render", text=f"")
                        row.operator("armature.get_in_pose_mode", text="", icon="POSE_HLT").object_name = obj.name
                        row.operator("armature.select_object", text="", icon="RESTRICT_SELECT_OFF").object_name = obj.name  # Select button
                        row.operator("armature.select_object_add", text="", icon="ADD").object_name = obj.name  # Select button
                elif isinstance(sub_group, dict):  
                    box = layout.box()
                    box.label(text=f"{key}")

                    if 'obj' not in sub_group:
                        op_viewport = box.operator("armature.toggle_viewport_visibility", text=f"Toggle Viewport")
                        op_viewport.group_name = f"{prefix}{key}"  
                        
                        op_render = box.operator("armature.toggle_render_visibility", text=f"Toggle Render")
                        op_render.group_name = f"{prefix}{key}"  

                    draw_group(sub_group, box, prefix=f"{prefix}{key}-")  

        draw_group(grouped_armatures, layout)

class ObjectVisibilityPanel(bpy.types.Panel):
    bl_label = "Objects"
    bl_idname = "VIEW3D_PT_object_visibility"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'GUI PatryCCio'
    bl_parent_id = "VIEW3D_PT_visible"  

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.prop(context.scene, "first_layer_filter_objects")
        layout.prop(context.scene, "second_layer_filter_objects")
        meshes = [obj for obj in bpy.context.scene.objects if obj.type in {'MESH', 'CURVE', 'LIGHT'} and '-' in obj.name]
        
        
        prefix = context.scene.first_layer_filter_objects
        sub = context.scene.second_layer_filter_objects
        filtered = [obj for obj in meshes if obj.name.startswith(f"{prefix}-") and (not sub or f"{prefix}-{sub}-" in obj.name or obj.name.startswith(f"{prefix}-{sub}"))]
        
        
        grouped_objects = group_by_prefix(filtered)

        def draw_group(group, layout, prefix=""):
            for key, sub_group in sorted(group.items()):
                if key == 'obj':  
                    box = layout.row()
                    for obj in sub_group:
                        row = box.row()
                        row.prop(obj, "hide_viewport", text="", expand=True)
                        row.prop(obj, "hide_render", text="", expand=True)
                        row.operator("object.select_object", text="", icon="RESTRICT_SELECT_OFF").object_name = obj.name  # Select button
                        row.operator("object.select_object_add", text="", icon="ADD").object_name = obj.name  # Select button
                elif isinstance(sub_group, dict):  
                    box = layout.box()
                    box.label(text=f"{key}")

                    if 'obj' not in sub_group:
                        op_viewport = box.operator("object.toggle_viewport_visibility", text=f"Toggle Viewport")
                        op_viewport.group_name = f"{prefix}{key}"  
                        
                        op_render = box.operator("object.toggle_render_visibility", text=f"Toggle Render")

                    draw_group(sub_group, box, prefix=f"{prefix}{key}-") 

        draw_group(grouped_objects, layout)

class ARMATURE_OT_toggle_viewport_visibility(bpy.types.Operator):
    bl_idname = "armature.toggle_viewport_visibility"
    bl_label = "Toggle Viewport Visibility for Armature"

    group_name: bpy.props.StringProperty()

    def execute(self, context):
        
        all_objects = bpy.context.scene.objects
        grouped_armatures = [obj for obj in all_objects if obj.type == 'ARMATURE' and obj.name.startswith(self.group_name)]
        
        for obj in grouped_armatures:
            obj.hide_viewport = not obj.hide_viewport
        
        return {'FINISHED'}


class ARMATURE_OT_toggle_render_visibility(bpy.types.Operator):
    bl_idname = "armature.toggle_render_visibility"
    bl_label = "Toggle Render Visibility for Armature"

    group_name: bpy.props.StringProperty()

    def execute(self, context):
        all_objects = bpy.context.scene.objects
        grouped_armatures = [obj for obj in all_objects if obj.type == 'ARMATURE' and obj.name.startswith(self.group_name)]
        
        for obj in grouped_armatures:
            obj.hide_render = not obj.hide_render
        
        return {'FINISHED'}


class OBJECT_OT_toggle_viewport_visibility(bpy.types.Operator):
    bl_idname = "object.toggle_viewport_visibility"
    bl_label = "Toggle Viewport Visibility for Object"

    group_name: bpy.props.StringProperty()

    def execute(self, context):
        all_objects = bpy.context.scene.objects
        grouped_objects = [obj for obj in all_objects if obj.type in {'MESH', 'CURVE', 'LIGHT'} and obj.name.startswith(self.group_name)]
        
        for obj in grouped_objects:
            obj.hide_viewport = not obj.hide_viewport
        
        return {'FINISHED'}


class OBJECT_OT_toggle_render_visibility(bpy.types.Operator):
    bl_idname = "object.toggle_render_visibility"
    bl_label = "Toggle Render Visibility for Object"

    group_name: bpy.props.StringProperty()

    def execute(self, context):
        all_objects = bpy.context.scene.objects
        grouped_objects = [obj for obj in all_objects if obj.type in {'MESH', 'CURVE', 'LIGHT'} and obj.name.startswith(self.group_name)]
        
        for obj in grouped_objects:
            obj.hide_render = not obj.hide_render
        
        return {'FINISHED'}

class ARMATURE_OT_select_object_add(bpy.types.Operator):
    bl_idname = "armature.select_object_add"
    bl_label = "Select Add Armature Object"

    object_name: bpy.props.StringProperty()

    def execute(self, context):
        cm = bpy.context.mode

        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        obj = bpy.context.scene.objects.get(self.object_name)
        
        if obj:
            # Jeśli obiekt jest schowany, odblokuj jego widoczność
            if obj.hide_viewport:
                obj.hide_viewport = False

            # Zaznacz obiekt
            obj.select_set(True)

            # Zmień kolor zaznaczenia na jaśniejszy pomarańczowy (ustawienie aktywnego obiektu)
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)

            if cm == 'POSE':
                bpy.ops.object.mode_set(mode='POSE')

        return {'FINISHED'}

class ARMATURE_OT_select_object(bpy.types.Operator):
    bl_idname = "armature.select_object"
    bl_label = "Select Armature Object"

    object_name: bpy.props.StringProperty()
    
    def execute(self, context):
        cm = bpy.context.mode
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        obj = bpy.context.scene.objects.get(self.object_name)
        bpy.ops.object.select_all(action='DESELECT')
        
        
        if obj:
            if obj.hide_viewport:
                obj.hide_viewport = False

            obj.select_set(True)

            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)

            if cm == 'POSE':
                bpy.ops.object.mode_set(mode='POSE')

        return {'FINISHED'}

class ARMATURE_OT_get_in_pose_mode(bpy.types.Operator):
    bl_idname = "armature.get_in_pose_mode"
    bl_label = "Get in Pose Mode"

    object_name: bpy.props.StringProperty()

    def execute(self, context):
        # Przeniesione do wnętrza funkcji
        bpy.ops.object.mode_set(mode='OBJECT')
        obj = context.scene.objects.get(self.object_name)
        bpy.ops.object.select_all(action='DESELECT')

        if obj and obj.type == 'ARMATURE':
            if obj.hide_viewport:
                obj.hide_viewport = False

            obj.select_set(True)
            context.view_layer.objects.active = obj
            obj.select_set(True)

            bpy.ops.object.mode_set(mode='POSE')

        return {'FINISHED'}

class OBJECT_OT_select_object_add(bpy.types.Operator):
    bl_idname = "object.select_object_add"
    bl_label = "Select Add Armature Object"

    object_name: bpy.props.StringProperty()

    def execute(self, context):
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        obj = bpy.context.scene.objects.get(self.object_name)
        
        if obj:
            # Jeśli obiekt jest schowany, odblokuj jego widoczność
            if obj.hide_viewport:
                obj.hide_viewport = False

            # Zaznacz obiekt
            obj.select_set(True)

            # Zmień kolor zaznaczenia na jaśniejszy pomarańczowy (ustawienie aktywnego obiektu)
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)

        return {'FINISHED'}

class OBJECT_OT_select_object(bpy.types.Operator):
    bl_idname = "object.select_object"
    bl_label = "Select Object"
    object_name: bpy.props.StringProperty()

    def execute(self, context):
        # Znajdź obiekt po nazwie
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        obj = bpy.context.scene.objects.get(self.object_name)
        bpy.ops.object.select_all(action='DESELECT')
        
        if obj:
            # Jeśli obiekt jest schowany, odblokuj jego widoczność
            if obj.hide_viewport:
                obj.hide_viewport = False

            # Zaznacz obiekt
            obj.select_set(True)

            # Zmień kolor zaznaczenia na jaśniejszy pomarańczowy (ustawienie aktywnego obiektu)
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)

        return {'FINISHED'}


class VisiblePanel(bpy.types.Panel):
    bl_label = "Visibility"
    bl_idname = "VIEW3D_PT_visible"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'GUI PatryCCio'  

    def draw(self, context):
        layout = self.layout

classes = [
    VisiblePanel,
    CollectionPanel,
    ObjectVisibilityPanel,
    ArmaturePanel,
    OBJECT_OT_toggle_viewport_visibility,
    OBJECT_OT_toggle_render_visibility,
    ARMATURE_OT_toggle_viewport_visibility,
    ARMATURE_OT_toggle_render_visibility,
    ARMATURE_OT_select_object,
    OBJECT_OT_select_object,
    ARMATURE_OT_select_object_add,
    ARMATURE_OT_get_in_pose_mode,
    OBJECT_OT_select_object_add,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
