import bpy
import mathutils
import math
import bgl
import gpu
from gpu_extras.batch import batch_for_shader

addon_keymaps = []

class ProportionalMoveProps(bpy.types.PropertyGroup):
    use_proportional: bpy.props.BoolProperty(name="Proportional Move", default=False)
    radius: bpy.props.FloatProperty(name="Radius", default=0.3, min=0.001)
    power: bpy.props.FloatProperty(name="Power", default=0.5, min=0.001, max=1.0)
    state_radius: bpy.props.IntProperty(name="State Radius", default=0)
    affect_selected_only: bpy.props.BoolProperty(name="Affect Only Selected Bones", default=False)
    use_active_as_center: bpy.props.BoolProperty(name="Use active as center", default=False)
    falloff_exponent: bpy.props.FloatProperty(name="Falloff Smoothness", default=2.0, min=0.1, max=6.0)
    simulation_cloth: bpy.props.BoolProperty(name="Use Simulation Cloth", default=False)
    invert_falloff: bpy.props.BoolProperty(name="Invert falloff", default=False)
    state_shortcut: bpy.props.IntProperty(default=0)

class POSE_OT_proportional_move_modal(bpy.types.Operator):
    bl_idname = "pose.proportional_move_modal"
    bl_label = "Proportional Move (Interactive)"
    bl_options = {'REGISTER', 'UNDO', 'GRAB_CURSOR', 'BLOCKING'}

    _draw_handle = None
    _start_mouse = None
    _orig_positions = {}

    def draw_circle(self, context):
        props = context.scene.prop_move_props
        if not props.use_proportional:
            return

        region = context.region
        rv3d = context.region_data
        if rv3d is None:
            return

        shader = gpu.shader.from_builtin('UNIFORM_COLOR')

        center = mathutils.Vector((0, 0, 0))
        total = 0
        arms = [obj for obj in bpy.context.selected_objects if obj.type == 'ARMATURE']

        for arm in arms:
            selected = [b for b in arm.pose.bones if b.bone.select]
            active = arm.pose.bones.get(arm.data.bones.active.name) if arm.data.bones.active else None
            if props.use_active_as_center and active:
                center = arm.matrix_world @ active.head
                break
            elif selected:
                for b in selected:
                    center += arm.matrix_world @ b.head
                    total += 1
                if total > 0:
                    center /= total

        def draw_ring(center, radius, color, segments=64):
            verts = []
            for i in range(segments):
                angle = 2 * math.pi * i / segments
                x = radius * math.cos(angle)
                y = radius * math.sin(angle)
                point = center + rv3d.view_rotation @ mathutils.Vector((x, y, 0))
                verts.append(point)
            batch = batch_for_shader(shader, 'LINE_LOOP', {"pos": verts})
            shader.bind()
            shader.uniform_float("color", color)
            batch.draw(shader)

        def weight_to_color(weight):
            # Red (1.0) → Yellow (0.5) → Green (0.0)
            if weight > 0.5:
                t = (weight - 0.5) * 2
                return (1.0, 1.0 * (1 - t), 0.0, 0.5)
            else:
                t = weight * 2
                return (t, 1.0, 0.0, 0.5)

        # Włącz blending (opcjonalne w Blenderze 4.4)
        # bgl.glEnable(bgl.GL_BLEND)

        # Rysuj warstwy falloffa
        layers = 8  # Liczba warstw gradientu
        for i in range(1, layers + 1):
            frac = i / layers
            dist = props.radius * frac
            weight = max(0.0, ((props.radius - dist) / props.radius) ** props.falloff_exponent)
            color = weight_to_color(weight)
            draw_ring(center, dist, color)

        # Rysuj zewnętrzny kontur radius jako cienką białą linię
        draw_ring(center, props.radius, (1.0, 1.0, 1.0, 0.8))

    def apply_rotation_towards(self, bone, move_vec_local, weight):
        if bone.rotation_mode != 'QUATERNION':
            bone.rotation_mode = 'QUATERNION'

        head_world = bone.id_data.matrix_world @ bone.head
        tail_world = bone.id_data.matrix_world @ bone.tail
        center = self._center

        dist_head = (head_world - center).length
        dist_tail = (tail_world - center).length

        if dist_tail < dist_head:
            bone_direction = (tail_world - head_world).normalized()
            target_direction = (center - tail_world).normalized()
        else:
            bone_direction = (head_world - tail_world).normalized()
            target_direction = (center - head_world).normalized()

        rotation_axis = bone_direction.cross(target_direction)
        angle = bone_direction.angle(target_direction)

        if rotation_axis.length > 0:
            rot_quat = mathutils.Quaternion(rotation_axis.normalized(), angle * weight)
            bone.rotation_quaternion = rot_quat @ bone.rotation_quaternion

    def modal(self, context, event):
        props = context.scene.prop_move_props
        arms = [obj for obj in bpy.context.selected_objects if obj.type == 'ARMATURE']
        props.state_shortcut = 1

        if len(arms) > 1:
            props.affect_selected_only = False

        if event.type in {'RIGHTMOUSE', 'ESC'}:
            for arm in arms:
                for name, loc in self._orig_positions.items():
                    if name in arm.pose.bones:
                        arm.pose.bones[name].location = loc
                        
                        # Przywróć rotację w odpowiednim formacie
                        if name in self._orig_rotations:
                            if arm.pose.bones[name].rotation_mode == 'QUATERNION':
                                arm.pose.bones[name].rotation_quaternion = self._orig_rotations[name]  # Przywróć kwaternion
                            else:
                                arm.pose.bones[name].rotation_euler = self._orig_rotations[name]  # Przywróć rotację Euler

            props.state_shortcut = 0
            props.invert_falloff = False
            bpy.types.SpaceView3D.draw_handler_remove(self._draw_handle, 'WINDOW')
            self._draw_handle = None
            return {'CANCELLED'}

        elif event.type == 'LEFTMOUSE':
            for arm in arms:
                for bone in arm.pose.bones:
                    bone.keyframe_insert(data_path="location", frame=context.scene.frame_current)

                    # Dodajemy warunek dla rotacji
                    if bone.rotation_mode == 'QUATERNION':
                        bone.keyframe_insert(data_path="rotation_quaternion", frame=context.scene.frame_current)
                    else:
                        bone.keyframe_insert(data_path="rotation_euler", frame=context.scene.frame_current)

                    bone.keyframe_insert(data_path="scale", frame=context.scene.frame_current)

            props.state_shortcut = 0
            props.invert_falloff = False
            bpy.types.SpaceView3D.draw_handler_remove(self._draw_handle, 'WINDOW')
            self._draw_handle = None
            return {'FINISHED'}

        elif event.type == 'MOUSEMOVE':
            dx = (event.mouse_region_x - self._start_mouse[0]) * props.power
            dy = (event.mouse_region_y - self._start_mouse[1]) * props.power

            region = context.region
            rv3d = context.region_data
            view_rotation = rv3d.view_rotation

            right = view_rotation @ mathutils.Vector((1.0, 0.0, 0.0))
            up = view_rotation @ mathutils.Vector((0.0, 1.0, 0.0))

            move_vec_world = (right * dx + up * dy) * 0.1

            all_bones = []
            center = mathutils.Vector((0, 0, 0))
            total = 0

            for arm in arms:
                selected = [b for b in arm.pose.bones if b.bone.select]
                active = arm.pose.bones.get(arm.data.bones.active.name) if arm.data.bones.active else None

                for b in arm.pose.bones:
                    if b.name in self._orig_positions:
                        b.location = self._orig_positions[b.name].copy()

                all_bones.extend([(arm, b) for b in arm.pose.bones])

                if center.length == 0:
                    if props.use_active_as_center and active:
                        center = arm.matrix_world @ active.head
                    elif selected:
                        for b in selected:
                            center += arm.matrix_world @ b.head
                            total += 1
                        if total > 0:
                            center /= total

            self._center = center
            for arm, b in all_bones:
                if b.name not in self._orig_positions:
                    continue

                bone_head_world = arm.matrix_world @ b.head
                dist = (bone_head_world - center).length
                bone_matrix = arm.matrix_world @ b.bone.matrix_local.to_4x4()
                move_vec_local = bone_matrix.inverted().to_3x3() @ move_vec_world
                weight = 0
                if props.affect_selected_only:
                    if b == arm.pose.bones.get(arm.data.bones.active.name):
                        b.location += move_vec_local * 0.05
                    elif b.bone.select:
                        if dist < props.radius:
                            if props.simulation_cloth and props.invert_falloff:
                                weight = max(0.003, ((dist) / props.radius) ** props.falloff_exponent)
                                weight2 = max(0.003, ((props.radius - dist) / props.radius) ** props.falloff_exponent)
                                b.location += move_vec_local * weight2 * 0.05
                            else:
                                weight = max(0.003, ((props.radius - dist) / props.radius) ** props.falloff_exponent)
                                b.location += move_vec_local * weight * 0.05


                            if props.simulation_cloth and b.name in self._orig_rotations:
                                # Przywracanie przed rotacją
                                if b.rotation_mode == 'QUATERNION':
                                    b.rotation_quaternion = self._orig_rotations[b.name].copy()
                                else:
                                    b.rotation_euler = self._orig_rotations[b.name].copy()

                                if b != active:
                                    self.apply_rotation_towards(b, move_vec_local, weight)
                else:
                    if dist < props.radius:
                        if props.simulation_cloth and props.invert_falloff:
                            weight = max(0.003, ((dist) / props.radius) ** props.falloff_exponent)
                            weight2 = max(0.003, ((props.radius - dist) / props.radius) ** props.falloff_exponent)
                            b.location += move_vec_local * weight2 * 0.05
                        else:
                            weight = max(0.003, ((props.radius - dist) / props.radius) ** props.falloff_exponent)
                            b.location += move_vec_local * weight * 0.05
                        

                        if props.simulation_cloth and b.name in self._orig_rotations:
                            if b.rotation_mode == 'QUATERNION':
                                b.rotation_quaternion = self._orig_rotations[b.name].copy()
                            else:
                                b.rotation_euler = self._orig_rotations[b.name].copy()
                            if b != active:
                                self.apply_rotation_towards(b, move_vec_local, weight)
                                
                    elif b.bone.select:
                        b.location += move_vec_local

                        if props.simulation_cloth and b.name in self._orig_rotations:
                            # Przywracanie rotacji poza promieniem
                            if b.rotation_mode == 'QUATERNION':
                                b.rotation_quaternion = self._orig_rotations[b.name].copy()
                            else:
                                b.rotation_euler = self._orig_rotations[b.name].copy()

        # Obsługa klawiszy
        if event.type == 'ONE' and event.value == 'PRESS':
            props.state_radius = 0
        elif event.type == 'TWO' and event.value == 'PRESS':
            props.state_radius = 2
        elif event.type == 'THREE' and event.value == 'PRESS':
            props.state_radius = 1
        elif event.type == 'FOUR' and event.value == 'PRESS':
            props.use_active_as_center = not props.use_active_as_center
        elif event.type == 'FIVE' and event.value == 'PRESS':
            props.affect_selected_only = not props.affect_selected_only
        elif event.type == 'SIX' and event.value == 'PRESS':
            helper = props.simulation_cloth
            props.simulation_cloth = not props.simulation_cloth
            if helper:
                props.invert_falloff = False
                for arm in arms:
                    for name, loc in self._orig_positions.items():
                        if name in arm.pose.bones:
                            arm.pose.bones[name].location = loc
                            
                            # Przywróć rotację w odpowiednim formacie
                            if name in self._orig_rotations:
                                if arm.pose.bones[name].rotation_mode == 'QUATERNION':
                                    arm.pose.bones[name].rotation_quaternion = self._orig_rotations[name]  # Przywróć kwaternion
                                else:
                                    arm.pose.bones[name].rotation_euler = self._orig_rotations[name]  # Przywróć rotację Euler

                props.state_shortcut = 0
                props.invert_falloff = False
                bpy.types.SpaceView3D.draw_handler_remove(self._draw_handle, 'WINDOW')
                self._draw_handle = None
                return {'CANCELLED'}
        elif event.type == 'SEVEN' and event.value == 'PRESS':
            props.invert_falloff = not props.invert_falloff
        

        elif event.type == 'WHEELUPMOUSE':
            if props.state_radius == 0:
                if props.radius < 0.05:
                    props.radius += 0.001
                elif props.radius >= 0.05 and props.radius < 0.16:
                    props.radius += 0.0075
                else:
                    props.radius += 0.0125
            elif props.state_radius == 1:
                if props.power < 0.05:
                    props.power += 0.001
                elif props.power >= 0.05 and props.power < 0.16:
                    props.power += 0.0075
                else:
                    props.power += 0.0125
            elif props.state_radius == 2:
                step = 0.01 + 0.1 * math.sqrt(props.falloff_exponent)
                props.falloff_exponent += step

        elif event.type == 'WHEELDOWNMOUSE':
            if props.state_radius == 0:
                if props.radius < 0.05:
                    props.radius = max(0.001, props.radius - 0.001)
                elif props.radius >= 0.05 and props.radius < 0.16:
                    props.radius = max(0.001, props.radius - 0.0075)
                else:
                    props.radius = max(0.001, props.radius - 0.0125)
            elif props.state_radius == 1:
                if props.power < 0.05:
                    props.power = max(0.001, props.power - 0.001)
                elif props.power >= 0.05 and props.power < 0.16:
                    props.power = max(0.001, props.power - 0.0075)
                else:
                    props.radius = max(0.001, props.radius - 0.0125)
            elif props.state_radius == 2:
                step = 0.01 + 0.1 * math.sqrt(props.falloff_exponent)
                props.falloff_exponent = max(0.1, props.falloff_exponent - step)

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
        self._orig_rotations = {}

        for arm in arms:
            for b in arm.pose.bones:
                # Zapisz oryginalną pozycję
                self._orig_positions[b.name] = b.location.copy()
                    
                # Zapisz rotację w odpowiednim formacie
                if b.rotation_mode == 'QUATERNION':
                    self._orig_rotations[b.name] = b.rotation_quaternion.copy()  # Zapisz kwaternion
                else:
                    self._orig_rotations[b.name] = b.rotation_euler.copy()  # Zapisz rotację Euler

        context.window_manager.modal_handler_add(self)
        self._draw_handle = bpy.types.SpaceView3D.draw_handler_add(self.draw_circle, (context,), 'WINDOW', 'POST_VIEW')
        return {'RUNNING_MODAL'}

class POSE_OT_proportional_rotate_modal(bpy.types.Operator):
    bl_idname = "pose.proportional_rotate_modal"
    bl_label = "Proportional Rotate (Interactive)"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING'}

    _start_mouse = None
    _orig_rotations = {}
    _draw_handle = None

    def draw_circle(self, context):
        props = context.scene.prop_move_props
        if not props.use_proportional:
            return

        region = context.region
        rv3d = context.region_data
        if rv3d is None:
            return

        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        center = mathutils.Vector((0, 0, 0))
        total = 0
        arms = [obj for obj in bpy.context.selected_objects if obj.type == 'ARMATURE']

        for arm in arms:
            selected = [b for b in arm.pose.bones if b.bone.select]
            active = arm.pose.bones.get(arm.data.bones.active.name) if arm.data.bones.active else None
            if props.use_active_as_center and active:
                center = arm.matrix_world @ active.head
                break
            elif selected:
                for b in selected:
                    center += arm.matrix_world @ b.head
                    total += 1
                if total > 0:
                    center /= total

        def draw_ring(center, radius, color, segments=64):
            verts = []
            for i in range(segments):
                angle = 2 * math.pi * i / segments
                x = radius * math.cos(angle)
                y = radius * math.sin(angle)
                point = center + rv3d.view_rotation @ mathutils.Vector((x, y, 0))
                verts.append(point)
            batch = batch_for_shader(shader, 'LINE_LOOP', {"pos": verts})
            shader.bind()
            shader.uniform_float("color", color)
            batch.draw(shader)

        def weight_to_color(weight):
            if weight > 0.5:
                t = (weight - 0.5) * 2
                return (1.0, 1.0 * (1 - t), 0.0, 0.5)
            else:
                t = weight * 2
                return (t, 1.0, 0.0, 0.5)

        layers = 8
        for i in range(1, layers + 1):
            frac = i / layers
            dist = props.radius * frac
            weight = max(0.0, ((props.radius - dist) / props.radius) ** props.falloff_exponent)
            color = weight_to_color(weight)
            draw_ring(center, dist, color)

        draw_ring(center, props.radius, (1.0, 1.0, 1.0, 0.8))

    def modal(self, context, event):
        props = context.scene.prop_move_props
        arms = [obj for obj in bpy.context.selected_objects if obj.type == 'ARMATURE']
        props.state_shortcut = 0
        props.invert_falloff = False

        if event.type in {'RIGHTMOUSE', 'ESC'}:
            for arm in arms:
                for name, quat in self._orig_rotations.items():
                    if name in arm.pose.bones:
                        bone = arm.pose.bones[name]
                        bone.rotation_quaternion = quat.copy()
            bpy.types.SpaceView3D.draw_handler_remove(self._draw_handle, 'WINDOW')
            self._draw_handle = None
            return {'CANCELLED'}

        elif event.type == 'LEFTMOUSE':
            for arm in arms:
                for bone in arm.pose.bones:
                    bone.keyframe_insert(data_path="rotation_quaternion", frame=context.scene.frame_current)
            bpy.types.SpaceView3D.draw_handler_remove(self._draw_handle, 'WINDOW')
            self._draw_handle = None
            return {'FINISHED'}

        elif event.type == 'MOUSEMOVE':
            dx = (event.mouse_region_x - self._start_mouse[0]) * props.power
            dy = (event.mouse_region_y - self._start_mouse[1]) * props.power
            angle = -dy * 0.05  # Obrót wokół osi Y, możesz dodać inne osie w zależności od preferencji

            rv3d = context.region_data
            view_rot = rv3d.view_rotation
            rot_axis = view_rot @ mathutils.Vector((0.0, 0.0, -1.0))  # Oś Z w przestrzeni widoku

            all_bones = []
            center = mathutils.Vector((0, 0, 0))
            total = 0

            for arm in arms:
                selected = [b for b in arm.pose.bones if b.bone.select]
                active = arm.pose.bones.get(arm.data.bones.active.name) if arm.data.bones.active else None
                all_bones.extend([(arm, b) for b in arm.pose.bones])

                if center.length == 0:
                    if props.use_active_as_center and active:
                        center = arm.matrix_world @ active.head
                    elif selected:
                        for b in selected:
                            center += arm.matrix_world @ b.head
                            total += 1
                        if total > 0:
                            center /= total

            for arm, b in all_bones:
                if b.name not in self._orig_rotations:
                    continue

                if b.rotation_mode != 'QUATERNION':
                    b.rotation_mode = 'QUATERNION'
                b.rotation_quaternion = self._orig_rotations[b.name].copy()

                # Obliczanie rotacji w przestrzeni lokalnej armatury
                bone_head_world = arm.matrix_world @ b.head
                dist = (bone_head_world - center).length

                # Uwzględnianie transformacji rodzica i lokalnych osi rotacji
                bone_matrix = arm.matrix_world @ b.bone.matrix_local.to_4x4()
                bone_local_rot_axis = bone_matrix.inverted().to_3x3() @ rot_axis

                if props.affect_selected_only:
                    if b.bone.select or b == arm.pose.bones.get(arm.data.bones.active.name):
                        if dist < props.radius:
                            weight = max(0.003, ((props.radius - dist) / props.radius) ** props.falloff_exponent)
                            rot_quat = mathutils.Quaternion(bone_local_rot_axis, angle * weight)
                            b.rotation_quaternion = rot_quat @ b.rotation_quaternion
                else:
                    if dist < props.radius:
                        weight = max(0.003, ((props.radius - dist) / props.radius) ** props.falloff_exponent)
                        rot_quat = mathutils.Quaternion(bone_local_rot_axis, angle * weight)
                        b.rotation_quaternion = rot_quat @ b.rotation_quaternion

        # Obsługa klawiszy pomocniczych
        if event.type == 'ONE' and event.value == 'PRESS':
            props.state_radius = 0
        elif event.type == 'TWO' and event.value == 'PRESS':
            props.state_radius = 2
        elif event.type == 'THREE' and event.value == 'PRESS':
            props.state_radius = 1
        elif event.type == 'FOUR' and event.value == 'PRESS':
            props.use_active_as_center = not props.use_active_as_center
        elif event.type == 'FIVE' and event.value == 'PRESS':
            props.affect_selected_only = not props.affect_selected_only
        elif event.type == 'WHEELUPMOUSE':
            if props.state_radius == 0:
                props.radius += 0.01
            elif props.state_radius == 1:
                props.power += 0.01
            elif props.state_radius == 2:
                props.falloff_exponent += 0.1
        elif event.type == 'WHEELDOWNMOUSE':
            if props.state_radius == 0:
                props.radius = max(0.001, props.radius - 0.01)
            elif props.state_radius == 1:
                props.power = max(0.001, props.power - 0.01)
            elif props.state_radius == 2:
                props.falloff_exponent = max(0.1, props.falloff_exponent - 0.1)

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
        self._orig_rotations = {}

        for arm in arms:
            for b in arm.pose.bones:
                if b.rotation_mode != 'QUATERNION':
                    b.rotation_mode = 'QUATERNION'
                self._orig_rotations[b.name] = b.rotation_quaternion.copy()

        context.window_manager.modal_handler_add(self)
        self._draw_handle = bpy.types.SpaceView3D.draw_handler_add(self.draw_circle, (context,), 'WINDOW', 'POST_VIEW')
        return {'RUNNING_MODAL'}


class POSE_PT_proportional_move(bpy.types.Panel):
    bl_label = "Proportional Move"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "GUI PatryCCio"
    bl_idname = 'POSE_PT_proportional_move'
    bl_parent_id= 'VIEW3D_PT_bone_edit'

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

            if props.state_radius == 0:
                box3.label(text="Change on wheel: Radius")
            elif props.state_radius == 1:
                box3.label(text="Change on wheel: Power")
            elif props.state_radius == 2:
                box3.label(text="Change on wheel: Falloff")

            box.prop(props, "radius")
            box.prop(props, "power")
            box.prop(props, "falloff_exponent", text="Smoothness")
            box.prop(props, "use_active_as_center")

            if len(arms) == 1:
                box.prop(props, "affect_selected_only")
            if props.state_shortcut == 1:
                box.prop(props, "simulation_cloth")
                if props.simulation_cloth:
                    box.prop(props, "invert_falloff")

            box2 = box.box()
            box2.label(text="CTRL + G - Proportional move")
            box2.label(text="CTRL + R - Proportional rotate")
            box2.label(text="1 - Set radius mode")
            box2.label(text="2 - Set falloff mode")
            box2.label(text="3 - Set power mode")
            box2.label(text="4 - Use active as center")
            box2.label(text="5 - Affect only selected bones")
            if props.state_shortcut == 1:
                box2.label(text="6 - Use simulation cloth (only within move)")
                if props.simulation_cloth:
                    box2.label(text="7 - Invert falloff (only within simulation cloth)")


addon_keymaps = []

def register():
    bpy.utils.register_class(ProportionalMoveProps)
    bpy.types.Scene.prop_move_props = bpy.props.PointerProperty(type=ProportionalMoveProps)
    bpy.utils.register_class(POSE_OT_proportional_move_modal)
    bpy.utils.register_class(POSE_PT_proportional_move)

    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps.new(name='Pose', space_type='EMPTY')
    kmi = km.keymap_items.new(POSE_OT_proportional_move_modal.bl_idname, 'G', 'PRESS', ctrl=True)
    addon_keymaps.append((km, kmi))

    bpy.utils.register_class(POSE_OT_proportional_rotate_modal)
    kmi = km.keymap_items.new(POSE_OT_proportional_rotate_modal.bl_idname, 'R', 'PRESS', ctrl=True)
    addon_keymaps.append((km, kmi))

def unregister():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    bpy.utils.unregister_class(ProportionalMoveProps)
    del bpy.types.Scene.prop_move_props
    bpy.utils.unregister_class(POSE_OT_proportional_move_modal)
    bpy.utils.unregister_class(POSE_PT_proportional_move)
    bpy.utils.unregister_class(POSE_OT_proportional_rotate_modal)

if __name__ == "__main__":
    register()
