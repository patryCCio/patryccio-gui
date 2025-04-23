import bpy
import random

class TextureBakerProps(bpy.types.PropertyGroup):
    bake_base_color: bpy.props.BoolProperty(name="Bake Base Color", default=True)
    bake_metallic: bpy.props.BoolProperty(name="Bake Metallic", default=True)
    bake_roughness: bpy.props.BoolProperty(name="Bake Rougnhess", default=True)
    bake_alpha: bpy.props.BoolProperty(name="Bake Alpha", default=True)
    bake_normal_map: bpy.props.BoolProperty(name="Bake Normal Map", default=True)

    texture_size: bpy.props.EnumProperty(
        name="",
        description="Select the size of the baked textures",
        items=[
            ('512', "512x512", ""),
            ('1024', "1024x1024", ""),
            ('2048', "2048x2048", ""),
            ('4096', "4096x4096", ""),
            ('8192', "8192x8192", "")
        ],
        default='2048'
    )
    bake_output_path: bpy.props.StringProperty(
        name="Bake Output Path",
        description="Folder to save baked textures",
        subtype='DIR_PATH',
        default="//"
    )
    material_name: bpy.props.EnumProperty(
        name="",
        description="Select material from active object",
        items=lambda self, context: self.get_material_items(context)
    )
    use_scene_cm: bpy.props.BoolProperty(
    name="Use Scene Color Management",
    description="Use current scene color management settings",
    default=False
    )

    def get_material_items(self, context):
        obj = context.active_object
        items = []
        if obj and obj.type == 'MESH' and obj.material_slots:
            for slot in obj.material_slots:
                if slot.material:
                    items.append((slot.material.name, slot.material.name, ""))
        return items if items else [('NONE', "No Materials", "")]


class BakeSimplifiedShaderOperator(bpy.types.Operator):
    bl_idname = "bake.shader_simplified"
    bl_label = "Bake Selected Channels (No UV Setup)"

    def execute(self, context):
        obj = context.active_object
        props = context.scene.prop_texture_baker
        size = int(props.texture_size)
        output_path = bpy.path.abspath(props.bake_output_path)

        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Select a mesh object")
            return {'CANCELLED'}

        if props.material_name == 'NONE':
            self.report({'ERROR'}, "No material selected")
            return {'CANCELLED'}

        mat_slot = next((slot for slot in obj.material_slots if slot.material and slot.material.name == props.material_name), None)
        if not mat_slot:
            self.report({'ERROR'}, "Material not found")
            return {'CANCELLED'}

        material = mat_slot.material
        if not material.use_nodes:
            self.report({'ERROR'}, "Material must use nodes")
            return {'CANCELLED'}

        node_tree = material.node_tree
        bsdf_node = next((n for n in node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        output_node = next((n for n in node_tree.nodes if n.type == 'OUTPUT_MATERIAL'), None)
        if not bsdf_node or not output_node:
            self.report({'ERROR'}, "Missing BSDF or Output node")
            return {'CANCELLED'}

        bake_channels = {
            "Base Color": (props.bake_base_color, "Base Color", 'base_color'),
            "Roughness": (props.bake_roughness, "Roughness", 'roughness'),
            "Metallic": (props.bake_metallic, "Metallic", 'metallic'),
            "Alpha": (props.bake_alpha, "Alpha", 'alpha'),
            "Normal": (props.bake_normal_map, "Normal", 'normal')
        }

        for label, (enabled, socket_name, suffix) in bake_channels.items():
            if not enabled:
                continue

            image_name = f"{material.name}_{suffix.upper()}"
            image = bpy.data.images.new(name=image_name, width=size, height=size, alpha=True)
            image.colorspace_settings.name = 'sRGB' if suffix == 'base_color' else 'Non-Color'

            tex_node = node_tree.nodes.new('ShaderNodeTexImage')
            tex_node.image = image
            tex_node.select = True
            node_tree.nodes.active = tex_node

            emission_node = node_tree.nodes.new('ShaderNodeEmission')
            if bsdf_node.inputs[socket_name].is_linked:
                from_socket = bsdf_node.inputs[socket_name].links[0].from_socket
                node_tree.links.new(emission_node.inputs["Color"], from_socket)
            else:
                val = bsdf_node.inputs[socket_name].default_value
                if isinstance(val, float):
                    emission_node.inputs["Color"].default_value = (val, val, val, 1)
                else:
                    emission_node.inputs["Color"].default_value = val

            node_tree.links.new(output_node.inputs["Surface"], emission_node.outputs["Emission"])

            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            context.view_layer.objects.active = obj

            bpy.context.scene.render.bake.use_selected_to_active = False
            bpy.context.scene.render.bake.use_clear = True
            bpy.context.scene.render.bake.margin = 2
            bpy.context.scene.render.bake.target = 'IMAGE_TEXTURES'

            try:
                bpy.ops.object.bake(type='EMIT', use_clear=True)
            except RuntimeError as e:
                self.report({'WARNING'}, f"Bake failed for {label}: {str(e)}")
                continue

            file_path = f"{output_path}/{image_name}.png"
            image.filepath_raw = file_path
            image.file_format = 'PNG'
            image.save()

            node_tree.nodes.remove(emission_node)
            node_tree.nodes.remove(tex_node)

        self.report({'INFO'}, "Selected channels baked (simplified)")
        return {'FINISHED'}
# ---------- Operators ----------
class BakeSingleOperator(bpy.types.Operator):
    bl_idname = "bake.texture_single"
    bl_label = "Bake Single"

    def execute(self, context):
        obj = context.active_object
        props = context.scene.prop_texture_baker
        size = int(props.texture_size)
        output_path = bpy.path.abspath(props.bake_output_path)

        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Select a mesh object")
            return {'CANCELLED'}

        if props.material_name == 'NONE':
            self.report({'ERROR'}, "No material selected")
            return {'CANCELLED'}

        mat = next((slot for slot in obj.material_slots if slot.material and slot.material.name == props.material_name), None)
        if not mat:
            self.report({'ERROR'}, "Material not found")
            return {'CANCELLED'}

        material = mat.material
        if not material.use_nodes:
            self.report({'ERROR'}, "Material must use nodes")
            return {'CANCELLED'}

        node_tree = material.node_tree
        bsdf_node = next((n for n in node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        output_node = next((n for n in node_tree.nodes if n.type == 'OUTPUT_MATERIAL'), None)
        if not bsdf_node or not output_node:
            self.report({'ERROR'}, "Material missing BSDF or Output node")
            return {'CANCELLED'}

        # Zapamiętaj oryginalne połączenie BSDF → Output
        original_link = next((l for l in node_tree.links if l.from_node == bsdf_node and l.to_node == output_node), None)

        bake_types = {
            "Base Color": ("bake_base_color", "Base Color", 'base_color', 'EMIT', 'Base Color'),
            "Roughness": ("bake_roughness", "Roughness", 'roughness', 'EMIT', 'Roughness'),
            "Metallic": ("bake_metallic", "Metallic", 'metallic', 'EMIT', 'Metallic'),
            "Alpha": ("bake_alpha", "Alpha", 'alpha', 'EMIT', 'Alpha'),
            "Normal": ("bake_normal_map", "Normal", 'normal', 'NORMAL', 'Normal')
        }

        for label, (prop_name, socket_name, suffix, bake_type, target_input) in bake_types.items():
            if not getattr(props, prop_name):
                continue

            image_name = f"{material.name}_{suffix.upper()}"
            image = bpy.data.images.new(name=image_name, width=size, height=size, alpha=True)
            image.colorspace_settings.name = 'sRGB' if suffix == 'base_color' else 'Non-Color'

            tex_node = node_tree.nodes.new('ShaderNodeTexImage')
            tex_node.image = image
            tex_node.image.colorspace_settings.name = image.colorspace_settings.name
            tex_node.select = True
            node_tree.nodes.active = tex_node

            emission_node = None
            if bake_type == 'EMIT':
                emission_node = node_tree.nodes.new('ShaderNodeEmission')
                if bsdf_node.inputs[target_input].is_linked:
                    from_socket = bsdf_node.inputs[target_input].links[0].from_socket
                    node_tree.links.new(emission_node.inputs["Color"], from_socket)
                else:
                    val = bsdf_node.inputs[target_input].default_value
                    if isinstance(val, float):
                        emission_node.inputs["Color"].default_value = (val, val, val, 1)
                    else:
                        emission_node.inputs["Color"].default_value = val
                node_tree.links.new(output_node.inputs["Surface"], emission_node.outputs["Emission"])

            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            context.view_layer.objects.active = obj

            bpy.context.scene.render.bake.use_selected_to_active = False
            bpy.context.scene.render.bake.use_clear = True
            bpy.context.scene.render.bake.margin = 2
            bpy.context.scene.render.bake.target = 'IMAGE_TEXTURES'

            try:
                bpy.ops.object.bake(type=bake_type, use_clear=True)
            except RuntimeError as e:
                self.report({'WARNING'}, f"Bake failed for {label}: {str(e)}")
                continue

            file_path = f"{output_path}/{image_name}.png"
            image.filepath_raw = file_path
            image.file_format = 'PNG'
            image.save()

            # Podłącz baked teksturę do odpowiedniego inputu BSDF
            if target_input in bsdf_node.inputs:
                node_tree.links.new(bsdf_node.inputs[target_input], tex_node.outputs['Color'])

            if bake_type == 'NORMAL':
                normal_map = node_tree.nodes.new('ShaderNodeNormalMap')
                normal_map.location = (tex_node.location.x + 200, tex_node.location.y)
                node_tree.links.new(normal_map.inputs['Color'], tex_node.outputs['Color'])
                node_tree.links.new(bsdf_node.inputs['Normal'], normal_map.outputs['Normal'])

            # Usuwamy tymczasowe emissiony, zostawiamy baked node
            if emission_node:
                node_tree.nodes.remove(emission_node)

        # Przywróć BSDF do Output
        if original_link:
            node_tree.links.new(original_link.to_socket, original_link.from_socket)

        self.report({'INFO'}, "Bake completed and textures assigned")
        return {'FINISHED'}

class BakeAllObjectOperator(bpy.types.Operator):
    bl_idname = "bake.texture_object"
    bl_label = "Bake All for Object"

    def execute(self, context):
        self.report({'INFO'}, "Bake All for Object executed (to implement)")
        return {'FINISHED'}

class BakeAllSceneOperator(bpy.types.Operator):
    bl_idname = "bake.texture_scene"
    bl_label = "Bake All for Scene"

    def execute(self, context):
        self.report({'INFO'}, "Bake All for Scene executed (to implement)")
        return {'FINISHED'}


# ---------- UI Panel ----------
class TextureBaker(bpy.types.Panel):
    bl_label = "Texture Baker"
    bl_idname = "VIEW3D_PT_Texture_Baker"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'GUI PatryCCio'  

    def draw(self, context):
        layout = self.layout
        props = context.scene.prop_texture_baker
        box = layout.box()
        box.label(text="Texture baker")

        box.operator("bake.shader_simplified", text="Bake Selected Channels", icon='MATERIAL')

        box.prop(props, "bake_base_color")
        box.prop(props, "bake_metallic")
        box.prop(props, "bake_roughness")
        box.prop(props, "bake_alpha")
        box.prop(props, "bake_normal_map")
        
        box.separator()
        box.label(text="Texture size:")
        box.prop(props, "texture_size")

        box.separator()
        box.label(text="Output folder:")
        box.prop(props, "bake_output_path")

        box.prop(props, "use_scene_cm")

        box.separator()
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            box.label(text="Select mesh", icon='ERROR')
        elif not obj.material_slots:
            box.label(text="Object doesn't have material!", icon='ERROR')
        else:
            box.label(text="Select material:")
            box.prop(props, "material_name")
            box.separator()
            box.operator("bake.texture_single", text="Bake Single", icon='RENDER_STILL')
            box.operator("bake.texture_object", text="Bake All for Object", icon='RENDER_ANIMATION')
        
        box.operator("bake.texture_scene", text="Bake All for Scene", icon='SCENE_DATA')


# ---------- Register ----------
classes = [
    TextureBakerProps,
    TextureBaker,
    BakeSingleOperator,
    BakeAllObjectOperator,
    BakeAllSceneOperator,
    BakeSimplifiedShaderOperator,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.prop_texture_baker = bpy.props.PointerProperty(type=TextureBakerProps)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.prop_texture_baker

if __name__ == "__main__":
    register()
