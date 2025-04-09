import bpy
import mathutils

addon_keymaps = []

class ProportionalMoveProps(bpy.types.PropertyGroup):
    use_proportional: bpy.props.BoolProperty(name="Proportional Move", default=False)
    radius: bpy.props.FloatProperty(name="Radius", default=0.6, min=0.05)
    power: bpy.props.FloatProperty(name="Power", default=0.5, min=0.1, max=1.0)

    state_radius: bpy.props.IntProperty(name="State Radius", default=0)
    affect_selected_only: bpy.props.BoolProperty(name="Affect Only Selected Bones", default=False)
    use_active_as_center: bpy.props.BoolProperty(name="Use active as center", default=False)

class POSE_OT_proportional_move_modal(bpy.types.Operator):
    bl_idname = "pose.proportional_move_modal"
    bl_label = "Proportional Move (Interactive)"
    bl_options = {'REGISTER', 'UNDO', 'GRAB_CURSOR', 'BLOCKING'}

    _start_mouse = None
    _orig_positions = {}

    def modal(self, context, event):
        props = context.scene.prop_move_props
        arms = [obj for obj in bpy.context.selected_objects if obj.type == 'ARMATURE']

        if len(arms) > 1:
            props.affect_selected_only = False

        if event.type in {'RIGHTMOUSE', 'ESC'}:
            for arm in arms:
                for name, loc in self._orig_positions.items():
                    if name in arm.pose.bones:
                        arm.pose.bones[name].location = loc
            return {'CANCELLED'}

        elif event.type == 'LEFTMOUSE':
            for arm in arms:
                for bone in arm.pose.bones:
                    bone.keyframe_insert(data_path="location", frame=context.scene.frame_current)
                    bone.keyframe_insert(data_path="rotation_euler", frame=context.scene.frame_current)
                    bone.keyframe_insert(data_path="scale", frame=context.scene.frame_current)

            return {'FINISHED'}

        elif event.type == 'MOUSEMOVE':
            dx = (event.mouse_region_x - self._start_mouse[0]) * props.power
            dy = (event.mouse_region_y - self._start_mouse[1]) * props.power

            # Zamiana ruchu myszy na ruch w przestrzeni 3D względem widoku
            view_rotation = bpy.context.region_data.view_rotation
            right = view_rotation @ mathutils.Vector((1.0, 0.0, 0.0))
            up = view_rotation @ mathutils.Vector((0.0, 1.0, 0.0))

            # Modyfikacja przekształcenia do lokalnej przestrzeni armatury
            move_vec_3d = (right * dx + up * dy) * 0.1

            all_bones = []
            center = mathutils.Vector()

            for arm in arms:
                selected = [b for b in arm.pose.bones if b.bone.select]
                active = arm.pose.bones.get(arm.data.bones.active.name) if arm.data.bones.active else None

                for b in arm.pose.bones:
                    if b.name in self._orig_positions:
                        b.location = self._orig_positions[b.name].copy()

                all_bones.extend(arm.pose.bones)

                if center.length == 0:
                    if props.use_active_as_center and active:
                        center = active.head.copy()
                    elif selected:
                        center = sum((b.head for b in selected), mathutils.Vector()) / len(selected)

            for arm in arms:
                local_move_vec = move_vec_3d

                for b in all_bones:
                    if b.name not in self._orig_positions:
                        continue

                    dist = (b.head - center).length
                    local_move_vec = b.matrix.inverted() @ move_vec_3d

                    if props.affect_selected_only:
                        if b == active:
                            b.location += local_move_vec * 0.05
                        elif b in selected:
                            weight = max(0.003, ((props.radius - dist) / props.radius) ** 2)
                            b.location += local_move_vec * weight * 0.05  # Zmniejszenie wpływu
                    else:
                        if dist < props.radius:
                            weight = max(0.003, ((props.radius - dist) / props.radius) ** 2)
                            b.location += local_move_vec * weight * 0.05
                        elif b.bone.select:
                            b.location += local_move_vec

        # Obsługa klawiszy
        if event.type == 'ONE' and event.value == 'PRESS':
            props.state_radius = (props.state_radius + 1) % 2
        elif event.type == 'TWO' and event.value == 'PRESS':
            props.use_active_as_center = not props.use_active_as_center
        elif event.type == 'THREE' and event.value == 'PRESS':
            props.affect_selected_only = not props.affect_selected_only

        elif event.type == 'WHEELUPMOUSE':
            if props.state_radius == 0:
                props.radius += 0.05
            elif props.state_radius == 1:
                props.power += 0.05

        elif event.type == 'WHEELDOWNMOUSE':
            if props.state_radius == 0:
                props.radius = max(0.15, props.radius - 0.05)
            elif props.state_radius == 1:
                props.power = max(0.1, props.power - 0.05)

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        if context.mode != 'POSE':
            self.report({'WARNING'}, "Must be in Pose Mode")
            return {'CANCELLED'}

        props = context.scene.prop_move_props
        if not props.use_proportional:
            self.report({'WARNING'}, "Enable Proportional Move first")
            return {'CANCELLED'}

        arms = [obj for obj in bpy.context.selected_objects if obj.type == 'ARMATURE']
        if not arms:
            self.report({'WARNING'}, "No armatures selected")
            return {'CANCELLED'}

        self._start_mouse = (event.mouse_region_x, event.mouse_region_y)
        self._orig_positions = {}

        for arm in arms:
            for b in arm.pose.bones:
                self._orig_positions[b.name] = b.location.copy()

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

class POSE_PT_proportional_move(bpy.types.Panel):
    bl_label = "Proportional Move"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "GUI PatryCCio"
    # bl_parent_id= 'VIEW3D_PT_bone_edit'

    @classmethod
    def poll(cls, context):
        return context.mode == 'POSE'

    def draw(self, context):
        props = context.scene.prop_move_props
        layout = self.layout
        layout.prop(props, "use_proportional")
        arms = [obj for obj in bpy.context.selected_objects if obj.type == 'ARMATURE']

        if props.use_proportional:
            box = layout.box()
            box3 = box.box()

            box3.label(text=f"Change on wheel: {'Radius' if props.state_radius == 0 else 'Power'}")

            box.prop(props, "radius")
            box.prop(props, "power")
            if len(arms) == 1:
                box.prop(props, "affect_selected_only")
            box.prop(props, "use_active_as_center")

            box2 = box.box()
            box2.label(text="ALT + G - Use proportional editing")
            box2.label(text="1 - Toggle wheel mode")
            box2.label(text="2 - Use active as center")
            box2.label(text="3 - Affect only selected bones")


addon_keymaps = []

def register():
    bpy.utils.register_class(ProportionalMoveProps)
    bpy.types.Scene.prop_move_props = bpy.props.PointerProperty(type=ProportionalMoveProps)
    bpy.utils.register_class(POSE_OT_proportional_move_modal)
    bpy.utils.register_class(POSE_PT_proportional_move)

    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps.new(name='Pose', space_type='EMPTY')
    kmi = km.keymap_items.new(POSE_OT_proportional_move_modal.bl_idname, 'G', 'PRESS', alt=True)
    addon_keymaps.append((km, kmi))

def unregister():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    bpy.utils.unregister_class(ProportionalMoveProps)
    del bpy.types.Scene.prop_move_props
    bpy.utils.unregister_class(POSE_OT_proportional_move_modal)
    bpy.utils.unregister_class(POSE_PT_proportional_move)

if __name__ == "__main__":
    register()
