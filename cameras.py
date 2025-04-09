import bpy

class VIEW3D_PT_cameras(bpy.types.Panel):
    bl_label = "Cameras"
    bl_idname = "VIEW3D_PT_cameras"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'GUI PatryCCio'

    def draw(self, context):
        layout = self.layout

        cameras = [obj for obj in bpy.data.objects if obj.type == 'CAMERA']
        if not cameras:
            layout.label(text="No cameras found.")
            return

        for cam in cameras:
            box = layout.box()
            box.label(text=cam.name)

            row = box.row(align=True)
            op = row.operator("view3d.set_active_camera", text="Set Active")
            op.camera_name = cam.name

            row.operator("view3d.fix_camera", text="Fix").camera_name = cam.name


class VIEW3D_OT_set_active_camera(bpy.types.Operator):
    bl_idname = "view3d.set_active_camera"
    bl_label = "Set Active Camera"

    camera_name: bpy.props.StringProperty()

    def execute(self, context):
        cam = bpy.data.objects.get(self.camera_name)
        if cam and cam.type == 'CAMERA':
            context.scene.camera = cam
            self.report({'INFO'}, f"Set active camera: {cam.name}")
        else:
            self.report({'WARNING'}, "Camera not found or invalid type")
        return {'FINISHED'}


class VIEW3D_OT_fix_camera(bpy.types.Operator):
    bl_idname = "view3d.fix_camera"
    bl_label = "Fix Camera"

    camera_name: bpy.props.StringProperty()

    def execute(self, context):
        cam = bpy.data.objects.get(self.camera_name)
        if cam and cam.type == 'CAMERA':
            current_view = context.space_data.region_3d.view_location.copy()

            cam.rotation_euler = (0.0, 0.0, 0.0)

            bpy.ops.view3d.view_camera()
            
            region_3d = context.space_data.region_3d
        
            region_3d.view_rotation = (0,0,0,0)

            self.report({'INFO'}, f"Fixed and switched to camera view: {self.camera_name}")
        else:
            self.report({'WARNING'}, "Camera not found or invalid type")

        return {'FINISHED'}



classes = [
    VIEW3D_PT_cameras,
    VIEW3D_OT_set_active_camera,
    VIEW3D_OT_fix_camera
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
