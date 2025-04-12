import bpy

def group_by_prefix(objects):
    """ Grupa obiekty rekurencyjnie po częściach przed myślnikiem. """
    grouped = {}
    for obj in objects:
        parts = obj.name.split('-')
        current_group = grouped
        for part in parts:
            if part not in current_group:
                current_group[part] = {}
            current_group = current_group[part]
        # Na końcu dodajemy obiekt, ponieważ cała ścieżka nazwy może kończyć się na obiekt
        current_group['obj'] = current_group.get('obj', []) + [obj]
    return grouped

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

        armatures = [obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE']

        grouped_armatures = group_by_prefix(armatures)

        def draw_group(group, layout, prefix=""):
            for key, sub_group in sorted(group.items()):
                if key == 'obj':  
                    box = layout.row()
                    for obj in sub_group:
                        row = box.row()
                        row.prop(obj, "hide_viewport", text=f"")
                        row.prop(obj, "hide_render", text=f"")
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

        meshes = [obj for obj in bpy.context.scene.objects if obj.type in {'MESH', 'CURVE', 'LIGHT'}]

        grouped_objects = group_by_prefix(meshes)

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
        # Znajdź obiekt po nazwie
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

class ARMATURE_OT_select_object(bpy.types.Operator):
    bl_idname = "armature.select_object"
    bl_label = "Select Armature Object"

    object_name: bpy.props.StringProperty()

    def execute(self, context):
        # Znajdź obiekt po nazwie
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

class OBJECT_OT_select_object_add(bpy.types.Operator):
    bl_idname = "object.select_object_add"
    bl_label = "Select Add Armature Object"

    object_name: bpy.props.StringProperty()

    def execute(self, context):
        # Znajdź obiekt po nazwie
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

def register():
    bpy.utils.register_class(VisiblePanel)
    bpy.utils.register_class(ObjectVisibilityPanel)
    bpy.utils.register_class(ArmaturePanel)
    bpy.utils.register_class(OBJECT_OT_toggle_viewport_visibility)
    bpy.utils.register_class(OBJECT_OT_toggle_render_visibility)
    bpy.utils.register_class(ARMATURE_OT_toggle_viewport_visibility)
    bpy.utils.register_class(ARMATURE_OT_toggle_render_visibility)
    bpy.utils.register_class(ARMATURE_OT_select_object)
    bpy.utils.register_class(OBJECT_OT_select_object)
    bpy.utils.register_class(ARMATURE_OT_select_object_add)
    bpy.utils.register_class(OBJECT_OT_select_object_add)

def unregister():
    bpy.utils.unregister_class(VisiblePanel)
    bpy.utils.unregister_class(ObjectVisibilityPanel)
    bpy.utils.unregister_class(ArmaturePanel)
    bpy.utils.unregister_class(OBJECT_OT_toggle_viewport_visibility)
    bpy.utils.unregister_class(OBJECT_OT_toggle_render_visibility)
    bpy.utils.unregister_class(ARMATURE_OT_toggle_viewport_visibility)
    bpy.utils.unregister_class(ARMATURE_OT_toggle_render_visibility)
    bpy.utils.unregister_class(ARMATURE_OT_select_object)
    bpy.utils.unregister_class(OBJECT_OT_select_object)
    bpy.utils.unregister_class(ARMATURE_OT_select_object_add)
    bpy.utils.unregister_class(OBJECT_OT_select_object_add)

if __name__ == "__main__":
    register()
