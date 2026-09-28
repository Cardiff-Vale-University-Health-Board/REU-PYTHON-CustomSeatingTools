import bpy
import mathutils

bl_info = {
    "name": "Cushion Processing Tools",
    "author": "Cardiff Rehabilitation Engineering Unit",
    "version": (0, 0, 0, 4),
    "blender": (3, 5)
}

G_PRINT_DEBUG = True

def calculate_triangle_normal_and_centre(v1, v2, v3):
    a = v2 - v1
    b = v3 - v1
    n = mathutils.Vector((
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0]
    ))
    c = mathutils.Vector((
        v1[0] + v2[0] + v3[0],
        v1[1] + v2[1] + v3[1],
        v1[2] + v2[2] + v3[2],
    )) / 3
    return n, c

def first_non_match(lst, val):
    for index, value in enumerate(lst):
        if value != val:
            return index, value
    return None, None

def transformation_matrix_from_vectors(v1, c1, v2, c2):
    """
    :param v1: A 3d "source" vector
    :param v2: A 3d "destination" vector
    :return mat: A transform matrix (4x4)
    """
    a = v1.normalized()
    b = v2.normalized()
    v = a.cross(b)
    c = a.dot(b)
        
    if(c == -1.0): # vectors are antiparrallel, pick an arbitrary rotation axes and calculate the rotation matrix
        axes = [
            mathutils.Vector((1.0, 0.0, 0.0)),
            mathutils.Vector((0.0, 1.0, 0.0)),
            mathutils.Vector((0.0, 0.0, 1.0))
        ]
        
        dot_products = [a.dot(vec) for vec in axes]
        i, c = first_non_match(dot_products, -1)
        v = a.cross(axes[i])
            
        R = mathutils.Matrix((
            [2*(v[0]*v[0]) - 1, 2*v[0]*v[1], 2*v[0]*v[2]],
            [2*v[0]*v[1], 2*(v[1]*v[1]) - 1, 2*v[1]*v[2]],
            [2*v[0]*v[2], 2*v[1]*v[2], 2*(v[2]*v[2]) - 1]
        ))
        
    elif(c == 1.0): # vectors are parrallel, no rotation required
        R = mathutils.Matrix.Identity(3)
        
    else:
        s = v.magnitude  
        K = mathutils.Matrix((
            [0, -v[2], v[1]],
            [v[2], 0, -v[0]],
            [-v[1], v[0], 0]
        ))    
        K2 = K @ K         
        I = mathutils.Matrix.Identity(3)
        division = (1 - c) / (s*s)
        R = I + K + K2 * division        
    
    R = R.to_4x4()                    
    T = mathutils.Matrix.Translation(c2 - c1)                

    return R @ T

class CREUProperties(bpy.types.PropertyGroup):
    active_tool: bpy.props.EnumProperty(
        items=[
            ("NONE", "None", ""),
            ("ALIGN", "Align", ""),
            ("FLIP", "Flip", ""),
            ("REDUCE", "Reduce", ""),
            ("ERASE", "Erase", ""),
            ("HOLES", "Filling Holes", ""),
            ("SMOOTH", "Smooth", ""),
            ("EXPORT", "Export", "")
        ],
        default="NONE"
    )

class StartAlignToOriginOperator(bpy.types.Operator):
    """Align the scan to the XY plane using three selected vertices.
    
    Select three vertices that define the seating surface, then click Align.
    The model will be rotated so that the selected surface lies flat on the
    XY plane and centred at the origin."""

    bl_idname = "creu.start_align"
    bl_label = "1. Align To Origin Tool"

    def execute(self, context):
        if context.active_object is None:
            self.report({'WARNING'}, "Please select an object")
            return {'CANCELLED'}

        context.scene.creu.active_tool = "ALIGN"
        bpy.ops.object.mode_set(mode='EDIT')
        return {'FINISHED'}

class StartInvertZAxisOperator(bpy.types.Operator):
    """Flip the model about the XY plane.
    
    Use this if the scan is upside down. The model will be rotated 180 degrees so that
    the seating surface faces upward."""

    bl_idname = "creu.start_flip_about_xy"
    bl_label = "2. Flip Model about XY Plane"

    def execute(self, context):
        if context.active_object is None:
            self.report({'WARNING'}, "Please select an object")
            return {'CANCELLED'}

        context.scene.creu.active_tool = "FLIP"
        bpy.ops.object.mode_set(mode='OBJECT')
        return {'FINISHED'}

class StartStandardiseMeshQualityOperator(bpy.types.Operator):
    """Standardise mesh resolution.

    Remesh the scan to produce a more consistent triangle size throughout the model.
    This improves the consistency of editing operations and reduces the number of
    triangles present."""

    bl_idname = "creu.start_mesh_quality"
    bl_label = "3. Standardise Mesh Resolution"

    def execute(self, context):
        if context.active_object is None:
            self.report({'WARNING'}, "Please select an object")
            return {'CANCELLED'}

        context.scene.creu.active_tool = "FLIP"
        bpy.ops.object.mode_set(mode='SCULPT')
        return {'FINISHED'}

class StartEraseMeshOperator(bpy.types.Operator):
    """Delete selected vertices and connected geometry.

    Use this tool to remove unwanted scan artefacts,
    isolated geometry, or areas outside the required seating surface."""

    bl_idname = "creu.start_erasing"
    bl_label = "4. Erase Vertices"

    def execute(self, context):
        if context.active_object is None:
            self.report({'WARNING'}, "Please select an object")
            return {'CANCELLED'}

        context.scene.creu.active_tool = "FLIP"
        bpy.ops.object.mode_set(mode='EDIT')
        return {'FINISHED'}

class StartHoleFillingOperator(bpy.types.Operator):
    """Fill holes in the scan.

    Automatically identify and close gaps in the mesh to create a more
    contiguous surface."""

    bl_idname = "creu.start_hole_filling"
    bl_label = "5. Fill Holes"

    def execute(self, context):
        if context.active_object is None:
            self.report({'WARNING'}, "Please select an object")
            return {'CANCELLED'}

        context.scene.creu.active_tool = "HOLES"
        bpy.ops.object.mode_set(mode='EDIT')
        return {'FINISHED'}

class StartSmoothingOperator(bpy.types.Operator):
    """Smooth the surface of the scan.

    Reduce sharp creases and local surface irregularities while preserving
    the overall shape of the cushion."""

    bl_idname = "creu.start_smooth"
    bl_label = "6. Remove Creases (Smoothing)"

    def execute(self, context):
        if context.active_object is None:
            self.report({'WARNING'}, "Please select an object")
            return {'CANCELLED'}

        context.scene.creu.active_tool = "SMOOTH"
        bpy.ops.object.mode_set(mode='SCULPT')
        return {'FINISHED'}

class StartExportOperator(bpy.types.Operator):
    """Export the processed model.

    Save the completed scan in a manufacturing-ready format for downstream design,
    machining, or archival purposes."""

    bl_idname = "creu.start_export"
    bl_label = "7. Export Model"

    def execute(self, context):
        if context.active_object is None:
            self.report({'WARNING'}, "Please select an object")
            return {'CANCELLED'}

        context.scene.creu.active_tool = "SMOOTH"
        bpy.ops.object.mode_set(mode='OBJECT')
        return {'FINISHED'}

class CancelAlignToOriginOperator(bpy.types.Operator):
    bl_idname = "creu.cancel_align"
    bl_label = "Cancel"

    def execute(self, context):
        context.scene.creu.active_tool = "NONE"
        bpy.ops.object.mode_set(mode='OBJECT')
        return {'FINISHED'}
        
class AlignToOriginOperator(bpy.types.Operator):
    """Aligns an object to the XY plane based on the three currently selected vertices"""
    bl_idname = "creu.align_to_origin"
    bl_label = "Align"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='EDIT')
        obj = bpy.context.active_object
        vertices = obj.data.vertices
        selected_vertices = [v for v in vertices if v.select]
        n, c = calculate_triangle_normal_and_centre(
            obj.matrix_world @ selected_vertices[0].co,
            obj.matrix_world @ selected_vertices[1].co,
            obj.matrix_world @ selected_vertices[2].co
        )
        T = transformation_matrix_from_vectors(
            n,
            c,
            mathutils.Vector((0.0, 0.0, 1.0)),
            mathutils.Vector((0.0, 0.0, 0.0))
        )
        obj.matrix_world = T @ obj.matrix_world
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.transform_apply(location=True, rotation=True)
        context.scene.creu.active_tool = "FLIP"
        return self.execute(context)

class NextToolOperator(bpy.types.Operator):
    bl_idname = "creu.next_tool"
    bl_label = "Skip Step"

    def execute(self, context):
        current = context.scene.creu.active_tool

        if current == "ALIGN":
            context.scene.creu.active_tool = "FLIP"

        elif current == "FLIP":
            context.scene.creu.active_tool = "STANDARDISE"

        elif current == "STANDARDISE":
            context.scene.creu.active_tool = "ERASE"

        elif current == "ERASE":
            context.scene.creu.active_tool = "FILL"

        elif current == "FILL":
            context.scene.creu.active_tool = "SMOOTH"

        elif current == "SMOOTH":
            context.scene.creu.active_tool = "EXPORT"

        return {'FINISHED'}
        

class CancelInvertZAxisOperator(bpy.types.Operator):
    bl_idname = "creu.cancel_flip_about_xy"
    bl_label = "Cancel"

    def execute(self, context):
        context.scene.creu.active_tool = "NONE"
        bpy.ops.object.mode_set(mode='OBJECT')
        return {'FINISHED'}
   
class InvertZAxisOperator(bpy.types.Operator):
    """Flips an object about the XY plane"""
    bl_idname = "creu.flip_about_xy"
    bl_label = "Flip"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        obj = bpy.context.active_object
        T = transformation_matrix_from_vectors(
            mathutils.Vector((0.0, 0.0, 1.0)),
            mathutils.Vector((0.0, 0.0, 0.0)),
            mathutils.Vector((0.0, 0.0, -1.0)),
            mathutils.Vector((0.0, 0.0, 0.0))
        )
        obj.matrix_world = T @ obj.matrix_world
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.transform_apply(location=True, rotation=True)
        context.scene.creu.active_tool = "NONE"
        return self.execute(context) 

def draw_align_workflow(layout):
    row = layout.row()
    row.label(text = 'Scan Alignment')
    row = layout.row()
    box = row.box()
    row = box.row()
    row.label(text=f"Please select three vertices.")
    row = box.row()

    nvert = 0
    if(len(bpy.context.selected_objects) > 0 and callable(getattr(bpy.context.active_object.data, 'count_selected_items', None))):
        (nvert, _, _) = bpy.context.active_object.data.count_selected_items()
    
    row = box.row()
    row.label(text = f"Selected vertices: {nvert}")
    
    align_enabled = True if nvert == 3 else False
    if(not align_enabled):
        row = box.row()
        row.label(text = f"Please select three vertices to use {AlignToOriginOperator.bl_label}.")

    row = layout.row()
    split = row.split(factor=0.5)
    left = split.column()
    right = split.column()
    left.alert = True
    left.operator(CancelAlignToOriginOperator.bl_idname, text = CancelAlignToOriginOperator.bl_label)
    right.enabled = align_enabled
    right.emboss = 'NORMAL'
    right.operator(AlignToOriginOperator.bl_idname, text = AlignToOriginOperator.bl_label)

    row = layout.row()
    split = row.split(factor=0.5)        
    left = split.column()
    right = split.column()
    right.operator(NextToolOperator.bl_idname, text = NextToolOperator.bl_label)

def draw_flip_workflow(layout):
    row = layout.row()
    row.label(text = 'Flip Mesh')
    row = layout.row()
    box = row.box()
    box.label(text=f"Select an object and then click the {InvertZAxisOperator.bl_label} button to flip the mesh.")

    row = layout.row()
    split = row.split(factor=0.5)
    left = split.column()
    right = split.column()
    left.alert = True
    left.operator(CancelInvertZAxisOperator.bl_idname, text = CancelInvertZAxisOperator.bl_label)
    right.emboss = 'NORMAL'
    right.operator(InvertZAxisOperator.bl_idname, text = InvertZAxisOperator.bl_label)

    row = layout.row()
    split = row.split(factor=0.5)        
    left = split.column()
    right = split.column()
    right.operator(NextToolOperator.bl_idname, text = NextToolOperator.bl_label)

class CREUAddonPanel(bpy.types.Panel):
    bl_label = "Cushion Processing Tools"
    bl_idname = "CREU_PT_tools_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Cushion Processing"
    #bl_context = "object" # Context will force the addon to appear in the side panel, we want it on the sidebar

    def draw(self, context):
        layout = self.layout
        
        grid = layout.grid_flow(row_major = True, columns = 4)

        grid.operator(
            StartAlignToOriginOperator.bl_idname,
            text = "",
            icon='ORIENTATION_GLOBAL'
        )

        grid.operator(
            StartInvertZAxisOperator.bl_idname,
            text = "",
            icon='ARROW_LEFTRIGHT'
        )

        grid.operator(
            StartStandardiseMeshQualityOperator.bl_idname,
            text = "",
            icon='MOD_REMESH'
        )

        grid.operator(
            StartEraseMeshOperator.bl_idname,
            text = "",
            icon='TRASH'
        )

        grid.operator(
            StartHoleFillingOperator.bl_idname,
            text = "",
            icon='MESH_GRID'
        )

        grid.operator(
            StartSmoothingOperator.bl_idname,
            text = "",
            icon='MOD_SMOOTH'
        )

        grid.operator(
            StartExportOperator.bl_idname,
            text = "",
            icon='EXPORT'
        )

        tool = context.scene.creu.active_tool

        # if tool == "NONE":
            # Do nothing
        if tool == "ALIGN":
            draw_align_workflow(layout)
        elif tool == "FLIP":
            draw_flip_workflow(layout)
        elif tool == "REDUCE":
            draw_reduce_workflow(layout)
        elif tool == "ERASE":
            draw_erase_workflow(layout)
        elif tool == "HOLES":
            draw_holes_workflow(layout)
        elif tool == "SMOOTH":
            draw_smooth_workflow(layout)
        elif tool == "EXPORT":
            draw_export_workflow(layout)

def register():
    bpy.utils.register_class(StartAlignToOriginOperator)
    bpy.utils.register_class(StartInvertZAxisOperator)
    bpy.utils.register_class(StartStandardiseMeshQualityOperator)
    bpy.utils.register_class(StartEraseMeshOperator)
    bpy.utils.register_class(StartHoleFillingOperator)
    bpy.utils.register_class(StartSmoothingOperator)
    bpy.utils.register_class(StartExportOperator)

    bpy.utils.register_class(CancelAlignToOriginOperator)
    bpy.utils.register_class(AlignToOriginOperator)

    bpy.utils.register_class(CancelInvertZAxisOperator)
    bpy.utils.register_class(InvertZAxisOperator)

    bpy.utils.register_class(NextToolOperator)

    bpy.utils.register_class(CREUAddonPanel)
    
    bpy.utils.register_class(CREUProperties)
    bpy.types.Scene.creu = bpy.props.PointerProperty(type = CREUProperties)


def unregister():
    bpy.utils.unregister_class(CREUAddonPanel)

    bpy.utils.unregister_class(NextToolOperator)

    bpy.utils.unregister_class(AlignToOriginOperator)
    bpy.utils.unregister_class(CancelAlignToOriginOperator)
    bpy.utils.unregister_class(InvertZAxisOperator)
    bpy.utils.unregister_class(CancelInvertZAxisOperator)

    bpy.utils.unregister_class(StartAlignToOriginOperator)
    bpy.utils.unregister_class(StartInvertZAxisOperator)
    bpy.utils.unregister_class(StartStandardiseMeshQualityOperator)
    bpy.utils.unregister_class(StartEraseMeshOperator)
    bpy.utils.unregister_class(StartHoleFillingOperator)
    bpy.utils.unregister_class(StartSmoothingOperator)
    bpy.utils.unregister_class(StartExportOperator)
    
    del bpy.types.Scene.creu
    bpy.utils.unregister_class(CREUProperties)

if __name__ == "__main__":
    register()





















