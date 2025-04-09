import bpy

registered_panels = []
shapes = []

def create_shape_key_item_panel(group):
    class PT_ShapeKeyItemPanel(bpy.types.Panel):
        bl_label = f'{group}'
        bl_idname = f'PT_{group.upper()}_SHAPEKEY_PT_PANEL'
        bl_space_type = 'VIEW_3D'
        bl_region_type = 'UI'
        bl_category = 'GUI PatryCCio'
        bl_parent_id = 'PT_KEYS_PT_PANEL'
        bl_options = {'DEFAULT_CLOSED'}

        @classmethod
        def poll(cls, context):
            obj_t = getattr(context, "object", None)
            return obj_t and obj_t.type == 'MESH' and obj_t.select_get()

        def draw(self, context):
            layout = self.layout
            obj_t = getattr(context, "object", None)

            if obj_t and obj_t.type == 'MESH':
                mesh = obj_t.data
                if mesh.shape_keys:
                    shape_keys = mesh.shape_keys.key_blocks
                    found_key = False

                    for key in shape_keys:
                        if key.name == "Basis":
                            continue

                        if key.name.startswith(group + "_") or (group == "Other" and "_" not in key.name):
                            found_key = True
                            key_name = key.name[len(group) + 1:] if group != "Other" else key.name
                            row = layout.row()
                            row.prop(mesh.shape_keys.key_blocks[key.name], 'value', text=key_name)
                            if key.name in shapes:
                                row.operator("object.remove_shape_key_from_selected", text="", icon="X").shape_key_name = key.name
                            else:
                                row.operator("object.add_shape_key_to_selected", text="", icon="PLUS").shape_key_name = key.name
                    
                    if not found_key:
                        layout.label(text="No shape keys found for this group", icon="ERROR")
                else:
                    layout.label(text="No shape keys found", icon="ERROR")
            else:
                layout.label(text="No mesh selected", icon="ERROR")

    return PT_ShapeKeyItemPanel

class OBJECT_OT_add_shape_key_to_selected(bpy.types.Operator):
    bl_idname = "object.add_shape_key_to_selected"
    bl_label = "Add Shape Key to Selected"
    
    shape_key_name: bpy.props.StringProperty()
    
    def execute(self, context):
        add_shape_key_to_selection(self.shape_key_name)
        return {'FINISHED'}

def add_shape_key_to_selection(shape_key_name):
    if shape_key_name not in shapes:
        shapes.append(shape_key_name)

class OBJECT_OT_remove_shape_key_from_selected(bpy.types.Operator):
    bl_idname = "object.remove_shape_key_from_selected"
    bl_label = "Remove Shape Key from Selected"
    
    shape_key_name: bpy.props.StringProperty()
    
    def execute(self, context):
        remove_shape_key_from_selection(self.shape_key_name)
        return {'FINISHED'}

def remove_shape_key_from_selection(shape_key_name):
    if shape_key_name in shapes:
        shapes.remove(shape_key_name)

class PT_ANIMATOR_PT_PANEL(bpy.types.Panel):
    bl_label = "Animator"
    bl_idname = 'PT_ANIMATOR_PT_PANEL'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'GUI PatryCCio'
    bl_parent_id = 'PT_ShapeKeyPanel'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        obj_t = getattr(context, "object", None)
        return obj_t and obj_t.type == 'MESH' and obj_t.data.shape_keys and obj_t.select_get()

    def draw(self, context):
        layout = self.layout
        layout.scale_y = 0.9

        row = layout.row()
        row.label(text="Current Frame:")
        row.label(text=str(context.scene.frame_current))

        row = layout.row(align=True)
        row.operator("object.change_frame", text="<").direction = 'BACKWARD'
        row.prop(context.scene, 'frame_change_amount', text="")
        row.operator("object.change_frame", text=">").direction = 'FORWARD'

        layout.label(text="Jump to Frame:")
        layout.prop(context.scene, 'frame_current', text="")

        layout.label(text="Frame Range:")
        row = layout.row()
        row.prop(context.scene, 'frame_start', text="Start")
        row.prop(context.scene, 'frame_end', text="End")

        layout.label(text="Create Repeat Animation:")
        layout.prop(context.scene, 'repeat_count', text="Repeat Count")
        layout.prop(context.scene, 'repeat_start', text="Repeat Start Frame")
        layout.prop(context.scene, 'repeat_end', text="Repeat End Frame")

        if shapes:
            box = layout.box()
            box.operator("object.create_repeat_animation", text="Create Repeat Animation")
            for shape in shapes:
                row = box.row()
                row.label(text=shape)
                row.operator("object.remove_shape_key_from_selected", text="", icon="X").shape_key_name = shape
        else:
            layout.label(text="No shape keys selected", icon="ERROR")

class PT_KEYS_PT_PANEL(bpy.types.Panel):
    bl_label = "Keys"
    bl_idname = 'PT_KEYS_PT_PANEL'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'GUI PatryCCio'
    bl_parent_id = 'PT_ShapeKeyPanel'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        obj_t = getattr(context, "object", None)
        return obj_t and obj_t.type == 'MESH' and obj_t.data.shape_keys and obj_t.select_get()

    def draw(self, context):
        layout = self.layout
        layout.scale_y = 1.4

class PT_ShapeKeyPanel(bpy.types.Panel):
    bl_label = 'Shape Keys'
    bl_idname = 'PT_ShapeKeyPanel'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'GUI PatryCCio'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        obj_t = getattr(context, "object", None)
        return obj_t and obj_t.type == 'MESH' and obj_t.select_get()

    def draw(self, context):
        layout = self.layout
        layout.scale_y = 1.4

        obj_t = getattr(context, "object", None)
        if obj_t and obj_t.type == 'MESH' and not obj_t.data.shape_keys:
            layout.label(text="No shape keys found", icon="ERROR")

class OBJECT_OT_create_shape_key_panels(bpy.types.Operator):
    bl_idname = "object.create_shape_key_panels"
    bl_label = "Create Shape Key Panels"

    def execute(self, context):
        reset_shape_key_panels(context)
        return {'FINISHED'}

class OBJECT_OT_change_frame(bpy.types.Operator):
    bl_idname = "object.change_frame"
    bl_label = "Change Frame"
    bl_options = {'REGISTER', 'UNDO'}

    direction: bpy.props.EnumProperty(
        items=[
            ('FORWARD', 'Forward', 'Move forward in time'),
            ('BACKWARD', 'Backward', 'Move backward in time')
        ],
        default='FORWARD'
    )

    def execute(self, context):
        change_frame(context.scene, self.direction)
        return {'FINISHED'}

def change_frame(scene, direction):
    frames = scene.frame_change_amount
    if direction == 'FORWARD':
        scene.frame_current += frames
    else:
        scene.frame_current -= frames

class OBJECT_OT_create_repeat_animation(bpy.types.Operator):
    bl_idname = "object.create_repeat_animation"
    bl_label = "Create Repeat Animation"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        create_repeat_animation(context)
        return {'FINISHED'}

def create_repeat_animation(context):
    scene = context.scene
    repeat_count = scene.repeat_count
    repeat_start = scene.repeat_start
    repeat_end = scene.repeat_end
    shape_keys = shapes[:]  

    obj_t = getattr(context, "object", None)
    if obj_t:
        action = obj_t.data.shape_keys.animation_data.action
        for fcurve in action.fcurves:
            data_path = fcurve.data_path

            if data_path.startswith('key_blocks'):
                shape_key_name = data_path.split('"')[1]
                if shape_key_name in shape_keys: 
                    keyframe_points = [keyframe for keyframe in fcurve.keyframe_points 
                                       if repeat_start <= keyframe.co.x <= repeat_end]

                    frame_range = repeat_end - repeat_start
                    for count in range(1, repeat_count + 1):
                        offset = count * frame_range
                        for keyframe in keyframe_points:
                            new_frame = keyframe.co.x + offset
                            fcurve.keyframe_points.insert(new_frame, keyframe.co.y)

    for area in context.screen.areas:
        if area.type == 'DOPESHEET_EDITOR':  
            area.tag_redraw()

def update_panels_on_object_change(scene):
    reset_shape_key_panels(bpy.context)

def register():
    bpy.utils.register_class(PT_ShapeKeyPanel)
    bpy.utils.register_class(PT_KEYS_PT_PANEL)
    bpy.utils.register_class(PT_ANIMATOR_PT_PANEL)
    bpy.utils.register_class(OBJECT_OT_create_shape_key_panels)
    bpy.utils.register_class(OBJECT_OT_change_frame)
    bpy.utils.register_class(OBJECT_OT_create_repeat_animation)
    bpy.utils.register_class(OBJECT_OT_add_shape_key_to_selected)
    bpy.utils.register_class(OBJECT_OT_remove_shape_key_from_selected)

    bpy.types.Scene.repeat_count = bpy.props.IntProperty(
        name="Repeat Count",
        description="Number of times to repeat the animation",
        default=2
    )
    bpy.types.Scene.repeat_start = bpy.props.IntProperty(
        name="Repeat Start Frame",
        description="Start frame of the repeat animation",
        default=0
    )
    bpy.types.Scene.repeat_end = bpy.props.IntProperty(
        name="Repeat End Frame",
        description="End frame of the repeat animation",
        default=10
    )
    bpy.types.Scene.frame_change_amount = bpy.props.IntProperty(
        name="Frame Change Amount",
        description="Amount to change the frame by",
        default=1
    )

    bpy.app.handlers.depsgraph_update_post.append(update_panels_on_object_change)

    reset_shape_key_panels(bpy.context)

def reset_shape_key_panels(context):
    global shapes
    obj = getattr(context, "object", None)
    if obj != reset_shape_key_panels.previous_object:
        shapes = []
        reset_shape_key_panels.previous_object = obj

    if obj and obj.type == 'MESH':
        mesh = obj.data
        if mesh.shape_keys:
            grouped_keys = group_shape_keys(mesh.shape_keys.key_blocks)
            register_shape_key_panels(grouped_keys)

def unregister_panels():
    for panel in registered_panels:
        bpy.utils.unregister_class(panel)
    registered_panels.clear()

def group_shape_keys(shape_keys):
    grouped_keys = {}
    for key in shape_keys:
        group, key_name = parse_shape_key_name(key.name)
        if group not in grouped_keys:
            grouped_keys[group] = []
        grouped_keys[group].append(key_name)
    return grouped_keys

def parse_shape_key_name(name):
    if "_" in name:
        return name.split("_", 1)
    return "Other", name

def register_shape_key_panels(grouped_keys):
    for group, keys in grouped_keys.items():
        panel_class = create_shape_key_item_panel(group)
        bpy.utils.register_class(panel_class)
        registered_panels.append(panel_class)

def unregister():
    bpy.utils.unregister_class(PT_ShapeKeyPanel)
    bpy.utils.unregister_class(PT_KEYS_PT_PANEL)
    bpy.utils.unregister_class(PT_ANIMATOR_PT_PANEL)
    bpy.utils.unregister_class(OBJECT_OT_create_shape_key_panels)
    bpy.utils.unregister_class(OBJECT_OT_change_frame)
    bpy.utils.unregister_class(OBJECT_OT_create_repeat_animation)
    bpy.utils.unregister_class(OBJECT_OT_add_shape_key_to_selected)
    bpy.utils.unregister_class(OBJECT_OT_remove_shape_key_from_selected)

    del bpy.types.Scene.repeat_count
    del bpy.types.Scene.repeat_start
    del bpy.types.Scene.repeat_end
    del bpy.types.Scene.frame_change_amount

    bpy.app.handlers.depsgraph_update_post.remove(update_panels_on_object_change)

reset_shape_key_panels.previous_object = None

if __name__ == "__main__":
    register()
